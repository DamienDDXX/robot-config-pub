#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import platform
import logging

if __name__ == '__main__':
    import sys
    import time
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

# 全局变量
_buttonInited = False

# 按键接口类
class buttonAPI(object):
    # 初始化
    def __init__(self):
        global _buttonInited
        if not _buttonInited:
            _buttonInited = True

            self._buttonTime        = time.time()

            self._cbButtonPlay      = None    # 播放按键回调函数指针
            self._cbButtonMute      = None    # 自动接入按键回调函数指针
            self._cbButtonCall      = None    # 呼叫按键回调函数指针
            self._cbButtonPower     = None    # 电源按键回调函数指针
            self._cbButtonIncVolume = None    # 音量增加按键回调函数指针
            self._cbButtonDecVolume = None    # 音量减少按键回调函数指针
            if platform.system().lower() == 'windows':
                self._cbButtonImx   = None    # 视频模拟按键回调函数指针
                self._cbButtonRadio = None    # 广播模拟按键回调函数指针
                self._pressed       = False

            if platform.system().lower() == 'linux':
                # 初始化按键端口及回调函数
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                buttonList = [ BUTTON_PLAY, BUTTON_MUTE, BUTTON_CALL, BUTTON_POWER, BUTTON_INC_VOLUME, BUTTON_DEC_VOLUME ]
                for button in buttonList:
                    GPIO.setup(button, GPIO.IN, pull_up_down = GPIO.PUD_UP)
                    GPIO.add_event_detect(button, GPIO.FALLING, callback = self.callback, bouncetime = 10)
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
        self._cbButtonPlay, cb = cb, self._cbButtonPlay
        return cb

    # 设置呼叫按键处理回调函数
    def setCallCallback(self, cb):
        self._cbButtonCall, cb = cb, self._cbButtonCall
        return cb

    # 设置关闭自动接入按键处理回调函数
    def setMuteCallback(self, cb):
        self._cbButtonMute, cb = cb, self._cbButtonMute
        return cb

    # 设置电源按键处理回调函数
    def setPowerCallback(self, cb):
        self._cbButtonPower, cb = cb, self._cbButtonPower
        return cb

    # 设置音量增加键处理回调函数
    def setIncVolumeCallback(self, cb):
        self._cbButtonIncVolume, cb = cb, self._cbButtonIncVolume
        return cb

    # 设置音量减少键处理回调函数
    def setDecVolumeCallback(self, cb):
        self._cbButtonDecVolume, cb = cb, self._cbButtonDecVolume
        return cb

    if platform.system().lower() == 'linux':
        # 按键回调函数
        def callback(self, chan):
            if time.time() - self._buttonTime < 0.3:
                self._buttonTime = time.time()
                return
            self._buttonTime = time.time()

            if  chan == BUTTON_PLAY and self._cbButtonPlay:
                self._cbButtonPlay()
            elif chan == BUTTON_MUTE and self._cbButtonMute:
                self._cbButtonMute()
            elif chan == BUTTON_CALL and self._cbButtonCall:
                self._cbButtonCall()
            elif chan == BUTTON_POWER and self._cbButtonPower:
                self._cbButtonPower()
            elif chan == BUTTON_INC_VOLUME and self._cbButtonIncVolume:
                self._cbButtonIncVolume()
            elif chan == BUTTON_DEC_VOLUME and self._cbButtonDecVolume:
                self._cbButtonDecVolume()

    elif platform.system().lower() == 'windows':
        # 设置视频模拟键处理回调函数
        def setImxCallback(self, cb):
            self._cbButtonImx, cb = cb, self._cbButtonImx
            return cb

        # 设置广播模拟键处理回调函数
        def setRadioCallback(self, cb):
            self._cbButtonRadio, cb = cb, self._cbButtonRadio
            return cb

        # 按下回调函数
        def onButtonDown(self, event):
            if not self._pressed:
                self._pressed = True
                if event.Key == BUTTON_POWER and self._cbButtonPower:
                    self._cbButtonPower()
                elif event.Key == BUTTON_INC_VOLUME and self._cbButtonIncVolume:
                    self._cbButtonIncVolume()
                elif event.Key == BUTTON_DEC_VOLUME and self._cbButtonDecVolume:
                    self._cbButtonDecVolume()
                elif event.Key == BUTTON_MUTE and self._cbButtonMute:
                    self._cbButtonMute()
                elif event.Key == BUTTON_PLAY and self._cbButtonPlay:
                    self._cbButtonPlay()
                elif event.Key == BUTTON_CALL and self._cbButtonCall:
                    self._cbButtonCall()
                elif event.Key == BUTTON_IMX and self._cbButtonImx:
                    self._cbButtonImx()
                elif event.Key == BUTTON_RADIO and self._cbButtonRadio:
                    self._cbButtonRadio()
            return True

        # 抬起回调函数
        def onButtonUp(self, event):
            self._pressed = False
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

    else:
        raise NotImplementedError


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
