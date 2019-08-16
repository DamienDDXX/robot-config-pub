#!/usr/bin/python
# -*- coding: utf8 -*-

import platform
from data_access import confmgr
from manager import bandManager


# 获取手环配置列表
def get_configured_bracelet_list():
    bracelet_conf, _ = confmgr.get_conf_section('BRACELET')
    bracelet1 = bracelet_conf['bracelet1']
    bracelet2 = bracelet_conf['bracelet2']
    bracelet_list = []
    if bracelet1 != '':
        bracelet_list.append({
            'id': 1,
            'mac': bracelet1
        })
    if bracelet2 != '':
        bracelet_list.append({
            'id': 2,
            'mac': bracelet2
        })
    return True, bracelet_list


# 获取指定的手环信息
def get_bracelet_info(bracelet_id):
    if bracelet_id > 2:
        return False, 'not found'
    bracelet_conf, _ = confmgr.get_conf_section('BRACELET')
    if bracelet_id == 1:
        bracelet = bracelet_conf['bracelet1']
    else:
        bracelet = bracelet_conf['bracelet2']
    if bracelet != '':
        return True, {
            'id': bracelet_id,
            'mac': bracelet
        }
    return False, 'not found'


# 重新配置手环信息
def update_bracelet_info(bracelet_id, mac):
    if bracelet_id > 2:
        return False, 'not found'
    bracelet_conf, conf = confmgr.get_conf_section('BRACELET')
    if bracelet_id == 1:
        bracelet_conf['bracelet1'] = mac
    else:
        bracelet_conf['bracelet2'] = mac
    confmgr.update_conf(conf)
    return True, 'updated'


# 增加手环配置
def add_bracelet(mac):
    # 保证先加bracelet1,  然后加bracelet2
    bracelet_conf, conf = confmgr.get_conf_section('BRACELET')
    if bracelet_conf['bracelet1'] != '' and bracelet_conf['bracelet2'] != '':
        return False, 'Only two bracelets supported'
    if bracelet_conf['bracelet1'] == '':
        bracelet_conf['bracelet1'] = mac
    else:
        bracelet_conf['bracelet2'] = mac
    confmgr.update_conf(conf)
    return True, 'added'


# 删除手环配置
def delete_bracelet(bracelet_id):
    # conn = dbmgr.get_connection()
    # try:
    #     cursor = conn.cursor()
    #     cursor.execute('delete from robot_conf.bracelet where id = ' + bracelet_id)
    #     conn.commit()
    #     return True, 'deleted'
    # except IOError:
    #     conn.rollback()
    #     return False, 'deleted failed'
    # finally:
    #     conn.close()
    if bracelet_id > 2:
        return False, 'not found'
    bracelet_conf, conf = confmgr.get_conf_section('BRACELET')
    if bracelet_id == 1:
        bracelet_conf['bracelet1'] = ''
    else:
        bracelet_conf['bracelet2'] = ''
    confmgr.update_conf(conf)
    return True, 'deleted'


# 获取扫描到的手环列表
def get_scanned_bracelet_list():
    if platform.system().lower() == 'windows':
        # windows 平台，模拟
        scanned_bracelet_list = [
                { 'mac': '6F361196FED7' },
                { 'mac': 'A58F537200F1' },
                { 'mac': 'EEEE1D8CAAE4' }
                ]
        return True, scanned_bracelet_list
    elif platform.system().lower() == 'linux':
        return True, bandManager.bandScan()
    else:
        return True, []
