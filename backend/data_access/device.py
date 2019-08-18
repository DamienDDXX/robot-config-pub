#!/usr/bin/python
# -*- coding: utf8 -*-

import platform
from utility import robotId

if platform.system().lower() == 'linux':
    import os
    import sys


def get_device_info():
    return True, { 'seriesNumber': robotId.robotId() }


def restart_server():
    if platform.system().lower() == 'linux':
        os.system('sudo reboot')
        sys.exit(0)
    return True, 'restarted'
