#!/usr/bin/python
# -*- coding: utf8 -*-


import RPi.GPIO as GPIO
import time
import threading
import logging


__all__ = [
            'buttonInit',
            'buttonPlaySetCallback',
            'buttonMuteSetCallback',
            'buttonCallSetCallback',
            'buttonPowerSetCallback',
            'buttonIncVolumeSetCallback',
            'buttonDecVolumeSetCallback',
            ]

logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(levelname)s- %(message)s')

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

    if chan == BUTTON_PLAY:
        # 播放按键
        logging.debug('pressed button: \"PLAY\".')
        if _cbButtonPlay:
            _cbButtonPlay()

    elif chan == BUTTON_MUTE:
        # 关闭自动接入按键
        logging.debug('pressed button: \"MUTE\".')
        if _cbButtonMute:
            _cbButtonMute()

    elif chan == BUTTON_INC_VOLUME:
        # 音量增加按键
        logging.debug('pressed button: \"VOLUME INC\".')
        if _cbButtonIncVolume:
            _cbButtonIncVolume()

    elif chan == BUTTON_DEC_VOLUME:
        # 音量减少按键
        logging.debug('pressed button: \"VOLUME DEC\".')
        if _cbButtonDecVolume:
            _cbButtonDecVolume()

    elif chan == BUTTON_CALL:
        # 呼叫按键
        logging.debug('pressed button: \"CALL\".')
        if _cbButtonCall:
            _cbButtonCall()

    elif chan == BUTTON_POWER:
        # 电源按键
        logging.debug('pressed button: \"POWER\".')
        if _cbButtonPower:
            _cbButtonPower()


# 初始化按键
def buttonInit():
    global _buttonInited, _cbButtonPower, _cbButtonIncVolume, _cbButtonDecVolume, _cbButtonMute, _cbButtonPlay, _cbButtonCall

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
def buttonPlaySetCallback(cb):
    global _cbButtonPlay
    _cbButtonPlay, cb = cb, _cbButtonPlay
    return cb


# 设置呼叫按键处理回调函数
def buttonCallSetCallback(cb):
    global _cbButtonCall
    _cbButtonCall, cb = cb, _cbButtonCall
    return cb


# 设置关闭自动接入按键处理回调函数
def buttonMuteSetCallback(cb):
    global _cbButtonMute
    _cbButtonMute, cb = cb, _cbButtonMute
    return cb


# 设置电源按键处理回调函数
def buttonPowerSetCallback(cb):
    global _cbButtonPower
    _cbButtonPower, cb = cb, _cbButtonPower
    return cb


# 设置音量增加键处理回调函数
def buttonIncVolumeSetCallback(cb):
    global _cbButtonIncVolume
    _cbButtonIncVolume, cb = cb, _cbButtonIncVolume
    return cb


# 设置音量减少键处理回调函数
def buttonDecVolumeSetCallback(cb):
    global _cbButtonDecVolume
    _cbButtonDecVolume, cb = cb, _cbButtonDecVolume
    return cb


# 回调函数测试
def testCallback():
    logging.debug('test callback.')


# 执行代码
if __name__ == '__main__':
    buttonInit()
    buttonPlaySetCallback(testCallback)
    buttonCallSetCallback(testCallback)
    buttonMuteSetCallback(testCallback)
    buttonPowerSetCallback(testCallback)
    buttonDecVolumeSetCallback(testCallback)
    buttonIncVolumeSetCallback(testCallback)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
