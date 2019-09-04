#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import platform
import traceback

__all__ = [
        'updateWifi'
        ]

WIFI_DIRNAME = os.getcwd()
WIFI_FILENAME = 'wpa_supplicant.conf'
if platform.system().lower() == 'linux':
    WIFI_SAVEFILE = '/etc/wpa_supplicant/wpa_supplicant.conf'

# 更新无线网络
def updateWifi(ssid = None, psk = None, priority = None):
    try:
        # 删除之前的无线配置文件
        filePath = os.path.join(WIFI_DIRNAME, WIFI_FILENAME)
        if os.path.isfile(filePath):
            os.remove(filePath)

        # 创建新的无线配置文件
        with open(filePath, 'w') as wifiFile:
            contents = [
                'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n',
                'update_config=1\n',
                'country=CN\n',
                '\n',
                'network={\n',
                '    ssid=\"%s\"\n' %str(ssid),
                '    psk=\"%s\"\n' %str(psk),
                '    priority=%s\n' %str(priority),
                '}\n'
                '\n',
                'network={\n',
                '    ssid=\"robot-cfg\"\n',
                '    psk=\"onlyforrobot\"\n',
                '    priority=1\n',
                '}'
            ]
            wifiFile.writelines(contents)
        if platform.system().lower() == 'linux':
            os.system('sudo cp %s %s' %(filePath, WIFI_SAVEFILE))
    except:
        traceback.print_exc()
    finally:
        # TODO
        pass


################################################################################
# 测试程序
if __name__ == '__main__':
    updateWifi('Damien', '12345678', '5')
