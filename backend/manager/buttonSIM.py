#!/usr/bin/python
# -*- coding: utf8 -*-

import pygame
import logging

if __name__ == '__main__':
    import time
    import sys
    sys.path.append('..')

from utility import setLogging

__all__ = [
            'init',
            'setPlayCallback',
            'setCallCallback',
            'setMuteCallback',
            'setPowerCallback',
            'setIncVolumeCallback',
            'setDecVolumeCallback',
            ]


# 局部变量
_buttonInited       = False
_cbButtonPower      = None  # 电源按键回调函数指针
_cbButtonIncVolume  = None  # 音量增加按键回调函数指针
_cbButtonDecVolume  = None  # 音量减少按键回调函数指针
_cbButtonMute       = None  # 关闭自动接入按键回调函数指针
_cbButtonPlay       = None  # 播放按键回调函数指针
_cbButtonCall       = None  # 呼叫按键回调函数指针


# 初始化按键
def init():
    # TODO
    pass


# 设置播放按键处理回调函数
def setPlayCallback(cb):
    global _cbButtonPlay
    _cbButtonPlay, cb = cb, _cbButtonPlay
    return cb

# 设置呼叫按键处理回调函数
def setCallCallback(cb):
    global _cbButtonCall
    _cbButtonCall, cb = cb, _cbButtonCall
    return cb


# 设置关闭自动接入按键处理回调函数
def setMuteCallback(cb):
    global _cbButtonMute
    _cbButtonMute, cb = cb, _cbButtonMute
    return cb


# 设置电源按键处理回调函数
def setPowerCallback(cb):
    global _cbButtonPower
    _cbButtonPower, cb = cb, _cbButtonPower
    return cb


# 设置音量增加键处理回调函数
def setIncVolumeCallback(cb):
    global _cbButtonIncVolume
    _cbButtonIncVolume, cb = cb, _cbButtonIncVolume
    return cb


# 设置音量减少键处理回调函数
def setDecVolumeCallback(cb):
    global _cbButtonDecVolume
    _cbButtonDecVolume, cb = cb, _cbButtonDecVolume
    return cb


################################################################################
# 测试程序
def testCallback():
    logging.debug('buttonAPI.testCallback()..')

if __name__ == '__main__':
    init()
    setPlayCallback(testCallback)
    setCallCallback(testCallback)
    setMuteCallback(testCallback)
    setPowerCallback(testCallback)
    setDecVolumeCallback(testCallback)
    setIncVolumeCallback(testCallback)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
