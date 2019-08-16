#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import random
import platform

from manager import mp3Manager
if platform.system().lower() == 'linux':
    from manager import buttonManager, bandManager

base_dir = os.path.dirname(os.path.abspath(__file__))


# 局部变量
_buttonArray = []
_cbButtonPower = None
_cbButtonMute = None
_cbButtonCall = None
_cbButtonPlay = None
_cbButtonIncVolume = None
_cbButtonDecVolume = None


# radio, 测试扬声器
def enter_radio_test_env():
    return True, 'OK'


def exit_radio_test_env():
    return True, 'OK'


def start_test_radio():
    mp3_file = os.path.join(base_dir, '..\static\mp3\\bird.wav')
    mp3Manager.mp3TestStart(mp3_file)
    return True, 'OK'


def stop_test_radio():
    mp3Manager.mp3TestStop()
    return True, 'OK'


# audio, 测试麦克风
def enter_audio_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def exit_audio_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def start_recording_audio():
    # start recording audio
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def stop_recording_audio():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def play_recorded_audio():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


# monitor, 测试液晶屏
def enter_monitor_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def exit_monitor_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def start_test_monitor():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def stop_test_monitor():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


# 测试按键
def button_record(button):
    global _buttonArray
    if button not in _buttonArray:
        _buttonArray.append(button)
    else:
        _buttonArray.remove(button)


def button_power():
    button_record('电源键')


def button_mute():
    button_record('接入模式键')


def button_call():
    button_record('呼叫键')


def button_play():
    button_record('播放键')


def button_inc_volume():
    button_record('增加音量键')


def button_dec_volume():
    button_record('增加音量键')


def enter_keypad_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        global _buttonArray, _cbButtonPower, _cbButtonMute, _cbButtonCall, _cbButtonPlay, _cbButtonIncVolume, _cbButtonDecVolume
        buttonManager.buttonInit()
        _buttonArray       = []
        _cbButtonPower     = buttonManager.buttonPowerSetCallback(button_power)
        _cbButtonMute      = buttonManager.buttonMuteSetCallback(button_mute)
        _cbButtonCall      = buttonManager.buttonCallSetCallback(button_call)
        _cbButtonPlay      = buttonManager.buttonPlaySetCallback(button_play)
        _cbButtonIncVolume = buttonManager.buttonIncVolumeSetCallback(button_inc_volume)
        _cbButtonDecVolume = buttonManager.buttonDecVolumeSetCallback(button_dec_volume)
        return True, 'OK'
    else:
        return True, 'OK'


def exit_keypad_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        global _buttonArray, _cbButtonPower, _cbButtonMute, _cbButtonCall, _cbButtonPlay, _cbButtonIncVolume, _cbButtonDecVolume
        buttonManager.buttonPowerSetCallback(_cbButtonPower)
        buttonManager.buttonMuteSetCallback(_cbButtonMute)
        buttonManager.buttonCallSetCallback(_cbButtonCall)
        buttonManager.buttonPlaySetCallback(_cbButtonPlay)
        buttonManager.buttonIncVolumeSetCallback(_cbButtonIncVolume)
        buttonManager.buttonDecVolumeSetCallback(_cbButtonDecVolume)
        return True, 'OK'
    else:
        return True, 'OK'


def get_keypad_strings():
    if platform.system().lower() == 'windows':
        arr = ['呼叫键', '音量增加', '音量减少', '功能键']
        num = random.randint(1, 5)
        random.shuffle(arr)
        return True, arr[0: num]
    elif platform.system().lower() == 'linux':
        global _buttonArray
        return True, _buttonArray
    else:
        return True, 'OK'


# camera, 测试摄像头
def enter_camera_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def exit_camera_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, 'OK'
    else:
        return True, 'OK'


def capture_camera():
    # invoke api to capture image and return image data
    if platform.system().lower() == 'windows':
        return True, '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'
    elif platform.system().lower() == 'linux':
        # TODO
        return True, ''
    else:
        return True, ''
