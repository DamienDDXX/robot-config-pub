# !/usr/bin/python
# * -*- coding: utf8 -*-

import os
import time

#
# 自动连接 WiFi
#
def auto_wifi():
    """
    automatic WiFi connection.
    """
    while True:
        try:
            fd = os.popen('ifconfig | grep 192')
            content = fd.read()
            print(content)
            fd.close()
            if '192' not in content:
                os.system('sudo ifup --force wlan0')
        finally:
            pass
        time.sleep(1 * 60)

# 执行代码
if __name__ == '__main__':
    print('automatic WiFi connection.')
    auto_wifi()
