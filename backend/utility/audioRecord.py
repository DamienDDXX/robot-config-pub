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

CAPTURE_VALUE = 60
PLAYBACK_LIST = [ 0, 100, 137, 155, 172, 184, 192, 200, 208, 214, 220, 224, 228, 233, 237, 240, 244, 247, 249, 250, 251 ]

base_dir = os.path.dirname(os.path.abspath(__file__))

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
            os.system('arecord -Dhw:0 -d 5 -f cd -r 44100 -c 2 -t wav %s' %wavFile)
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

# 播放启动音效
def soundStartup(wait):
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\startup.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/startup.wav')
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

# 播放连接成功音效
def soundConnected(wait):
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\connected.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/connected.wav')
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

# 播放掉线音效
def soundOffline(wait):
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\offline.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/offline.wav')
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

# 播放异常音效
def soundException(wait):
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\exception.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/exception.wav')
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
        os.system('amixer -c 0 cset numid=1 %d' %CAPTURE_VALUE)  # 设置麦克风灵敏度
        os.system('amixer -c 1 cset numid=1 %d' %CAPTURE_VALUE)  # 设置麦克风灵敏度
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
        os.system('amixer -c 0 cset numid=10 %d' %playback) # 设置播放音量
        os.system('amixer -c 1 cset numid=10 %d' %playback) # 设置播放音量
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
            os.system('amixer -c 0 cset numid=10 %d' %playback) # 设置播放音量
            os.system('amixer -c 1 cset numid=10 %d' %playback) # 设置播放音量
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
            os.system('amixer cset numid=10 %d' %playback) # 设置播放音量
    finally:
        pass


################################################################################
# 测试程序
if __name__ == '__main__':
    captureInit()
    volumeInit()
    incVolume()
    incVolume()
