#!/usr/bin/python
# -*- coding: utf8 -*-

import pyaudio
import wave
import os
import sys

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
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(wavFile, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()


# 播放
def audioPlay(wavFile):
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

    stream.stop_stream()
    stream.close()
    p.terminate()
    wf.close()


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
