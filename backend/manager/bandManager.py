#!/usr/bin/python
# -*- coding: utf8 -*-

from ctypes import *
import time
import threading
import logging


__all__ = [
        'bandInit',
        'bandScan',
        'bandConnect',
        'bandDisconnect',
        'bandMonitor',
        'bandMonitorSetCallback',
        'bandGetHvx',
        'bandSetInv',
        'bandThreadStart',
        'bandThreadStop'
        ]


BLE_SERIAL_NAME = '/dev/serial0'

US_BLE_OK                   = 100
US_BLE_ERR_ADAPTER_INIT     = 101
US_BLE_ERR_STACK_INIT       = 102
US_BLE_ERR_OPTIONS_SET      = 103
US_BLE_ERR_CALLBACK_INVALID = 104
US_BLE_ERR_CONN_IN_PROGRESS = 105
US_BLE_ERR_CONN_TOO_MANY    = 106

logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(levelname)s- %(message)s')


# 手环 mac 地址数据结构
band_addr_t = POINTER(c_ubyte)
c_ubyte_p   = POINTER(c_ubyte)
band_mac_t  = c_ubyte * 6


# 定义回调函数类型
onConnectedCallback_t       = CFUNCTYPE(None, band_addr_t, c_ushort)
onDisconnectedCallback_t    = CFUNCTYPE(None, c_ushort)
onAdvReportCallback_t       = CFUNCTYPE(None, band_addr_t, c_ubyte, c_ubyte_p, c_ushort, c_char)
onConnTimeoutCallback_t     = CFUNCTYPE(None, band_addr_t)
onScanTimeoutCallback_t     = CFUNCTYPE(None)
onWriteResponseCallback_t   = CFUNCTYPE(None, c_ushort, c_ushort, c_ushort)
onHvxCallback_t             = CFUNCTYPE(None, c_ushort, c_ushort, c_ubyte_p, c_ushort)
onTxCompleteCallback_t      = CFUNCTYPE(None, c_ushort)


# 局部变量
_bandCdll           = None
_bandIsConnected    = False
_bandConnHandle     = None
_bandConnTimeout    = False
_bandList           = []
_bandHvx            = {}
_bandInv            = 30 * 60

_bandStop           = False
_bandThread         = None

_reqeustHealth      = False

_scanDone           = False

_cbOnConnected      = None
_cbOnDisconnected   = None
_cbOnMonitor        = None


# 将地址转换为字符串
def macToString(addr):
    mac = '%02X%02X%02X%02X%02X%02X' %(addr[0], addr[1], addr[2], addr[3], addr[4], addr[5])
    return mac


# 将字符串转换为地址
def stringToMac(addr):
    mac = (c_ubyte * 6)()
    mac[0] = int(addr[ 0: 2], 16)
    mac[1] = int(addr[ 2: 4], 16)
    mac[2] = int(addr[ 4: 6], 16)
    mac[3] = int(addr[ 6: 8], 16)
    mac[4] = int(addr[ 8:10], 16)
    mac[5] = int(addr[10:12], 16)
    return mac


# 连接成功处理回调函数
def onConnected(addr, handle):
    global _bandCdll, _bandIsConnected, _bandConnHandle
    logging.debug('onConnected().')
    if _bandCdll:
        _bandCdll.us_ble_enable_cccd(handle)
        _bandIsConnected = True
        _bandConnHandle  = handle

    # 连接成功回调函数
    if _cbOnConnected:
        _cbOnConnected()


# 连接断开回调函数
def onDisconnected(handle):
    global _bandIsConnected, _bandConnHandle
    logging.debug('onDisconnected().')
    _bandIsConnected = False
    _bandConnHandle  = 0xFFFF

    # 连接断开回调函数
    if _cbOnDisconnected:
        _cbOnDisconnected()


# 扫描结果处理回调函数
def onAdvReport(addr, type, buff, length, rssi):
    global _bandList
    if length == 31 and buff[0] == 0x03 and buff[1] == 0x08 and buff[2] == 0x42 and buff[3] == 0x33:
        addr = macToString(addr)
        item = { 'mac' : addr }
        if item not in _bandList:
            _bandList.append(item)
            logging.debug('onAdvReport(): mac - %s, high blood - %d, low blood - %d, heart rate - %d' %(addr, buff[25], buff[30], buff[16]))


# 连接超时回调函数
def onConnTimeout(addr):
    global _bandConnTimeout
    _bandConnTimeout = True
    logging.debug('onConnTimeout(): mac - %s' %macToString(addr))


# 扫描结束回调函数
def onScanTimeout():
    global _scanDone
    _scanDone = True
    logging.debug('onScanTimeout().')
    for band in _bandList:
        logging.debug('mac - %s' %band['mac'])


# 激活设备通知成功回调函数
def onWriteResponse(connHandle, cccdHandle, status):
    logging.debug('onWriteResponse().')


