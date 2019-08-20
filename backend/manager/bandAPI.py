#!/usr/bin/python
# -*- coding: utf8 -*-

from ctypes import *
import sys
import time
import logging

__all__ = [
        'init',
        'scan',
        'connect',
        'disconnect',
        'monitor',
        'getHvx',
        'getScan',
        ]


BLE_SERIAL_NAME  = '/dev/serial0'
BLE_LIBRARY_PATH = '/usr/lib/libm1_shared_zerow_gcc.so'

US_BLE_OK                   = 100
US_BLE_ERR_ADAPTER_INIT     = 101
US_BLE_ERR_STACK_INIT       = 102
US_BLE_ERR_OPTIONS_SET      = 103
US_BLE_ERR_CALLBACK_INVALID = 104
US_BLE_ERR_CONN_IN_PROGRESS = 105
US_BLE_ERR_CONN_TOO_MANY    = 106

logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(filename)s[line:%(lineno)d] - %(thread)d - %(levelname)s - %(message)s')


# 手环 mac 地址数据结构
band_addr_t = POINTER(c_ubyte)
c_ubyte_p   = POINTER(c_ubyte)
band_mac_t  = c_ubyte * 6


# 定义回调函数类型
onConnectedCallback_t       = CFUNCTYPE(None, band_addr_t, c_ushort)
onDisconnectedCallback_t    = CFUNCTYPE(None, c_ushort)
onAdvReportCallback_t       = CFUNCTYPE(None, band_addr_t, c_ubyte, c_ubyte_p, c_ushort, c_byte)
onConnTimeoutCallback_t     = CFUNCTYPE(None, band_addr_t)
onScanTimeoutCallback_t     = CFUNCTYPE(None)
onWriteResponseCallback_t   = CFUNCTYPE(None, c_ushort, c_ushort, c_ushort)
onHvxCallback_t             = CFUNCTYPE(None, c_ushort, c_ushort, c_ubyte_p, c_ushort)
onTxCompleteCallback_t      = CFUNCTYPE(None, c_ushort)


# 局部变量
_cdll           = None
_band           = None
_isConnected    = False
_connHandle     = None
_connTimeout    = False

_scanDone       = False
_scanList       = []

_hvx            = {}
_mac            = (c_ubyte * 6)()

_reqeustHealth  = False

_cbOnConnected      = None
_cbOnDisconnected   = None
_cbOnAdvReport      = None
_cbOnConnTimeout    = None
_cbOnScanTimeout    = None
_cbOnWriteResponse  = None
_cbOnHvx            = None
_cbOnTxComplete     = None


# 将地址转换为字符串
def macToString(addr):
    mac = '%02X%02X%02X%02X%02X%02X' %(addr[5], addr[4], addr[3], addr[2], addr[1], addr[0])
    return mac


# 将字符串转换为地址
def stringToMac(addr):
    _mac[5] = int(addr[ 0: 2], 16)
    _mac[4] = int(addr[ 2: 4], 16)
    _mac[3] = int(addr[ 4: 6], 16)
    _mac[2] = int(addr[ 6: 8], 16)
    _mac[1] = int(addr[ 8:10], 16)
    _mac[0] = int(addr[10:12], 16)
    return _mac


# 连接成功处理回调函数
def onConnected(addr, handle):
    global _cdll, _isConnected, _connHandle
    logging.debug('bandAPI.onConnected().')
    if _cdll:
        _cdll.us_ble_enable_cccd(c_ushort(handle))
        _isConnected = True
        _connHandle  = handle


# 连接断开回调函数
def onDisconnected(handle):
    global _isConnected, _connHandle
    logging.debug('bandAPI.onDisconnected().')
    _isConnected = False
    _connHandle  = 0xFFFF


# 扫描结果处理回调函数
def onAdvReport(addr, type, buff, length, rssi):
    global _scanList, _band, _hvx
    if length == 31 and buff[0] == 0x03 and buff[1] == 0x08 and buff[2] == 0x42 and buff[3] == 0x33:
        addr = macToString(addr)
        item = { 'mac' : addr }
        if item not in _scanList:
            _scanList.append(item)
            logging.debug('bandAPI.onAdvReport(): mac - %s, high blood - %d, low blood - %d, heart rate - %d' %(addr, buff[25], buff[30], buff[16]))

        if _band and addr == _band:
            _hvx['battery'] = buff[15] & 0x7F
            _hvx['batteryUpdate'] = True if (buff[15] & 0x80) == 0x80 else False
            _hvx['heartRate'] = buff[16] & 0xFF
            _hvx['heartRateUpdate'] = True if (buff[18] & 0x80) == 0x80 else False
            _hvx['temperature'] = ((buff[23] & 0x7F) << 4) + ((buff[24] & 0xFF) >> 4)
            _hvx['temperatureUpdate'] = True if (buff[23] & 0x80) == 0x80 else False
            _hvx['systolicPre'] = buff[25] & 0xFF
            _hvx['diastolicPre'] = buff[30] & 0xFF
            _hvx['bloodPressureUpdate'] = True if (buff[24] & 0x01) == 0x01 else False
            _hvx['notWearingAlert'] = True if (buff[24] & 0x04) == 0x04 else False


