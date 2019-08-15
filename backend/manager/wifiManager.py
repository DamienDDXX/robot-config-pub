#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import sys
import time
import threading
import logging
import pywifi
import platform
from pywifi import const


__all__ = [
        'wifiInit',
        'wifiScan',
        'wifiConnect'
        'wifiDisonnect'
        ]


logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(levelname)s- %(message)s')


# 局部变量
_wifiIFace      = None
_wifiProfile    = None


# 初始化无线网络
def wifiInit():
    global _wifiIFace
    logging.debug('wifiInit() start.')
    if not _wifiIFace:
        # 避免重复初始化
        _wifiIFace = pywifi.PyWiFi().interfaces()[0]


# 扫描可用的无线网络
def wifiScan():
    global _wifiIFace
    logging.debug('wifiScan() start.')
    scanList = []
    if _wifiIFace:
        _wifiIFace.scan()
        time.sleep(5)
        wifiDict = {}
        wifiList = _wifiIFace.scan_results()
        for ap in wifiList:
            if ap.ssid:
                wifiDict[ap.ssid] = ap

        for ssid in list(wifiDict.keys()):
            ap = { 'name': wifiDict[ssid].ssid, 'isSecured':  not wifiDict[ssid].akm[0] == const.CIPHER_TYPE_NONE }
            scanList.append(ap)
    return scanList


# 连接指定的无线网络
def wifiConnect(ssid, key):
    global _wifiIFace, _wifiProfile
    logging.debug('wifiConnect(ssid - %s, key - %s) start.' %(ssid, key))
    if _wifiIFace:
        if wifiIsConnected():
            wifiDisconnect()

        _wifiIFace.remove_all_network_profiles()
        profile = pywifi.Profile()
        profile.ssid = ssid
        profile.auth = const.AUTH_ALG_OPEN
        profile.akm.append(const.AKM_TYPE_WPA2PSK if key else const.AKM_TYPE_NONE)
        profile.cipher = const.CIPHER_TYPE_CCMP if key else const.CIPHER_TYPE_NONE
        profile.key = key
        _wifiProfile = _wifiIFace.add_network_profile(profile)
        _wifiIFace.connect(_wifiProfile)
        for timeout in range(15):
            time.sleep(1)
            if _wifiIFace.status() == const.IFACE_CONNECTED:
                logging.debug('wifi connect to \'%s\' success.' %_wifiProfile.ssid)
                return True
    logging.debug('wifi connect to \'%s\' failed.' %_wifiProfile.ssid)
    return False


# 断开无线网络连接
def wifiDisconnect():
    global _wifiIFace
    logging.debug('wifiDisconnect() start.')
    if _wifiIFace:
        _wifiIFace.disconnect()
        for timeout in range(0, 3):
            time.sleep(1)
            if _wifiIFace.status() == const.IFACE_DISCONNECTED:
                break;


# 判定无线网络是否连接
def wifiIsConnected():
    global _wifiIFace
    if _wifiIFace:
        return True if _wifiIFace.status() == const.IFACE_CONNECTED else False
    return False


# wifi 管理模块
#   自动检测掉线并重新连接
#   扫描所有的 wifi 热点
#   连接 wifi
#   断开连接 wifi
#   判断是否连接 wifi
class wifiManager:
    def __init__(self):
        self._wifiIFace     = pywifi.PyWiFi().interfaces()[0]
        self._wifiApDict    = {}
        self._wifiApList    = None
        self._wifiProfile   = None
        self._wifiThread    = None
        self._stopEvent     = threading.Event()
        self._stopEvent.clear()


    # 自动检测掉线并重新连接
    def wifiThread(self):
        logging.debug('\n****** start monitoring wifi... ******\n')
        while not self._stopEvent.isSet():
            if self._wifiProfile:
                if self._wifiIFace.status() != const.IFACE_CONNECTED:
                    logging.debug('\n****** wifi is down, restart... ******\n')
                    self.wifiConnect(self._wifiProfile)
            self._stopEvent.wait(30)


    def start(self):
        if self._wifiThread == None:
            self._stopEvent.clear()
            self._wifiThread = threading.Thread(target = self.wifiThread)
            self._wifiThread.start()

    def stop(self):
        if self._wifiThread:
            self._stopEvent.set()
            self._wifiThread.join()
            self._wifiThread = None


if __name__ == '__main__':
    wifiInit()
    wifiScan()
    wifiConnect('Damien', '123456789')