# 从设备通知回调函数
def onHvx(connHandle, charHandle, buff, length):
    global _bandHvx, _reqeustHealth
    logging.debug('onHvx().')
    cmd = buff[1]
    if cmd == 0x14:
        # 电池电量数据
        _bandHvx['battery'] = str(buff[4])
        logging.debug('battery - %d' %buff[4])
    elif cmd == 0x47:
        # 实时心率数据
        _bandHvx['heartRate'] = str(buff[4])
        logging.debug('heartRate - %d' %buff[4])
    elif cmd == 0x48:
        # 实时体温数据
        _bandHvx['temperature'] = str(buff[5] * 256 + buff[4])
        logging.debug('temperature - %d' %(buff[5] * 256 + buff[4]))
    elif cmd == 0x4C:
        # 全部健康数据
        _bandHvx['heartrate'] = str(buff[4])
        _bandHvx['diastolicPre'] = str(buff[5])
        _bandHvx['systolicPre'] = str(buff[6])
        logging.debug('heartRate - %d, diastolicPre - %d, systolicPre - %d' %(buff[4], buff[5], buff[6]))
        _reqeustHealth = False
    else:
        pass


# 发送完毕回调函数
def onTxComplete(connHandle):
    logging.debug('onTxComplete().')


# 手环错误处理
def bandError():
    global _bandCdll
    if _bandCdll:
        error = _bandCdll.us_ble_error_code()
        if error == 100:
            logging.debug('Error code: %d - US_BLE_OK' %error)
        if error == 101:
            logging.debug('Error code: %d - US_BLE_ERR_ADAPTER_INIT' %error)
        elif error == 102:
            logging.debug('Error code: %d - US_BLE_ERR_STACK_INIT' %error)
        elif error == 103:
            logging.debug('Error code: %d - US_BLE_ERR_OPTIONS_SET' %error)
        elif error == 104:
            logging.debug('Error code: %d - US_BLE_ERR_CALLBACK_INVALID' %error)
        elif error == 105:
            logging.debug('Error code: %d - US_BLE_ERR_CONN_IN_PROGRESS' %error)
        elif error == 106:
            logging.debug('Error code: %d - US_BLE_ERR_CONN_TOO_MANY' %error)
        else:
            logging.debug('Error code: %d - Unknown error type' %error)
    else:
        logging.debug('CDLL not loaded.')


# 手环初始化
def bandInit():
    global _bandCdll
    logging.debug('bandInit() start.')
    try:
        if not _bandCdll:
            # 避免重复初始化
            _bandCdll = cdll.LoadLibrary('/usr/lib/libm1_shared_raspbian_zerow.so')
            if _bandCdll.us_ble_init(BLE_SERIAL_NAME):
                _bandCdll.us_ble_set_callbacks(onConnectedCallback_t(onConnected),
                                               onAdvReportCallback_t(onAdvReport),
                                               onConnTimeoutCallback_t(onConnTimeout),
                                               onScanTimeoutCallback_t(onScanTimeout),
                                               onDisconnectedCallback_t(onDisconnected),
                                               onWriteResponseCallback_t(onWriteResponse),
                                               onHvxCallback_t(onHvx),
                                               onTxCompleteCallback_t(onTxComplete))
                logging.debug('bandInit() success.')
                return True
        logging.debug('bandInit() failed.')
        bandError()
        return False
    except:
        logging.debug('bandInit() except.')
        return False


# 扫描手环
def bandScan():
    global _bandCdll, _scanDone, _bandList
    logging.debug('bandScan() start.')
    _bandList = []
    if _bandCdll:
        _scanDone = False
        _bandCdll.us_ble_scan()
        while not _scanDone:
            time.sleep(1)
        logging.debug('band scan success.')
    else:
        logging.debug('band scan failed.')
        bandError()
    return _bandList


# 连接手环
def bandConnect(addr):
    global _bandCdll, _bandIsConnected, _bandConnTimeout
    logging.debug('bandConnect(%s) start.' %addr)
    if _bandCdll:
        _bandIsConnected = False
        _bandConnTimeout = False
        _bandCdll.us_ble_connect.restype = c_bool
        if bool(_bandCdll.us_ble_connect(stringToMac(addr))):
            for timeout in range(0, 30):
                time.sleep(1)
                logging.debug('band connect wait %d.' %(timeout + 1))
                if _bandIsConnected or _bandConnTimeout:
                    break
            if _bandIsConnected:
                logging.debug('band connect success.')
                return True
    logging.debug('band connect failed.')
    bandError()
    return False


