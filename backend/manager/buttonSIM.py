#!/usr/bin/python
# -*- coding: utf8 -*-

import logging
import threading
import pyHook
import pythoncom

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
            'setImxCallback'
            ]

# 定义按键
BUTTON_POWER        = 'R'   # 'r' - 电源
BUTTON_INC_VOLUME   = 'I'   # 'i' - 音量增加
BUTTON_DEC_VOLUME   = 'D'   # 'd' - 音量减少
BUTTON_MUTE         = 'M'   # 'm' - 接入模式

BUTTON_PLAY         = 'P'   # 'p' - 播放
BUTTON_CALL         = 'C'   # 'c' - 呼叫

BUTTON_IMX          = 'X'   # 'x' - 视频模拟

# 局部变量
_fini               = False
_pressed            = False

_cbButtonPower      = None  # 电源按键回调函数指针
_cbButtonIncVolume  = None  # 音量增加按键回调函数指针
_cbButtonDecVolume  = None  # 音量减少按键回调函数指针
_cbButtonMute       = None  # 关闭自动接入按键回调函数指针
_cbButtonPlay       = None  # 播放按键回调函数指针
_cbButtonCall       = None  # 呼叫按键回调函数指针
_cbButtonImx        = None  # 视频模拟按键回调函数指针

_buttonThread       = None

class keypad():
    def onKeyDown(self, event):
        global _pressed
        if not _pressed:
            _pressed = True
            if event.Key == BUTTON_POWER and _cbButtonPower:
                _cbButtonPower()
            elif event.Key == BUTTON_INC_VOLUME and _cbButtonIncVolume:
                _cbButtonIncVolume()
            elif event.Key == BUTTON_DEC_VOLUME and _cbButtonDecVolume:
                _cbButtonDecVolume()
            elif event.Key == BUTTON_MUTE and _cbButtonMute:
                _cbButtonMute()
            elif event.Key == BUTTON_PLAY and _cbButtonPlay:
                _cbButtonPlay()
            elif event.Key == BUTTON_CALL and _cbButtonCall:
                _cbButtonCall()
            elif event.Key == BUTTON_IMX and _cbButtonImx:
                _cbButtonImx()
        return True

    def onKeyUp(self, event):
        global _pressed
        _pressed = False
        return True


# 按键线程
def buttonThread():
    global _buttonThread, _fini

    logging.debug('buttonSIM.buttonThread().')
    _fini = False
    kp = keypad()
    hm = pyHook.HookManager()
    hm.KeyDown = kp.onKeyDown
    hm.KeyUp   = kp.onKeyUp
    hm.HookKeyboard()
    pythoncom.PumpMessages()
    while not _fini:
        time.sleep(1)
    _buttonThread = None
    logging.debug('buttonSIM.buttonThread() fini.')


# 初始化按键
def init():
    global _buttonThread

    logging.debug('buttonSIM.ini().')
    if not _buttonThread:
        _buttonThread = threading.Thread(target = buttonThread)
        _buttonThread.start()
        time.sleep(0.5)


# 结束按键
def fini():
    global _fini, _buttonThread

    logging.debug('buttonSIM.fini().')
    if _buttonThread:
        _fini = True
        while _buttonThread:
            time.sleep(1)


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


# 设置视频模拟键处理回调函数
def setImxCallback(cb):
    global _cbButtonImx
    _cbButtonImx, cb = cb, _cbButtonImx
    return cb


################################################################################
# 测试程序
def testCallback():
    logging.debug('buttonSIM.testCallback()..')

if __name__ == '__main__':
    global _buttonThread

    init()
    setPlayCallback(testCallback)
    setCallCallback(testCallback)
    setMuteCallback(testCallback)
    setPowerCallback(testCallback)
    setDecVolumeCallback(testCallback)
    setIncVolumeCallback(testCallback)
    setImxCallback(testCallback)
    try:
        while True:
            time.sleep(2)
            if not _buttonThread:
                break
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
