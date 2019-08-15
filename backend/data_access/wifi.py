#!/usr/bin/python
# -*- coding: utf8 -*-

from data_access import confmgr
from manager import wifiManager

wifi_list = [
    {
        'name': 'robot-cfg',
        'isSecured': True
    },
    {
        'name': 'godking',
        'isSecured': False
    },
    {
        'name': 'test',
        'isSecured': True
    }
]


def get_wifi_info():
    # conn = dbmgr.get_connection()
    # try:
    #     wifi_info = {}
    #     cursor = conn.cursor()
    #     cursor.execute('select name, password from robot_conf.wifi limit 1')
    #     result = cursor.fetchall()
    #     if len(result) > 0:
    #         wifi_info = {
    #             'name': result[0][0],
    #             'password': result[0][1]
    #         }
    #     return True, wifi_info
    # except IOError:
    #     return False, 'database operation error'
    # finally:
    #     conn.close()
    wifi_conf, _ = confmgr.get_conf_section('WIFI')
    wifi_info = {
        'name': wifi_conf['name'],
        'password': wifi_conf['password']
    }
    return True, wifi_info


def update_wifi_info(w_info):
    if not('name' in w_info):
        return False, 'wifi name is missing'
    # conn = dbmgr.get_connection()
    # try:
    #     cursor = conn.cursor()
    #     cursor.execute('delete from robot_conf.wifi')
    #     add_sql = 'insert into robot_conf.wifi(name, password) values (%s, %s)'
    #     cursor.execute(add_sql, (w_info['name'], w_info['password']))
    #     conn.commit()
    #     return True, 'updated'
    # except IOError:
    #     conn.rollback()
    #     return False, 'update failed'
    # finally:
    #     conn.close()
    wifi_info, conf = confmgr.get_conf_section('WIFI')
    wifi_info['name'] = w_info['name']
    if 'password' in w_info:
        wifi_info['password'] = w_info['password']
    else:
        wifi_info['password'] = ''
    confmgr.update_conf(conf)
    return True, 'updated'


def get_available_wifi_list():
    wifiManager.wifiInit()
    return True, wifiManager.wifiScan()
