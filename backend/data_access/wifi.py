#!/usr/bin/python
# -*- coding: utf8 -*-

from data_access import confmgr
from utility import updateWifi
from manager.wifiAPI import wifiAPI

_wifi = None

# 获取无线网络配置信息
def get_wifi_info():
    wifi_conf, _ = confmgr.get_conf_section('WIFI')
    wifi_info = {
        'name': wifi_conf['name'],
        'password': wifi_conf['password']
    }
    return True, wifi_info


# 更新无线网络配置信息
def update_wifi_info(w_info):
    if not('name' in w_info):
        return False, 'wifi name is missing'
    wifi_info, conf = confmgr.get_conf_section('WIFI')
    wifi_info['name'] = w_info['name']
    if 'password' in w_info:
        wifi_info['password'] = w_info['password']
    else:
        wifi_info['password'] = ''
    confmgr.update_conf(conf)
    updateWifi.updateWifi(w_info['name'], w_info['password'], '5')
    return True, 'updated'


# 获取可用的无线网络列表
def get_available_wifi_list():
    global _wifi
    if not _wifi:
        _wifi = wifiAPI()
    return True, _wifi.scan()
