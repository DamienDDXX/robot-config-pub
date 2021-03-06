#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import pyaudio, wave
import os, sys, platform
from multiprocessing import Process

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from data_access import volume

__all__ = [
        'audioRecord',
        ]

CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5

CAPTURE_VALUE = 40
PLAYBACK_LIST = [ 0, 100, 137, 155, 172, 184, 192, 200, 208, 214, 220, 224, 228, 233, 237, 240, 244, 247, 249, 250, 251 ]

base_dir = os.path.dirname(os.path.abspath(__file__))

# 获取声卡编号
def soundCard():
    fd = os.popen('aplay -l | grep seeed2micvoicec')
    content = fd.read()
    fd.close()
    if 'card 0' in content:
        return True, 0
    elif 'card 1' in content:
        return True, 1
    return False, None

# 录音
def audioRecord(wavFile, seconds):
    if platform.system().lower() == 'windows':
        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format = FORMAT,
                            channels = CHANNELS,
                            rate = RATE,
                            input = True,
                            frames_per_buffer = CHUNK)
            frames = []
            for i in range(0, int(RATE / CHUNK * seconds)):
                data = stream.read(CHUNK)
                frames.append(data)
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if p:
                p.terminate()

        wf = None
        try:
            wf = wave.open(wavFile, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        finally:
            if wf:
                wf.close()
    elif platform.system().lower() == 'linux':
        try:
            ret, card = soundCard()
            if ret:
                os.system('arecord -Dhw:%d -d 5 -f cd -r 44100 -c 2 -t wav %s' %(card, wavFile))
        finally:
            pass
    else:
        pass

# 播放
def audioPlay(wavFile):
    if platform.system().lower() == 'windows':
        wf = None
        p = None
        stream = None
        try:
            wf = wave.open(wavFile, 'rb')
            p = pyaudio.PyAudio()
            stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                            channels = wf.getnchannels(),
                            rate=wf.getframerate(),
                            output = True)
            data = wf.readframes(CHUNK)
            while data != '':
                stream.write(data)
                data = wf.readframes(CHUNK)

        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if p:
                p.terminate()
            if wf:
                wf.close()
    elif platform.system().lower() == 'linux':
        try:
            os.system('aplay %s' %wavFile)
        finally:
            pass
    else:
        pass

# 循环播放音频
def audioPlayLoop(wavFile):
    wf = None
    p = None
    stream = None
    try:
        wf = wave.open(wavFile, 'rb')
        p = pyaudio.PyAudio()
        while True:
            stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                            channels = wf.getnchannels(),
                            rate=wf.getframerate(),
                            output = True)
            data = wf.readframes(CHUNK)
            while data != '':
                stream.write(data)
                data = wf.readframes(CHUNK)
            stream.stop_stream()
            stream.close()
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if p:
            p.terminate()
        if wf:
            wf.close()

# 播放音效
def soundPlay(wavFile, wait):
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\%s' %wavFile)
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/%s' %wavFile)
    else:
        sound = None

    if sound and os.path.isfile(sound):
        p = Process(target = audioPlay, args = (sound, ))
        p.daemon = True
        p.start()
        if wait:
            while p.is_alive():
                time.sleep(0.1)
        return p
    return None

# 播放启动音效
def soundStartup(wait):
    p = soundPlay('startup.wav', wait)
    return p

# 播放连接成功音效
def soundConnected(wait):
    p = soundPlay('connected.wav', wait)
    return p

# 播放掉线音效
def soundOffline(wait):
    p = soundPlay('offline.wav', wait)
    return p

# 播放异常音效
def soundException(wait):
    p = soundPlay('exception.wav', wait)
    return p

# 播放打开自动接听模式音效
def soundAutoModeOn(wait):
    p = soundPlay('automode_on.wav', wait)
    return p

# 播放关闭自动接听模式音效
def soundAutoModeOff(wait):
    p = soundPlay('automode_off.wav', wait)
    return p

# 播放手环连接成功音效
def soundBandOk(wait):
    p = soundPlay('band_ok.wav', wait)
    return p

# 播放手环连接失败音效
def soundBandFail(wait):
    p = soundPlay('band_fail.wav', wait)
    return p

# 播放电话呼叫音效
def soundDudu():
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\dudu.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/dudu.wav')
    else:
        sound = None

    if sound and os.path.isfile(sound):
        p = Process(target = audioPlayLoop, args = (sound, ))
        p.daemon = True
        p.start()
        return p
    return None

# 初始化麦克风
def captureInit():
    global CAPTURE_VALUE
    try:
        ret, card = soundCard()
        if ret:
            os.system('amixer -c %d cset numid=1 %d' %(card, CAPTURE_VALUE))  # 设置麦克风灵敏度
    finally:
        pass

# 初始化音量
def volumeInit():
    global PLAYBACK_LIST
    try:
        playback = PLAYBACK_LIST[len(PLAYBACK_LIST) / 2]
        ret, v = volume.get_volume()
        if ret and v >= 0 and v < len(PLAYBACK_LIST):
            playback = PLAYBACK_LIST[v]
        else:
            v = len(PLAYBACK_LIST) / 2
            volume.set_volume(v)
        ret, card = soundCard()
        if ret:
            os.system('amixer -c %d cset numid=10 %d' %(card, playback)) # 设置播放音量
    finally:
        pass

# 增加音量
def incVolume():
    global PLAYBACK_LIST
    try:
        _, v = volume.get_volume()
        v = v + 1
        if v >= 0 and v < len(PLAYBACK_LIST):
            volume.set_volume(v)
            playback = PLAYBACK_LIST[v]
            ret, card = soundCard()
            if ret:
                os.system('amixer -c %d cset numid=10 %d' %(card, playback)) # 设置播放音量
    finally:
        pass

# 减少音量
def decVolume():
    global PLAYBACK_LIST
    try:
        _, v = volume.get_volume()
        v = v - 1
        if v >= 0 and v < len(PLAYBACK_LIST):
            volume.set_volume(v)
            playback = PLAYBACK_LIST[v]
            ret, card = soundCard()
            if ret:
                os.system('amixer -c %d cset numid=10 %d' %(card, playback)) # 设置播放音量
    finally:
        pass


################################################################################
# 测试程序
if __name__ == '__main__':
    soundStartup(True)
    soundOffline(True)
    soundConnected(True)
    soundException(True)
    soundAutoModeOn(False)
    time.sleep(1)
    soundAutoModeOff(False)
    time.sleep(1)
    soundBandOk(True)
    soundBandFail(True)
