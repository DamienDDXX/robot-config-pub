#!/usr/bin/python
# -*- coding: utf8 -*-

import pyaudio, wave
import os, sys, platform

__all__ = [
        'audioRecord',
        ]

CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5


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


if __name__ == '__main__':
    wavFile = '/home/pi/robot-config/backend/static/mp3/bird.wav'
    audioPlay(wavFile)
    """
    wavFile = 'test.wav'
    if os.path.isfile(wavFile):
        try:
            os.remove(wavFile)
        except:
            pass
    audioRecord(wavFile, 5)
    audioPlay(wavFile)
    if os.path.isfile(wavFile):
        try:
            os.remove(wavFile)
        except:
            pass
    """
