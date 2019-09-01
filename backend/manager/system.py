#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import logging
if __name__ == '__main__':
    import sys
    sys.path.append('..')
import data_access
from data_access import server
from manager.serverFSM import serverFSM
from utility import setLogging

# 局部变量
_system = None


# 初始化系统
def init(robotId = 'b827eb319c88'):
    logging.debug('system.init().')
    global _system
    if not _system:
        _, server_info = server.get_server_info()   # 获取服务器地址
        hostName = server_info['address']
        portNumber = server_info['port']
        _system = serverFSM(hostName = hostName, portNumber = portNumber, robotId = robotId)


# 终止系统
def fini():
    logging.debug('system.fini().')
    global _system
    if _system:
        _system.fini()
    _system = None


if __name__ == '__main__':
    try:
        init()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        fini()
        time.sleep(10)
        try:
            init()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            fini()
            sys.exit(0)

