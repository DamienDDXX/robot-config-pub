#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import pyaudio, wave
import os, sys, platform
from multiprocessing import Process

__all__ = [
        'audioRecord',
        ]

CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5

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
    while True:
        audioPlay(wavFile)

# 播放启动音效
def soundStartup():
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\startup.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/startup.wav')
    else:
        sound = None

    if sound and os.path.isfile(sound):
        p = Process(target = audioPlay, args = (sound, ))
        p.start()
        return p
    return None

# 播放连接成功音效
def soundConnected():
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\connected.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/connected.wav')
    else:
        sound = None

    if sound and os.path.isfile(sound):
        p = Process(target = audioPlay, args = (sound, ))
        p.start()
        return p
    return None

# 播放掉线音效
def soundOffline():
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\offline.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/offline.wav')
    else:
        sound = None

    if sound and os.path.isfile(sound):
        p = Process(target = audioPlay, args = (sound, ))
        p.start()
        return p
    return None

# 播放异常音效
def soundException():
    if platform.system().lower() == 'windows':
        sound = os.path.join(base_dir, '..\static\mp3\\exception.wav')
    elif platform.system().lower() == 'linux':
        sound = os.path.join(base_dir, '../static/mp3/exception.wav')
    else:
        sound = None

    if sound and os.path.isfile(sound):
        p = Process(target = audioPlay, args = (sound, ))
        p.start()
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
        p.start()
        return p
    return None


################################################################################
# 测试程序
if __name__ == '__main__':
    p = soundDudu()
    if p:
        time.sleep(20)
        if p.is_alive():
            print('terminate')
            p.terminate()
