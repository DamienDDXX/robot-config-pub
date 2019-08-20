#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import logging

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from data_access import confmgr
from utility import setLogging

__all__ = [
        'init',
        'scan',
        'connect',
        'disconnect',
        'monitor',
        'getHvx',
        'getScan',
        'getBand'
        ]


# 局部变量
_band               = None
_isConnected        = False
_scanList           = []
_hvx                = {}


# 手环初始化
def init():
    logging.debug('bandSIM.init().')
    time.sleep(3)
    return True


# 扫描手环
def scan():
    global _scanList, _band

    del _scanList[:]
    logging.debug('bandSIM.scan().')
    time.sleep(30)
    _scanList = [
            { 'mac': '1F007295A7D1' },
            { 'mac': '435A30318903' },
            ]
    if _band:
        _scanList.append({ 'mac': _band })
    return True, _scanList


# 获取扫描列表
def getScan():
    global _scanList
    return _scanList


# 连接手环
def connect(addr):
    global _isConnected

    logging.debug('bandSIM.connect(%s).' %addr)

    _isConnected = False
    time.sleep(15)
    if addr == _band:
        _isConnected = True
    else:
        for band in _scanList:
            if addr == band['mac']:
                _isConnected = True
                break
    return _isConnected


# 断开手环连接
def disconnect():
    global _isConnected

    logging.debug('bandSIM.disconnect().')
    time.sleep(2)
    _isConnected = False
    return True


# 判定手环是否连接成功
def isConnected():
    global _isConnected
    return _isConnected


# 获取手环测量健康数据
def getHvx():
    global _hvx
    return _hvx if len(_hvx) > 0 else None


# 手环监控健康数据
def monitor(addr):
    global _isConnected, _band, _hvx

    logging.debug('bandSIM.monitor(%s).' %addr)
    _hvx.clear()
    _band = addr
    if connect(addr):
        time.sleep(15)      # 等待测量结果

        # 模拟监控结果
        _hvx['battery']             = 71
        _hvx['batteryUpdate']       = False
        _hvx['heartRate']           = 78
        _hvx['heartRateUpdate']     = False
        _hvx['temperature']         = 312
        _hvx['temperatureUpdate']   = False
        _hvx['systolicPre']         = 110
        _hvx['diastolicPre']        = 82
        _hvx['bloodPressureUpdate'] = False
        _hvx['notWearingAlert']     = False

        if _isConnected:
            time.sleep(1)
            disconnect()    # 断开连接
        time.sleep(5)
        _band = addr
        scan()              # 再次进行扫描，以获取手环的佩戴状态信息
        return True, _hvx
    return False, None


# 获取手环配置
def getBand():
    ret = False
    band = ''
    logging.debug('bandSIM.getBand().')
    try:
        setting_conf, _ = confmgr.get_conf_section('BRACELET')
        band = setting_conf['bracelet1']
        if len(band) == 12:
            for i in range(0, 6):
                val = int(band[2 * i : 2 * (i + 1)], 16)
                if val < 0 or val > 255:
                    raise ValueError
        ret = True
    except:
        ret = False
    finally:
        return ret, band


################################################################################
# 测试程序
if __name__ == '__main__':
    try:
        scanList = []
        if init():
            ret, band = getBand()
            if not ret:
                while True:
                    ret, scanList = scan()
                    if ret and len(scanList) > 0:
                        band = scanList[0]['mac']
                        print(scanList)
                        break;
                    time.sleep(30)

            while True:
                ret, hvx = monitor(band)
                if ret:
                    print(hvx)
                time.sleep(60)
            time.sleep(10)
    except KeyboardInterrupt:
        sys.exit(0)
