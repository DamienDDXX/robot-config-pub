#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import time
import random
import platform

from utility import audioRecord, camera
from manager.buttonAPI import buttonAPI
from manager.lcdAPI import lcdAPI

base_dir = os.path.dirname(os.path.abspath(__file__))


# 局部变量
_buttonArray   = []
_buttonAPI     = None
_cbButtonPower = None
_cbButtonMute  = None
_cbButtonCall  = None
_cbButtonPlay  = None
_cbButtonIncVolume = None
_cbButtonDecVolume = None

_lcdAPI = None

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
        global _lcdAPI
        if not _lcdAPI:
            _lcdAPI = lcdAPI()
        return True, 'OK'
    else:
        return True, 'OK'


def exit_monitor_test_env():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        return True, 'OK'
    else:
        return True, 'OK'


def start_test_monitor():
    if platform.system().lower() == 'windows':
        return True, 'OK'
    elif platform.system().lower() == 'linux':
        global _lcdAPI
        if not _lcdAPI:
            _lcdAPI = lcdAPI()
        time.sleep(1)
        _lcdAPI.backlit_off()       # 关闭背光
        time.sleep(1)
        _lcdAPI.backlit_on()        # 打开背光
        time.sleep(1)
        _lcdAPI.page_logo()
        time.sleep(1)
        _lcdAPI.page_wait()
        time.sleep(1)
        _lcdAPI.page_blink()
        time.sleep(1)
        _lcdAPI.page_fail()
        time.sleep(1)
        _lcdAPI.page_happy()
        time.sleep(1)
        _lcdAPI.page_listen()
        time.sleep(1)
        _lcdAPI.page_sad()
        time.sleep(1)
        _lcdAPI.page_smile()
        time.sleep(1)
        _lcdAPI.page_logo()
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
    global _buttonAPI, _buttonArray, _cbButtonPower, _cbButtonMute, _cbButtonCall, _cbButtonPlay, _cbButtonIncVolume, _cbButtonDecVolume
    if not _buttonAPI:
        _buttonAPI = buttonAPI()
    _buttonArray       = []
    _cbButtonPower     = _buttonAPI.setPowerCallback(button_power)
    _cbButtonMute      = _buttonAPI.setMuteCallback(button_mute)
    _cbButtonCall      = _buttonAPI.setCallCallback(button_call)
    _cbButtonPlay      = _buttonAPI.setPlayCallback(button_play)
    _cbButtonIncVolume = _buttonAPI.setIncVolumeCallback(button_inc_volume)
    _cbButtonDecVolume = _buttonAPI.setDecVolumeCallback(button_dec_volume)
    return True, 'OK'


def exit_keypad_test_env():
    global _buttonAPI, _buttonArray, _cbButtonPower, _cbButtonMute, _cbButtonCall, _cbButtonPlay, _cbButtonIncVolume, _cbButtonDecVolume
    if not _buttonAPI:
        _buttonAPI = buttonAPI()
    _buttonAPI.setPowerCallback(_cbButtonPower)
    _buttonAPI.setMuteCallback(_cbButtonMute)
    _buttonAPI.setCallCallback(_cbButtonCall)
    _buttonAPI.setPlayCallback(_cbButtonPlay)
    _buttonAPI.setIncVolumeCallback(_cbButtonIncVolume)
    _buttonAPI.setDecVolumeCallback(_cbButtonDecVolume)
    return True, 'OK'


def get_keypad_strings():
    global _buttonArray
    return True, _buttonArray


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
