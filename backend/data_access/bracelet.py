#!/usr/bin/python
# -*- coding: utf8 -*-

from data_access import confmgr

scanned_bracelet_list = [
    {
        'mac': '5CEA1D8CAAE4'
    },
    {
        'mac': 'EEEE1D8CAAE4'
    },
    {
        'mac': '5CEA1D8CEEEE'
    }
]


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


# not used yet
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


def get_scanned_bracelet_list():
    return True, scanned_bracelet_list
