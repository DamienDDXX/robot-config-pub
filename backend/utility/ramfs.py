#!/usr/bin/python
# -*- coding: utf8 -*-


import os, platform
import logging
import traceback

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from utility import setLogging

__all__ = [
        'ramfs',
        ]

if platform.system().lower() == 'windows':
    PATH = os.getcwd()
elif platform.system().lower() == 'linux':
    PATH = '/ram'
else:
    raise NotImplementedError

# 初始化内存文件系统
def ramfsInit():
    try:
        logging.debug('ramfsInit().')
        if platform.system().lower() == 'linux':
            fd = os.popen('df -l | grep %s' %PATH)
            content = fd.read()
            logging.debug('ramfsInit() - %s.' %content)
            fd.close()
            if PATH not in content:
                if not os.path.isdir(PATH):
                    logging.debug('ramfsInit() - mkdir %s.' %PATH)
                    os.system('sudo mkdir %s' %PATH)
                os.system('sudo mount -t tmpfs -o size=300m,mode=0777 tmpfs /ram')
    finally:
        return PATH


###############################################################################
# 测试程序
if __name__ == '__main__':
    ramfsInit()
