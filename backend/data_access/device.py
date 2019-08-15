#!/usr/bin/python
# -*- coding: utf8 -*-

from utility import robotId


def get_device_info():
    return True, { 'seriesNumber': robotId.robotId() }


def restart_server():
    return True, 'restarted'
