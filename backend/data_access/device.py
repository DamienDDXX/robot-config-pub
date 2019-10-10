#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import platform
from utility import robotId
from manager import system

if platform.system().lower() == 'linux':
    import os
    import sys


def get_device_info():
    return True, { 'seriesNumber': robotId.robotId() + ' - ' + str(os.getpid()) }


def restart_server():
    if platform.system().lower() == 'linux':
        os.system('sudo reboot')
        sys.exit(0)
    return True, 'restarted'


def shutdown_server():
    system.fini()   # 关闭后台服务器
    return True, 'shut down successfully'


def mimic_debug():
    system.fini()
    system.init()
    return True, 'mimic debug successfully'