# 断开手环连接
def bandDisconnect():
    global _bandCdll, _bandIsConnected, _connHandle
    logging.debug('bandDisconnect() start.')
    if _bandCdll and _bandIsConnected:
        _bandCdll.us_ble_disconnect(c_ushort(_connHandle))
        for timeout in range(0, 30):
            time.sleep(1)
            if not _bandIsConnected:
                break

        if not _bandIsConnected:
            logging.debug('band disconnect success.')
            return True

    logging.debug('band disconnect failed.')
    return False


# 判定手环是否连接成功
def bandIsConnected():
    return _bandIsConnected


# 获取手环测量健康数据
def bandGetHvx():
    global _bandHvx
    return _bandHvx if len(_bandHvx) > 0 else None


# 设置手环时间
def bandSetTime():
    global _bandCdll, _bandIsConnected, _bandConnHandle
    logging.debug('bandSetTime() start.')
    if _bandCdll and _bandIsConnected:
        tm   = time.localtime(time.time())
        tm32 = (((tm.tm_year - 2016) & 0x0F) << 26) + ((tm.tm_mon & 0x0F) << 22) + ((tm.tm_mday & 0x1F) << 17) + ((tm.tm_hour & 0x1F) << 12) + ((tm.tm_min & 0x3F) << 6) + ((tm.tm_sec & 0x3F) << 0)
        data = (c_ubyte * 20)()
        data[0] = 0x26;
        data[1] = 0x01;
        data[2] = 0x00;
        data[3] = 0x00;
        data[4] = (tm32 >> 24) & 0xFF
        data[5] = (tm32 >> 16) & 0xFF
        data[6] = (tm32 >>  8) & 0xFF
        data[7] = (tm32 >>  0) & 0xFF
        _bandCdll.us_ble_write(_bandConnHandle, pointer(data), 20)


# 请求电量信息
def bandRequestBattery():
    global _bandCdll, _bandIsConnected, _bandConnHandle
    logging.debug('bandRequestBattery() start.')
    if _bandCdll and _bandIsConnected:
        data = (c_ubyte * 20)()
        data[0] = 0x20
        data[1] = 0x14
        data[2] = 0x00
        data[3] = 0x00
        _bandCdll.us_ble_write(_bandConnHandle, pointer(data), 20)


# 请求测量健康数据
def bandRequestHealth(onOff):
    global _bandCdll, _bandIsConnected, _bandConnHandle, _reqeustHealth
    logging.debug('bandRequestHealth() start.')
    if _bandCdll and _bandIsConnected:
        _reqeustHealth = onOff
        data = (c_ubyte * 20)()
        data[0] = 0x20
        data[1] = 0x14
        data[2] = 0x00
        data[3] = 0x00
        data[4] = 0x01 if onOff else 0x00
        _bandCdll.us_ble_write(_bandConnHandle, pointer(data), 20)


# 手环监控健康数据
def bandMonitor(addr):
    global _reqeustHealth, _bandIsConnected, _cbOnMonitor
    logging.debug('bandMonitor() start.')
    if bandConnect(addr):
        bandSetTime()                   # 设置手环时间
        bandRequestBattery()            # 请求获取手环电量信息
        bandRequestHealth(True)         # 请求获取健康数据

        # 等待测量结果
        for timeout in range(0, 120):
            if not _reqeustHealth or not _bandIsConnected:
                time.sleep(1)
                logging.debug('band monitor wait: %ds.' %(timeout + 1))

        # 获取测量结果后，断开连接
        if _bandIsConnected:
            bandRequestHealth(False)    # 关闭测量健康数据
            time.sleep(1)
            bandDisconnect()            # 断开连接
            if _cbOnMonitor:
                _cbOnMonitor()

        return True
    return False


# 设置手环监控成功回调函数
def bandMonitorSetCallback(cb):
    global _cbOnMonitor
    _cbOnMonitor, cb = cb, _cbOnMonitor
    return cb


# 设置手环检测时间间隔
def bandSetInv(inv):
    global _bandInv
    _bandInv = inv * 60


# 手环后台监控线程
def bandThread(addr):
    global _bandStop, _bandThread
    logging.debug('bandThread() start.')
    while not _bandStop:
        start = time.time()
        bandMonitor(addr)
        interval = _bandInv - int(time.time() - start)
        interval = 30 if interval < 30 else interval
        for timeout in range(0, interval):
            if _bandStop:
                break;
            time.sleep(1)
    _bandThread = None
    logging.debug('bandThread() stop.')


# 启动手环管理线程
def bandThreadStart(addr):
    global _bandStop, _bandThread
    _bandStop = False
    if not _bandThread:
        _bandThread = threading.Thread(target = bandThread, args = [addr, ])
        _bandThread.start()


# 停止手环管理线程
def bandThreadStop():
    global _bandStop
    _bandStop = True


# 测试程序
if __name__ == '__main__':
    bandInit()
    try:
        while len(_bandList) == 0:
            bandScan()
        bandSetInv(1)
        bandThreadStart(_bandList[0]['mac'])
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        bandThreadStop()