# 连接超时回调函数
def onConnTimeout(addr):
    global _connTimeout
    _connTimeout = True
    logging.debug('bandAPI.onConnTimeout(%s).' %macToString(addr))


# 扫描结束回调函数
def onScanTimeout():
    global _scanDone, _scanList
    _scanDone = True
    logging.debug('bandAPI.onScanTimeout().')
    for band in _scanList:
        logging.debug('mac - %s' %band['mac'])


# 激活设备通知成功回调函数
def onWriteResponse(connHandle, cccdHandle, status):
    if connHandle == 12:
        logging.debug('bandAPI.onWriteResponse(): CCCD Enabled')


# 从设备通知回调函数
def onHvx(connHandle, charHandle, buff, length):
    global _hvx, _reqeustHealth
    cmd = buff[1]
    logging.debug('bandAPI.onHvx() 0x%02x.' %cmd)
    if cmd == 0x14:
        # 电池电量数据
        _hvx['battery'] = str(buff[4])
        logging.debug('battery - %d' %buff[4])
    elif cmd == 0x47:
        # 实时心率数据
        _hvx['heartRate'] = str(buff[4])
        logging.debug('heartRate - %d' %buff[4])
    elif cmd == 0x48:
        # 实时体温数据
        _hvx['temperature'] = str(buff[5] * 256 + buff[4])
        logging.debug('temperature - %d' %(buff[5] * 256 + buff[4]))
    elif cmd == 0x4C:
        # 全部健康数据
        _hvx['heartrate'] = str(buff[4])
        _hvx['diastolicPre'] = str(buff[5])
        _hvx['systolicPre'] = str(buff[6])
        logging.debug('heartRate - %d, diastolicPre - %d, systolicPre - %d' %(buff[4], buff[5], buff[6]))
        _reqeustHealth = False
    else:
        pass


# 发送完毕回调函数
def onTxComplete(connHandle):
    logging.debug('bandAPI.onTxComplete().')


# 手环错误处理
def reportError():
    global _cdll
    if _cdll:
        error = _cdll.us_ble_error_code()
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
        logging.debug('cdll not loaded.')


# 手环初始化
def init():
    global _cdll
    global _cbOnConnected, _cbOnAdvReport, _cbOnConnTimeout, _cbOnScanTimeout, _cbOnDisconnected, _cbOnWriteResponse, _cbOnHvx, _cbOnTxComplete

    ret = True
    logging.debug('bandAPI.init().')
    try:
        if not _cdll:   # 避免重复初始化
            _cdll = cdll.LoadLibrary(BLE_LIBRARY_PATH)
            logging.debug('load library: %s' %BLE_LIBRARY_PATH)
            if _cdll.us_ble_init(BLE_SERIAL_NAME):
                _cbOnConnected      = onConnectedCallback_t(onConnected)
                _cbOnDisconnected   = onDisconnectedCallback_t(onDisconnected)
                _cbOnAdvReport      = onAdvReportCallback_t(onAdvReport)
                _cbOnConnTimeout    = onConnTimeoutCallback_t(onConnTimeout)
                _cbOnScanTimeout    = onScanTimeoutCallback_t(onScanTimeout)
                _cbOnWriteResponse  = onWriteResponseCallback_t(onWriteResponse)
                _cbOnHvx            = onHvxCallback_t(onHvx)
                _cbOnTxComplete     = onTxCompleteCallback_t(onTxComplete)
                _cdll.us_ble_set_callbacks(_cbOnConnected,
                                               _cbOnAdvReport,
                                               _cbOnConnTimeout,
                                               _cbOnScanTimeout,
                                               _cbOnDisconnected,
                                               _cbOnWriteResponse,
                                               _cbOnHvx,
                                               _cbOnTxComplete)
            else:
                ret = False
    except:
        ret = False
        traceback.print_exc()
    finally:
        logging.debug('bandAPI.init() %s.' %('success' if ret else 'failed'))
        if not ret:
            reportError()
        return ret


