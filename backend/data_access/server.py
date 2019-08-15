#!/usr/bin/python
# -*- coding: utf8 -*-

from data_access import confmgr


def get_server_info():
    server_conf, _ = confmgr.get_conf_section('SERVER')
    server_info = {
        'address': server_conf['address'],
        'port': server_conf['port']
    }
    return True, server_info


def update_server_info(s_info):
    if not('address' in s_info and 'port' in s_info):
        return False, 'address or port is missing'
    server_info, conf = confmgr.get_conf_section('SERVER')
    server_info['address'] = s_info['address']
    server_info['port'] = str(s_info['port'])
    confmgr.update_conf(conf)
    return True, 'updated'
