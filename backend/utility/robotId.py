#!/usr/bin/python
# -*- coding: utf8 -*-

import uuid


__all__ = ["robotId"]

# 计算机器人的 id
#
#   算法说明：
#       获取主板的 MAC 地址
def robotId():
    """
    get the local machine's mac address
    """
    return uuid.uuid1().hex[-12:].lower()


# 执行代码
if __name__ == '__main__':
    print(robotId())
