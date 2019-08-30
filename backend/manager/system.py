#!/usr/bin/python
# -*- coding: utf8 -*-

import time
if __name__ == '__main__':
    import sys
    sys.path.append('..')
import data_access
from data_access import server
from manager.serverFSM import serverFSM

_system = None

def init(robotId = None):
    global _system
    if not _system:
        _, server_info = server.get_server_info()   # 获取服务器地址
        hostName = server_info['address']
        portNumber = server_info['port']
        if not robotId:
            robotId = 'b827eb319c88'
        _system = serverFSM(hostName = hostName, portNumber = portNumber, robotId = robotId)


def fini():
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
        sys.exit(0)

