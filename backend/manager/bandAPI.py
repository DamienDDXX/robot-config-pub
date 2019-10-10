#!/usr/bin/python
# -*- coding: utf8 -*-

from ctypes import *
import time
import logging
import threading
import traceback

if __name__ == '__main__':
    import sys
    sys.path.append('..')
    from data_access import bracelet

from utility import setLogging

__all__ = [
        'bandAPI',
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
_bandInited = False

# 手环接口类
class bandAPI(object):
    # 类初始化
    def __init__(self):
        self._cdll = cdll.LoadLibrary(BLE_LIBRARY_PATH)
        self._band = None

        self._connIsOk = False
        self._connHandle = None
        self._connEvent = threading.Event()

        self._scanList = []
        self._scanEvent = threading.Event()

        self._hvx = {}
        self._mac = (c_ubyte * 6)()
        self._reqeustHealth = False

        self._cbOnConnected = None
        self._cbOnDisconnected = None
        self._cbOnAdvReport = None
        self._cbOnConnTimeout = None
        self._cbOnScanTimeout = None
        self._cbOnWriteResponse = None
        self._cbOnHvx = None
        self._cbOnTxComplete = None

    # 初始化手环
    def init(self):
        global _bandInited
        logging.debug('bandAPI.init().')
        try:
            ret = True
            if not _bandInited:
                _bandInited = True
                if self._cdll.us_ble_init(BLE_SERIAL_NAME):
                    self._cbOnConnected = onConnectedCallback_t(self.onConnected)
                    self._cbOnDisconnected = onDisconnectedCallback_t(self.onDisconnected)
                    self._cbOnAdvReport = onAdvReportCallback_t(self.onAdvReport)
                    self._cbOnConnTimeout = onConnTimeoutCallback_t(self.onConnTimeout)
                    self._cbOnScanTimeout = onScanTimeoutCallback_t(self.onScanTimeout)
                    self._cbOnWriteResponse = onWriteResponseCallback_t(self.onWriteResponse)
                    self._cbOnHvx = onHvxCallback_t(self.onHvx)
                    self._cbOnTxComplete = onTxCompleteCallback_t(self.onTxComplete)
                    self._cdll.us_ble_set_callbacks(self._cbOnConnected,
                                                    self._cbOnAdvReport,
                                                    self._cbOnConnTimeout,
                                                    self._cbOnScanTimeout,
                                                    self._cbOnDisconnected,
                                                    self._cbOnWriteResponse,
                                                    self._cbOnHvx,
                                                    self._cbOnTxComplete)
                else:
                    self.reportError()
                    raise Exception
        except Exception:
            ret = False
            traceback.print_exc()
        finally:
            logging.debug('bandAPI.init() %s.' %('success' if ret else 'failed'))
            return ret

    # 扫描手环
    def scan(self):
        logging.debug('bandAPI.scan().')
        self._scanEvent.clear()
        self._cdll.us_ble_scan()
        self._scanEvent.wait(40)
        if self._scanEvent.isSet():
            return True, self._scanList
        return False, None

    # 获取扫描结果
    def getScan(self):
        return self._scanList

    # 连接手环
    def connect(self, addr):
        logging.debug('bandAPI.connect(%s).' %addr)
        ret = False
        self._connIsOk = False
        self._connEvent.clear()
        self._cdll.us_ble_connect(self.stringToMac(addr))
        self._connEvent.wait(30)
        ret = True if self._connIsOk else False
        if not ret:
            self.reportError()
        logging.debug('bandAPI.connect(%s) %s.' %(addr, 'success' if ret else 'failed'))
        return ret

    # 断开手环连接
    def disconnect(self):
        logging.debug('bandAPI.disconnect().')
        if self._connIsOk:
            self._connEvent.clear()
            self._cdll.us_ble_disconnect(c_ushort(self._connHandle))
            self._connEvent.wait(30)
        logging.debug('bandAPI.disconnect %s.' %('success' if not self._connIsOk else 'failed'))
        return not self._connIsOk

    # 判定手环是否连接成功
    def isConnected(self):
        return self._connIsOk

    # 获取手环测量健康数据
    def getHvx(self):
        logging.debug('bandAPI.getHvx().')
        return self._hvx if len(self._hvx) > 0 else None

    # 将地址转换为字符串
    def macToString(self, addr):
        mac = '%02X%02X%02X%02X%02X%02X' %(addr[5], addr[4], addr[3], addr[2], addr[1], addr[0])
        return mac

    # 将字符串转换为地址
    def stringToMac(self, addr):
        self._mac[5] = int(addr[ 0: 2], 16)
        self._mac[4] = int(addr[ 2: 4], 16)
        self._mac[3] = int(addr[ 4: 6], 16)
        self._mac[2] = int(addr[ 6: 8], 16)
        self._mac[1] = int(addr[ 8:10], 16)
        self._mac[0] = int(addr[10:12], 16)
        return self._mac

    # 连接成功处理回调函数
    def onConnected(self, addr, handle):
        logging.debug('bandAPI.onConnected().')
        self._cdll.us_ble_enable_cccd(c_ushort(handle))
        self._connHandle = handle
        self._connIsOk = True
        self._connEvent.set()

    # 连接断开回调函数
    def onDisconnected(self, handle):
        logging.debug('bandAPI.onDisconnected().')
        self._connHandle = 0xFFFF
        self._connIsOk = False
        self._connEvent.set()

    # 扫描结果处理回调函数
    def onAdvReport(self, addr, type, buff, length, rssi):
        if length == 31 and buff[0] == 0x03 and buff[1] == 0x08 and buff[2] == 0x42 and buff[3] == 0x33:
            addr = self.macToString(addr)
            item = { 'mac' : addr }
            if item not in self._scanList:
                self._scanList.append(item)
                logging.debug('bandAPI.onAdvReport(): mac - %s, high blood - %d, low blood - %d, heart rate - %d' %(addr, buff[25], buff[30], buff[16]))

            if self._band and addr == self._band:
                self._hvx['battery']             = buff[15] & 0x7F
                self._hvx['batteryUpdate']       = True if (buff[15] & 0x80) == 0x80 else False
                self._hvx['heartRate']           = buff[16] & 0xFF
                self._hvx['heartRateUpdate']     = True if (buff[18] & 0x80) == 0x80 else False
                self._hvx['temperature']         = ((buff[23] & 0x7F) << 4) + ((buff[24] & 0xFF) >> 4)
                self._hvx['temperatureUpdate']   = True if (buff[23] & 0x80) == 0x80 else False
                self._hvx['systolicPre']         = buff[25] & 0xFF
                self._hvx['diastolicPre']        = buff[30] & 0xFF
                self._hvx['bloodPressureUpdate'] = True if (buff[24] & 0x01) == 0x01 else False
                self._hvx['notWearingAlert']     = True if (buff[24] & 0x02) == 0x02 else False

    # 连接超时回调函数
    def onConnTimeout(self, addr):
        self._connIsOk = False
        self._connEvent.set()
        logging.debug('bandAPI.onConnTimeout(%s).' %self.macToString(addr))

    # 扫描结束回调函数
    def onScanTimeout(self):
        logging.debug('bandAPI.onScanTimeout().')
        for band in self._scanList:
            logging.debug('mac - %s' %band['mac'])
        self._scanEvent.set()

    # 激活设备通知成功回调函数
    def onWriteResponse(self, connHandle, cccdHandle, status):
        if connHandle == 12:
            logging.debug('bandAPI.onWriteResponse(): CCCD Enabled')

    # 从设备通知回调函数
    def onHvx(self, connHandle, charHandle, buff, length):
        cmd = buff[1]
        logging.debug('bandAPI.onHvx() 0x%02x.' %cmd)
        if cmd == 0x14:
            # 电池电量数据
            self._hvx['battery'] = str(buff[4])
            logging.debug('battery - %d' %buff[4])
        elif cmd == 0x47:
            # 实时心率数据
            self._hvx['heartRate'] = str(buff[4])
            logging.debug('heartRate - %d' %buff[4])
        elif cmd == 0x48:
            # 实时体温数据
            self._hvx['temperature'] = str(buff[5] * 256 + buff[4])
            logging.debug('temperature - %d' %(buff[5] * 256 + buff[4]))
        elif cmd == 0x4C:
            # 全部健康数据
            self._hvx['heartRate'] = str(buff[4])
            self._hvx['diastolicPre'] = str(buff[5])
            self._hvx['systolicPre'] = str(buff[6])
            logging.debug('heartRate - %d, diastolicPre - %d, systolicPre - %d' %(buff[4], buff[5], buff[6]))
            self._reqeustHealth = False
        else:
            pass

    # 发送完毕回调函数
    def onTxComplete(self, connHandle):
        logging.debug('bandAPI.onTxComplete().')

    # 手环错误处理
    def reportError(self):
        error = self._cdll.us_ble_error_code()
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

    # 设置手环时间
    def setTime(self):
        logging.debug('bandAPI.setTime().')
        if self._connIsOk:
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
            self._cdll.us_ble_write(self._connHandle, pointer(data), 20)

    # 请求电量信息
    def requestBattery(self):
        logging.debug('bandAPI.requestBattery().')
        if self._connIsOk:
            data = (c_ubyte * 20)()
            data[0] = 0x20
            data[1] = 0x14
            data[2] = 0x00
            data[3] = 0x00
            self._cdll.us_ble_write(self._connHandle, pointer(data), 20)

    # 请求测量健康数据
    def requestHealth(self, onOff):
        logging.debug('bandAPI.requestHealth(%s).' %('on' if onOff else 'off'))
        if self._connIsOk:
            self._reqeustHealth = onOff
            data = (c_ubyte * 20)()
            data[0] = 0x20
            data[1] = 0x4B
            data[2] = 0x00
            data[3] = 0x00
            data[4] = 0x01 if onOff else 0x00
            self._cdll.us_ble_write(self._connHandle, pointer(data), 20)

    # 手环监控健康数据
    def monitor(self, addr):
        logging.debug('bandAPI.monitor(%s).' %addr)
        if self.connect(addr):
            self.setTime()                  # 设置手环时间
            time.sleep(1)
            self.requestBattery()           # 请求获取手环电量信息
            time.sleep(1)
            self.requestHealth(True)        # 请求获取健康数据
            time.sleep(1)

            # 等待测量结果
            for timeout in range(0, 120):
                if self._reqeustHealth and self._connIsOk:
                    time.sleep(1)
                    logging.debug('band monitor wait: %ds.' %(timeout + 1))

            # 获取测量结果后，断开连接
            if self._connIsOk:
                self.requestHealth(False)   # 关闭测量健康数据
                time.sleep(1)
                self.disconnect()           # 断开连接
            time.sleep(3)
            self._band = addr
            self.scan()                     # 再次进行扫描，以获取手环的佩戴状态信息
            return True, self._hvx
        self._hvx.clear()
        return False, None


################################################################################
# 测试程序
if __name__ == '__main__':
    try:
        scanList = []
        api = bandAPI()
        if api.init():
            _, mac = bracelet.get_bracelet_mac(1)
            if not mac:
                while True:
                    ret, scanList = api.scan()
                    if ret and len(scanList) > 0:
                        mac = scanList[0]['mac']
                        print(scanList)
                        break;
                    time.sleep(30)
            while True:
                ret, hvx = api.monitor(mac)
                if ret:
                    print(hvx)
                time.sleep(60)
            time.sleep(10)
    except KeyboardInterrupt:
        sys.exit(0)