# 扫描手环
def scan():
    global _cdll, _scanDone, _scanList

    ret = False
    del _scanList[:]
    logging.debug('bandAPI.scan().')
    if _cdll:
        _scanDone = False
        _cdll.us_ble_scan()
        while not _scanDone:
            time.sleep(1)
        ret = True
    logging.debug('bandAPI.scan() %s.' %('success' if ret else 'failed'))
    if not ret:
        reportError()
    return ret, _scanList


# 获取扫描列表
def getScan():
    global _scanList
    return _scanList


# 连接手环
def connect(addr):
    global _cdll, _isConnected, _connTimeout

    ret = False
    logging.debug('bandAPI.connect(%s).' %addr)
    if _cdll:
        _isConnected = False
        _connTimeout = False
        _cdll.us_ble_connect.restype = c_bool
        if bool(_cdll.us_ble_connect(stringToMac(addr))):
            for timeout in range(0, 30):
                time.sleep(1)
                logging.debug('band connect wait %d.' %(timeout + 1))
                if _isConnected or _connTimeout:
                    break
            if _isConnected:
                ret = True
    logging.debug('bandAPI.connect(%s) %s.' %(addr, 'success' if ret else 'failed'))
    if not ret:
        reportError()
    return ret


# 断开手环连接
def disconnect():
    global _cdll, _isConnected, _connHandle

    ret = False
    logging.debug('bandAPI.disconnect().')
    if _cdll and _isConnected:
        _cdll.us_ble_disconnect(c_ushort(_connHandle))
        for timeout in range(0, 30):
            time.sleep(1)
            if not _isConnected:
                break
        if not _isConnected:
            ret = True
    logging.debug('bandAPI.disconnect %s.' %('success' if ret else 'failed'))
    return False


# 判定手环是否连接成功
def isConnected():
    global _isConnected
    return _isConnected


# 获取手环测量健康数据
def getHvx():
    global _hvx
    return _hvx if len(_hvx) > 0 else None


# 设置手环时间
def setTime():
    global _cdll, _isConnected, _connHandle
    logging.debug('bandAPI.setTime().')
    if _cdll and _isConnected:
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
        _cdll.us_ble_write(_connHandle, pointer(data), 20)


# 请求电量信息
def requestBattery():
    global _cdll, _isConnected, _connHandle
    logging.debug('bandAPI.requestBattery().')
    if _cdll and _isConnected:
        data = (c_ubyte * 20)()
        data[0] = 0x20
        data[1] = 0x14
        data[2] = 0x00
        data[3] = 0x00
        _cdll.us_ble_write(_connHandle, pointer(data), 20)


# 请求测量健康数据
def requestHealth(onOff):
    global _cdll, _isConnected, _connHandle, _reqeustHealth
    logging.debug('bandAPI.requestHealth().')
    if _cdll and _isConnected:
        _reqeustHealth = onOff
        data = (c_ubyte * 20)()
        data[0] = 0x20
        data[1] = 0x4B
        data[2] = 0x00
        data[3] = 0x00
        data[4] = 0x01 if onOff else 0x00
        _cdll.us_ble_write(_connHandle, pointer(data), 20)


# 手环监控健康数据
def monitor(addr):
    global _reqeustHealth, _isConnected, _band

    logging.debug('bandAPI.monitor().')
    if connect(addr):
        setTime()                   # 设置手环时间
        time.sleep(1)
        requestBattery()            # 请求获取手环电量信息
        time.sleep(1)
        requestHealth(True)         # 请求获取健康数据
        time.sleep(1)

        # 等待测量结果
        for timeout in range(0, 120):
            if _reqeustHealth and _isConnected:
                time.sleep(1)
                logging.debug('band monitor wait: %ds.' %(timeout + 1))

        # 获取测量结果后，断开连接
        if _isConnected:
            requestHealth(False)    # 关闭测量健康数据
            time.sleep(1)
            disconnect()            # 断开连接
        time.sleep(5)
        _band = addr
        scan()                      # 再次进行扫描，以获取手环的佩戴状态信息
        return True, _hvx
    return False, None


# 测试程序
if __name__ == '__main__':
    try:
        scanList = []
        if init():
            while True:
                ret, scanList = scan()
                if ret and len(scanList) > 0:
                    print(scanList)
                    while True:
                        ret, hvx = monitor(scanList[0]['mac'])
                        if ret:
                            print(hvx)
                        time.sleep(60)
                time.sleep(10)
    except KeyboardInterrupt:
        sys.exit(0)

