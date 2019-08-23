#!/usr/bin/python
# -*- coding: utf8 -*-

import RPi.GPIO as GPIO
import logging

if __name__ == '__main__':
    import sys
    import time
    sys.path.append('..')

from utility import setLogging

__all__ = [
            'keyAPI',
            ]

# 定义按键
KEY_POWER       = 23    # Key1 - 电源
KEY_INC_VOLUME  = 24    # Key2 - 音量增加
KEY_DEC_VOLUME  = 25    # Key3 - 音量减少
KEY_MUTE        = 8     # Key4 - 关闭自动接入

KEY_PLAY        =  7    # 播放
KEY_CALL        = 16    # 呼叫

# 局部变量
_key            = None


# 按键处理回调函数
def cbKey(chan):
    global _key
    if _key:
        if  chan == KEY_PLAY and _key._cbKeyPlay:
            _key._cbKeyPlay()
        elif chan == KEY_MUTE and _key._cbKeyMute:
            _key._cbKeyMute()
        elif chan == KEY_CALL and _key._cbKeyCall:
            _key._cbKeyCall()
        elif chan == KEY_POWER and _key._cbKeyPower:
            _key._cbKeyPower()
        elif chan == KEY_INC_VOLUME and _key._cbKeyIncVolume:
            _key._cbKeyIncVolume()
        elif chan == KEY_DEC_VOLUME and _key._cbKeyDecVolume:
            _key._cbKeyDecVolume()


# 按键接口类
class keyAPI(object):
    # 初始化
    def __init__(self):
        global _key
        logging.debug('keyAPI.init().')
        _key = self
        self._cbKeyPlay       = None    # 播放按键回调函数指针
        self._cbKeyMute       = None    # 自动接入按键回调函数指针
        self._cbKeyCall       = None    # 呼叫按键回调函数指针
        self._cbKeyPower      = None    # 电源按键回调函数指针
        self._cbKeyIncVolume  = None    # 音量增加按键回调函数指针
        self._cbKeyDecVolume  = None    # 音量减少按键回调函数指针

        # 初始化按键端口及回调函数
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        keyList = [KEY_PLAY, KEY_MUTE, KEY_CALL, KEY_POWER, KEY_INC_VOLUME, KEY_DEC_VOLUME]
        for key in keyList:
            GPIO.setup(key, GPIO.IN, pull_up_down = GPIO.PUD_UP)
            GPIO.add_event_detect(key, GPIO.FALLING, callback = cbKey, bouncetime = 5)

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


################################################################################
# 测试程序
def testCallback():
    logging.debug('keyAPI.testCallback()..')

if __name__ == '__main__':
    key = keyAPI()
    key.setPlayCallback(testCallback)
    key.setCallCallback(testCallback)
    key.setMuteCallback(testCallback)
    key.setPowerCallback(testCallback)
    key.setDecVolumeCallback(testCallback)
    key.setIncVolumeCallback(testCallback)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.debug('Quit by user...')

