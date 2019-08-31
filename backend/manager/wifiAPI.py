#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import platform
import pywifi
from pywifi import const
import logging
import traceback

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from utility import setLogging


__all__ = [
        'wifiAPI',
        ]


# 无线网络接口类
class wifiAPI(object):
    # 初始化
    def __init__(self):
        if platform.system().lower() == 'windows':
            self._iface = pywifi.PyWiFi().interfaces()[0]
        elif platform.system().lower() == 'linux':
            self._iface = pywifi.PyWiFi().interfaces()[1]
        else:
            self._iface = None
        self._profile = None

    # 扫描网络热点
    def scan(self):
        logging.debug('wifiAPI.scan().')
        scanList = []
        try:
            apDict = {}
            self._iface.scan()
            time.sleep(8)
            apList = self._iface.scan_results()
            for ap in apList:
                if ap.ssid:
                    apDict[ap.ssid] = ap
            for ssid in list(apDict.keys()):
                ap = { 'name': apDict[ssid].ssid, 'isSecured':  not apDict[ssid].akm[0] == const.CIPHER_TYPE_NONE }
                scanList.append(ap)
        except:
            traceback.print_exc()
        finally:
            return scanList

    # 连接指定的无线网络
    def connect(self, ssid, key):
        logging.debug('wifiAPI.connect(%s, %s).' %(ssid, key))
        if self.isConnected():
            self.disconnect()
        self._iface.remove_all_network_profiles()
        profile = pywifi.Profile()
        profile.ssid = ssid
        profile.auth = const.AUTH_ALG_OPEN
        profile.akm.append(const.AKM_TYPE_WPA2PSK if key else const.AKM_TYPE_NONE)
        profile.cipher = const.CIPHER_TYPE_CCMP if key else const.CIPHER_TYPE_NONE
        profile.key = key
        self._profile = self._iface.add_network_profile(profile)
        self._iface.connect(self._profile)
        for i in range(0, 15):
            time.sleep(1)
            if self._iface.status() == const.IFACE_CONNECTED:
                logging.debug('wifiAPIconnect(%s, %s) success.' %(ssid, key))
                return True
        logging.debug('wifiAPIconnect(%s, %s) failed.' %(ssid, key))
        return False

    # 端口无线网络连接
    def disconnect(self):
        logging.debug('wifiAPI.disconnect().')
        self._iface.disconnect()
        for i in range(0, 10):
            time.sleep(1)
            if self._iface.status() == const.IFACE_DISCONNECTED:
                return True
        return False

    # 判断是否连接无线网络
    def isConnected(self):
        logging.debug('wifiAPI.isConnected().')
        return True if self._iface.status() == const.IFACE_CONNECTED else False


###############################################################################
# 测试程序
if __name__ == '__main__':
    wifi = wifiAPI()
    scanList = wifiAPI().scan()
    for i in scanList:
        print(i)

