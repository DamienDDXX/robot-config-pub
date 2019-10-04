#!/usr/bin/python
# -*- coding: utf8 -*-

from data_access import confmgr


def get_volume():
    volume_info, _ = confmgr.get_conf_section('VOLUME')
    return True, volume_info['volume']

def set_volume(volume):
    if volume >= 0 and volume <= 100:
        volume_info, conf = confmgr.get_conf_section('VOLUME')
        volume_info['volume'] = str(volume)
        confmgr.update_conf(conf)
        return True, 'updated'
    return False, 'failed'

