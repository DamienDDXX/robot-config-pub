#!/usr/bin/python
# -*- coding: utf8 -*-

from data_access import confmgr


def get_settings():
    setting_conf, _ = confmgr.get_conf_section('SETTINGS')
    if setting_conf['audio_frequency'] == '':
        audio_frequency = ''
    else:
        audio_frequency = int(setting_conf['audio_frequency'])
    return True, {
        'cameraResolution': setting_conf['camera_resolution'],
        'audioFrequency': audio_frequency,
        'gpsCoord': setting_conf['gps']
    }


def update_settings(s):
    if not('cameraResolution' in s and 'audioFrequency' in s):
        return False, 'cameraResolution or audioFrequency is missing'
    setting_conf, conf = confmgr.get_conf_section('SETTINGS')
    setting_conf['camera_resolution'] = s['cameraResolution']
    setting_conf['audio_frequency'] = str(s['audioFrequency'])
    if 'gpsCoord' in s:
        setting_conf['gps'] = s['gpsCoord']
    else:
        setting_conf['gps'] = ''
    confmgr.update_conf(conf)
    return True, 'updated'
