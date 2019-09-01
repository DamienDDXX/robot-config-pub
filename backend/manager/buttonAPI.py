#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import platform
import logging

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from utility import setLogging

if platform.system().lower() == 'linux':
    import RPi.GPIO as GPIO
elif platform.system().lower() == 'windows':
    import pyHook
    import pythoncom
    import threading
else:
    raise NotImplementedError


__all__ = [
            'buttonAPI',
            ]

# 定义按键
if platform.system().lower() == 'linux':
    BUTTON_POWER        = 23    # 电源
    BUTTON_INC_VOLUME   = 24    # 音量增加
    BUTTON_DEC_VOLUME   = 25    # 音量减少
    BUTTON_MUTE         = 8     # 关闭自动接入

    BUTTON_PLAY         = 7     # 播放
    BUTTON_CALL         = 16    # 呼叫
elif platform.system().lower() == 'windows':
    BUTTON_POWER        = 'R'   # 'r' - 电源
    BUTTON_INC_VOLUME   = 'I'   # 'i' - 音量增加
    BUTTON_DEC_VOLUME   = 'D'   # 'd' - 音量减少
    BUTTON_MUTE         = 'M'   # 'm' - 接入模式

    BUTTON_PLAY         = 'P'   # 'p' - 播放
    BUTTON_CALL         = 'C'   # 'c' - 呼叫

    BUTTON_IMX          = 'X'   # 'x' - 模拟视频呼入
    BUTTON_RADIO        = 'U'   # 'u' - 模拟广播播放
else:
    raise NotImplementedError

# 局部变量
_buttonTime = time.time()
_buttonInited = False

_cbButtonPlay = None        # 播放按键回调函数指针
_cbButtonMute = None        # 自动接入按键回调函数指针
_cbButtonCall = None        # 呼叫按键回调函数指针
_cbButtonPower = None       # 电源按键回调函数指针
_cbButtonIncVolume = None   # 音量增加按键回调函数指针
_cbButtonDecVolume = None   # 音量减少按键回调函数指针
if platform.system().lower() == 'windows':
    _cbButtonImx = None     # 视频模拟按键回调函数指针
    _cbButtonRadio = None   # 广播模拟按键回调函数指针
    _pressed = False

# 按键回调函数
def cbButton(chan):
    global _buttonTime
    global _cbButtonPlay, _cbButtonMute, _cbButtonCall, _cbButtonPower, _cbButtonIncVolume, _cbButtonDecVolume
    if time.time() - _buttonTime < 0.3:
        _buttonTime = time.time()
        return
    _buttonTime = time.time()

    if  chan == BUTTON_PLAY and _cbButtonPlay:
        _cbButtonPlay()
    elif chan == BUTTON_MUTE and _cbButtonMute:
        _cbButtonMute()
    elif chan == BUTTON_CALL and _cbButtonCall:
        _cbButtonCall()
    elif chan == BUTTON_POWER and _cbButtonPower:
        _cbButtonPower()
    elif chan == BUTTON_INC_VOLUME and _cbButtonIncVolume:
        _cbButtonIncVolume()
    elif chan == BUTTON_DEC_VOLUME and _cbButtonDecVolume:
        _cbButtonDecVolume()

# 按键接口类
class buttonAPI(object):
    # 初始化
    def __init__(self):
        if platform.system().lower() == 'linux':
            global _buttonInited
            if not _buttonInited:
                _buttonInited = True    # 避免重复初始化

                # 初始化按键端口及回调函数
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                buttonList = [ BUTTON_PLAY, BUTTON_MUTE, BUTTON_CALL, BUTTON_POWER, BUTTON_INC_VOLUME, BUTTON_DEC_VOLUME ]
                for button in buttonList:
                    GPIO.setup(button, GPIO.IN, pull_up_down = GPIO.PUD_UP)
                    GPIO.add_event_detect(button, GPIO.FALLING, callback = cbButton, bouncetime = 10)
        elif platform.system().lower() == 'windows':
            # 启动按键模拟线程
            self._finiEvent = threading.Event()
            self._finiEvent.clear()
            self._thread = threading.Thread(target = self.simThread)
            self._thread.start()
        else:
            raise NotImplementedError

    # 设置播放按键处理回调函数
    def setPlayCallback(self, cb):
        global _cbButtonPlay
        _cbButtonPlay, cb = cb, _cbButtonPlay
        return cb

    # 设置呼叫按键处理回调函数
    def setCallCallback(self, cb):
        global _cbButtonCall
        _cbButtonCall, cb = cb, _cbButtonCall
        return cb

    # 设置关闭自动接入按键处理回调函数
    def setMuteCallback(self, cb):
        global _cbButtonMute
        _cbButtonMute, cb = cb, _cbButtonMute
        return cb

    # 设置电源按键处理回调函数
    def setPowerCallback(self, cb):
        global _cbButtonPower
        _cbButtonPower, cb = cb, _cbButtonPower
        return cb

    # 设置音量增加键处理回调函数
    def setIncVolumeCallback(self, cb):
        global _cbButtonIncVolume
        _cbButtonIncVolume, cb = cb, _cbButtonIncVolume
        return cb

    # 设置音量减少键处理回调函数
    def setDecVolumeCallback(self, cb):
        global _cbButtonDecVolume
        _cbButtonDecVolume, cb = cb, _cbButtonDecVolume
        return cb

    if platform.system().lower() == 'windows':
        # 设置视频模拟键处理回调函数
        def setImxCallback(self, cb):
            global _cbButtonImx
            _cbButtonImx, cb = cb, _cbButtonImx
            return cb

        # 设置广播模拟键处理回调函数
        def setRadioCallback(self, cb):
            global _cbButtonRadio
            _cbButtonRadio, cb = cb, _cbButtonRadio
            return cb

        # 按下回调函数
        def onButtonDown(self, event):
            global _pressed
            global _cbButtonPower, _cbButtonIncVolume, _cbButtonDecVolume, _cbButtonMute, _cbButtonPlay, _cbButtonCall, _cbButtonImx, _cbButtonRadio
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
                elif event.Key == BUTTON_RADIO and _cbButtonRadio:
                    _cbButtonRadio()
            return True

        # 抬起回调函数
        def onButtonUp(self, event):
            global _pressed
            _pressed = False
            return True

        # 按键模拟线程
        def simThread(self):
            logging.debug('buttonAPI.simThread().')
            hm = pyHook.HookManager()
            hm.KeyDown = self.onButtonDown
            hm.KeyUp   = self.onButtonUp
            hm.HookKeyboard()
            pythoncom.PumpMessages()
            self._finiEvent.Wait()
            self._thread = None
            logging.debug('buttonAPI.simThread() fini.')

        # 终止模拟线程
        def fini(self):
            logging.debug('buttonAPI.fini().')
            if self._thread:
                self._finiEvent.set()


################################################################################
# 测试程序
def testCallback():
    logging.debug('buttonAPI.testCallback().')

if __name__ == '__main__':
    button = buttonAPI()
    button.setPlayCallback(testCallback)
    button.setCallCallback(testCallback)
    button.setMuteCallback(testCallback)
    button.setPowerCallback(testCallback)
    button.setDecVolumeCallback(testCallback)
    button.setIncVolumeCallback(testCallback)
    if platform.system().lower() == 'windows':
        button.setImxCallback(testCallback)
        button.setRadioCallback(testCallback)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if platform.system().lower() == 'windows':
            button.fini()
    finally:
        if platform.system().lower() == 'windows':
            while button._thread:
                time.sleep(1)
        logging.debug('Quit by user...')
