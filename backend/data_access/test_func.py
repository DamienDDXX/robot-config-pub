#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import random
import platform

from utility import audioRecord, camera
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
def make_radio_filename():
    if platform.system().lower() == 'windows':
        radio_file = os.path.join(base_dir, '..\static\mp3\\bird.wav')
    elif platform.system().lower() == 'linux':
        radio_file = os.path.join(base_dir, '../static/mp3/bird.wav')
    else:
        radio_file = None
    return radio_file


def enter_radio_test_env():
    return True, 'OK'


def exit_radio_test_env():
    return True, 'OK'


def start_test_radio():
    radio_file = make_radio_filename()
    if radio_file:
        if os.path.isfile(radio_file):
            audioRecord.audioPlay(radio_file)
    return True, 'OK'


def stop_test_radio():
    return True, 'OK'


# audio, 测试麦克风
def make_audio_filename():
    if platform.system().lower() == 'windows':
        audio_file = os.path.join(base_dir, '..\static\mp3\\test.wav')
    elif platform.system().lower() == 'linux':
        audio_file = os.path.join(base_dir, '../static/mp3/test.wav')
    else:
        audio_file = None
    return audio_file


def remove_audio_file():
    audio_file = make_audio_filename()
    if audio_file:
        if os.path.isfile(audio_file):
            try:
                os.remove(audio_file)
            except:
                pass


def enter_audio_test_env():
    remove_audio_file()
    return True, 'OK'


def exit_audio_test_env():
    remove_audio_file()
    return True, 'OK'


def start_recording_audio():
    remove_audio_file()
    audio_file = make_audio_filename()
    audioRecord.audioRecord(audio_file, 5)
    return True, 'OK'


def stop_recording_audio():
    return True, 'OK'


def play_recorded_audio():
    audio_file = make_audio_filename()
    if os.path.isfile(audio_file):
        audioRecord.audioPlay(audio_file)
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
    button_record('减少音量键')


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
def make_picture_filename():
    if platform.system().lower() == 'windows':
        pic_file = os.path.join(base_dir, '..\static\img\\camera.jpg')
    elif platform.system().lower() == 'linux':
        pic_file = os.path.join(base_dir, '../static/img/camera.jpg')
    else:
        pic_file = None
    return pic_file


def remove_picture_file():
    pic_file = make_picture_filename()
    if pic_file:
        if os.path.isfile(pic_file):
            try:
                os.remove(pic_file)
            except:
                pass
    return True, 'OK'


def enter_camera_test_env():
    remove_picture_file()
    return True, 'OK'


def exit_camera_test_env():
    remove_picture_file()
    return True, 'OK'


def capture_camera():
    pic_file = make_picture_filename()
    if pic_file:
        if camera.capturePicture(pic_file):
            return True, camera.pictureToBase64(pic_file)
    return True, ''
