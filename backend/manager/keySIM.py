#!/usr/bin/python
# -*- coding: utf8 -*-

import logging
import threading
import pyHook
import pythoncom
import time

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from utility import setLogging

__all__ = [
            'keyAPI'
            ]

# 定义按键
KEY_POWER        = 'R'   # 'r' - 电源
KEY_INC_VOLUME   = 'I'   # 'i' - 音量增加
KEY_DEC_VOLUME   = 'D'   # 'd' - 音量减少
KEY_MUTE         = 'M'   # 'm' - 接入模式

KEY_PLAY         = 'P'   # 'p' - 播放
KEY_CALL         = 'C'   # 'c' - 呼叫

KEY_IMX          = 'X'   # 'x' - 视频模拟
KEY_RADIO        = 'U'   # 'u' - 广播模拟

# 局部变量
_fini           = False
_pressed            = False

_cbKeyPower     = None  # 电源按键回调函数指针
_cbKeyIncVolume = None  # 音量增加按键回调函数指针
_cbKeyDecVolume = None  # 音量减少按键回调函数指针
_cbKeyMute      = None  # 关闭自动接入按键回调函数指针
_cbKeyPlay      = None  # 播放按键回调函数指针
_cbKeyCall      = None  # 呼叫按键回调函数指针
_cbKeyImx       = None  # 视频模拟按键回调函数指针
_cbKeyRadio     = None  # 广播模拟按键回调函数指针


# 按键线程
def keyThread(key):
    logging.debug('keySIM.keyThread().')
    hm = pyHook.HookManager()
    hm.KeyDown = key.onKeyDown
    hm.KeyUp   = key.onKeyUp
    hm.HookKeyboard()
    pythoncom.PumpMessages()
    while not key._fini:
        time.sleep(1)
    key._thread = None
    logging.debug('keySIM.keyThread() fini.')


# 按键接口类
class keyAPI(object):
    # 初始化
    def __init__(self):
        logging.debug('keyAPI.init().')
        self._fini      = False
        self._pressed   = None

        self._cbKeyPlay       = None    # 播放按键回调函数指针
        self._cbKeyMute       = None    # 自动接入按键回调函数指针
        self._cbKeyCall       = None    # 呼叫按键回调函数指针
        self._cbKeyPower      = None    # 电源按键回调函数指针
        self._cbKeyIncVolume  = None    # 音量增加按键回调函数指针
        self._cbKeyDecVolume  = None    # 音量减少按键回调函数指针
        self._cbKeyImx        = None    # 视频模拟按键回调函数指针
        self._cbKeyRadio      = None    # 广播模拟按键回调函数指针

        # 启动按键监控线程
        self._thread = threading.Thread(target = keyThread, args = [self, ])
        self._thread.start()

    # 终止
    def fini(self):
        logging.debug('keyAPI.fini().')
        if self._thread:
            self._fini = True
            while self._thread:
                time.sleep(0.5)

    # 设置播放按键处理回调函数
    def setPlayCallback(self, cb):
        self._cbKeyPlay, cb = cb, self._cbKeyPlay
        return cb

    # 设置呼叫按键处理回调函数
    def setCallCallback(self, cb):
        self._cbKeyCall, cb = cb, self._cbKeyCall
        return cb

    # 设置关闭自动接入按键处理回调函数
    def setMuteCallback(self, cb):
        self._cbKeyMute, cb = cb, self._cbKeyMute
        return cb

    # 设置电源按键处理回调函数
    def setPowerCallback(self, cb):
        self._cbKeyPower, cb = cb, self._cbKeyPower
        return cb

    # 设置音量增加键处理回调函数
    def setIncVolumeCallback(self, cb):
        self._cbKeyIncVolume, cb = cb, self._cbKeyIncVolume
        return cb

    # 设置音量减少键处理回调函数
    def setDecVolumeCallback(self, cb):
        self._cbKeyDecVolume, cb = cb, self._cbKeyDecVolume
        return cb

    # 设置视频模拟键处理回调函数
    def setImxCallback(self, cb):
        self._cbKeyImx, cb = cb, self._cbKeyImx
        return cb

    # 设置广播模拟键处理回调函数
    def setRadioCallback(self, cb):
        self._cbKeyRadio, cb = cb, self._cbKeyRadio
        return cb

    # 按下回调函数
    def onKeyDown(self, event):
        if not self._pressed:
            self._pressed = True
            if event.Key == KEY_POWER and self._cbKeyPower:
                self._cbKeyPower()
            elif event.Key == KEY_INC_VOLUME and self._cbKeyIncVolume:
                self._cbKeyIncVolume()
            elif event.Key == KEY_DEC_VOLUME and self._cbKeyDecVolume:
                self._cbKeyDecVolume()
            elif event.Key == KEY_MUTE and self._cbKeyMute:
                self._cbKeyMute()
            elif event.Key == KEY_PLAY and self._cbKeyPlay:
                self._cbKeyPlay()
            elif event.Key == KEY_CALL and self._cbKeyCall:
                self._cbKeyCall()
            elif event.Key == KEY_IMX and self._cbKeyImx:
                self._cbKeyImx()
            elif event.Key == KEY_RADIO and self._cbKeyRadio:
                self._cbKeyRadio()
        return True

    # 抬起回调函数
    def onKeyUp(self, event):
        key._pressed = False
        return True


################################################################################
# 测试程序
def testCallback():
    logging.debug('keySIM.testCallback().')

if __name__ == '__main__':
    key = keyAPI()
    key.setPlayCallback(testCallback)
    key.setCallCallback(testCallback)
    key.setMuteCallback(testCallback)
    key.setPowerCallback(testCallback)
    key.setDecVolumeCallback(testCallback)
    key.setIncVolumeCallback(testCallback)
    key.setImxCallback(testCallback)
    key.setRadioCallback(testCallback)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        key.fini()
    finally:
        while key._thread:
            time.sleep(1)
        logging.debug('Quit by user...')

