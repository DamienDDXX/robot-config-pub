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
            'init',
            'setPlayCallback',
            'setCallCallback',
            'setMuteCallback',
            'setPowerCallback',
            'setIncVolumeCallback',
            'setDecVolumeCallback',
            ]

# 定义按键
BUTTON_POWER        = 8     # Key4 - 电源
BUTTON_INC_VOLUME   = 25    # Key3 - 音量增加
BUTTON_DEC_VOLUME   = 24    # Key2 - 音量减少
BUTTON_MUTE         = 23    # Key1 - 关闭自动接入

BUTTON_PLAY         =  7    # 播放
BUTTON_CALL         = 16    # 呼叫

# 局部变量
_buttonInited       = False
_cbButtonPower      = None  # 电源按键回调函数指针
_cbButtonIncVolume  = None  # 音量增加按键回调函数指针
_cbButtonDecVolume  = None  # 音量减少按键回调函数指针
_cbButtonMute       = None  # 关闭自动接入按键回调函数指针
_cbButtonPlay       = None  # 播放按键回调函数指针
_cbButtonCall       = None  # 呼叫按键回调函数指针


# 按键处理回调函数
def cbButton(chan):
    global _cbButtonPower, _cbButtonIncVolume, _cbButtonDecVolume, _cbButtonMute, _cbButtonPlay, _cbButtonCall

    if chan == BUTTON_PLAY:         # 播放按键
        if _cbButtonPlay:
            _cbButtonPlay()
        else:
            logging.debug('pressed button: \"PLAY\".')
    elif chan == BUTTON_MUTE:       # 关闭自动接入按键
        if _cbButtonMute:
            _cbButtonMute()
        else:
            logging.debug('pressed button: \"MUTE\".')
    elif chan == BUTTON_INC_VOLUME: # 音量增加按键
        if _cbButtonIncVolume:
            _cbButtonIncVolume()
        else:
            logging.debug('pressed button: \"VOLUME INC\".')
    elif chan == BUTTON_DEC_VOLUME: # 音量减少按键
        if _cbButtonDecVolume:
            _cbButtonDecVolume()
        else:
            logging.debug('pressed button: \"VOLUME DEC\".')
    elif chan == BUTTON_CALL:       # 呼叫按键
        if _cbButtonCall:
            _cbButtonCall()
        else:
            logging.debug('pressed button: \"CALL\".')
    elif chan == BUTTON_POWER:      # 电源按键
        if _cbButtonPower:
            _cbButtonPower()
        else:
            logging.debug('pressed button: \"POWER\".')


# 初始化按键
def init():
    global _buttonInited, _cbButtonPower, _cbButtonIncVolume, _cbButtonDecVolume, _cbButtonMute, _cbButtonPlay, _cbButtonCall

    logging.debug('buttonAPI.init().')
    if not _buttonInited:
        _buttonInited       = True
        _cbButtonPlay       = None
        _cbButtonMute       = None
        _cbButtonCall       = None
        _cbButtonPower      = None
        _cbButtonIncVolume  = None
        _cbButtonDecVolume  = None

        logging.debug('initialize button gpio.')

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(BUTTON_PLAY,       GPIO.IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(BUTTON_MUTE,       GPIO.IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(BUTTON_CALL,       GPIO.IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(BUTTON_POWER,      GPIO.IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(BUTTON_INC_VOLUME, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        GPIO.setup(BUTTON_DEC_VOLUME, GPIO.IN, pull_up_down = GPIO.PUD_UP)

        GPIO.add_event_detect(BUTTON_PLAY,       GPIO.FALLING, callback = cbButton, bouncetime = 5)
        GPIO.add_event_detect(BUTTON_MUTE,       GPIO.FALLING, callback = cbButton, bouncetime = 5)
        GPIO.add_event_detect(BUTTON_CALL,       GPIO.FALLING, callback = cbButton, bouncetime = 5)
        GPIO.add_event_detect(BUTTON_POWER,      GPIO.FALLING, callback = cbButton, bouncetime = 5)
        GPIO.add_event_detect(BUTTON_INC_VOLUME, GPIO.FALLING, callback = cbButton, bouncetime = 5)
        GPIO.add_event_detect(BUTTON_DEC_VOLUME, GPIO.FALLING, callback = cbButton, bouncetime = 5)


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
