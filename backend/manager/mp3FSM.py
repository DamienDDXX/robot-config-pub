#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import time
import requests
from pygame import mixer
import Queue
import string
import platform
import logging
import traceback
import threading
from transitions import Machine, State

if __name__ == '__main__':
    import sys
    sys.path.append('..')
    from manager.serverAPI import serverAPI
    from manager.buttonAPI import buttonAPI

from utility import setLogging

__all__ = [
        'mp3FSM',
        ]

# 常量定义
if platform.system().lower() == 'windows':
    MP3_DIR_ = os.getcwd()
elif platform.system().lower() == 'linux':
    MP3_DIR_ = '/ram'
else:
    raise NotImplementedError

MP3_FILE_URL_POSTFIX = '/medical/basic/file/download'   # 音频文件地址后缀

VOLUME_MIN  = 0.00
VOLUME_MAX  = 1.00
VOLUME_INV  = 0.05

# 音频状态机管理类
class mp3FSM(object):
    # 类初始化
    def __init__(self, hostName, portNumber, token, getMp3List, volume = 0.5, mp3Dir = MP3_DIR_):
        if platform.system().lower() == 'linux':
            # 挂载虚拟盘
            os.system('sudo mount -t tmpfs -o size=300m,mode=0777 tmpfs /ram')

        self._hostName = hostName
        self._portNumber = portNumber
        self._token = token
        self._getMp3Lsit = getMp3List
        self._playList = []
        self._fileList = []
        self._volume = volume
        self._mp3Dir = MP3_DIR_
        self._sound = None

        self._playThread = None
        self._playFiniEvent = threading.Event()
        self._playDoneEvent = threading.Event()

        self._updateThread = None
        self._updateFiniEvent = threading.Event()
        self._updateDoneEvent = threading.Event()

        self._states = [
            State(name = 'stateInit',   on_enter = 'actUpdate',     ignore_invalid_triggers = True),
            State(name = 'stateIdle',                               ignore_invalid_triggers = True),
            State(name = 'stateImx',                                ignore_invalid_triggers = True),
        ]
        self._transitions = [
            # 初始状态 ------->
            {
                'trigger':  'evtInitOk',
                'source':   'stateInit',
                'dest':     'stateIdle',
            },
            {
                'trigger':  'evtImxOn',
                'source':   'stateInit',
                'dest':     'stateImx',
                'before':   'actImxOn'
            },
            # 空闲状态 ------->
            {
                'trigger':  'evtImxOn',
                'source':   'stateIdle',
                'dest':     'stateImx',
                'before':   'actImxOn'
            },
            {
                'trigger':  'evtButtonPlay',
                'source':   'stateIdle',
                'dest':     'stateIdle',
                'before':   'actButtonPlay'
            },
            {
                'trigger':  'evtRadio',
                'source':   'stateIdle',
                'dest':     'stateIdle',
                'before':   'actRadio'
            },
            # 通话状态 ------->
            {
                'trigger':  'evtImxOff',
                'source':   'stateImx',
                'dest':     'stateIdle',
                'before':   'actImxOff'
            },
        ]

        self._machine = Machine(self, states = self._states, transitions = self._transitions, ignore_invalid_triggers = True)
        self._eventQueue = Queue.Queue(5)
        self._eventList = []
        self._fsmDoneEvent = threading.Event()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    # 音频管理状态机后台线程
    def fsmThread(self):
        logging.debug('mp3FSM.fsmThread().')
        try:
            self._fsmDoneEvent.clear()
            self.to_stateInit()
            while True:
                ret, desc, event = self.getEvent()
                if ret:
                    if desc == 'fini':
                        raise Exception('fini')
                    else:
                        event()
                        logging.debug('mp3FSM: state - %s' %self.state)
        finally:
            self.playFini(quit = True)
            self.updateFini()
            self._eventQueue.queue.clear()
            self._eventQueue = None
            del self._eventList[:]
            logging.debug('mp3FSM.fsmThread() fini.')
            self._fsmThread = None
            self._fsmDoneEvent.set()

    # 更新本地音频文件
    def updateFileLocal(self):
        logging.debug('mp3FSM.updateFileLocal().')
        try:
            ret = False
            del self._fileList[:]
            result = [(i, os.stat(i).st_mtime) for i in os.listdir(self._mp3Dir)]
            for i in sorted(result, key = lambda x : x[1]):
                fileName = i[0]
                postFix = string.split(fileName, '.')[-1].lower()
                if postFix == 'mp3':
                    fileId = string.split(fileName, '.')[0]
                    filePath = os.path.join(self._mp3Dir, fileName)
                    self._fileList.append({ 'fileId': fileId, 'filePath': filePath, 'pri': '0' })
            ret = True
        except:
            traceback.print_exc()
        finally:
            logging.debug('mp3FSM.updateFileLocal() %s.' %('success' if ret else 'failed'))
            return ret

    # 按优先级排序音频文件列表
    def sortFileList(self, mp3List):
        logging.debug('mp3FSM.sortFileList().')
        try:
            sortList = []
            priList = [ '1', '0' ]
            for pri in priList:
                for mp3 in mp3List:
                    postFix = ''
                    if 'fileName' in mp3 and mp3['fileName']:
                        postFix  = string.split(mp3['fileName'], '.')[-1].lower()
                    if 'fileId' in mp3 and mp3['fileId'] and 'pri' in mp3 and mp3['pri'] and postFix == 'mp3':
                        if pri == mp3['pri'] and mp3 not in sortList:
                            sortList.append(mp3)
        except:
            traceback.print_exc()
        finally:
            return sortList

    # 判定音频文件是否存在
    def fileExisted(self, fileId):
        for i in range(len(self._fileList)):
            if self._fileList[i]['fileId'] == fileId:
                return i
        return None

    # 更新音频文件
    def updateThread(self, cbUpdateDone):
        logging.debug('mp3FSM.updateThread().')
        try:
            self._updateDoneEvent.clear()
            self._updateFiniEvent.clear()
            ret, mp3List = self._getMp3Lsit()
            if ret:
                newList = []
                mp3List = self.sortFileList(mp3List)
                self.updateFileLocal()
                for mp3 in mp3List:
                    try:
                        fileId = str(mp3['fileId'])
                        index = self.fileExisted(fileId)
                        if index:
                            # 音频文件已经存在
                            self._fileList[index]['pri'] = str(mp3['pri'])
                            newList.append(self._fileList[index])
                        else:
                            # 音频文件不存在，需要重新下载
                            if not os.path.exists(self._mp3Dir):
                                logging.debug('make mp3 dir.')
                                os.mkdirs(self._mp3Dir)
                            fileUrl = self._hostName + ':' + self._portNumber + MP3_FILE_URL_POSTFIX + '?fileId=' + fileId
                            fileName = fileId + '.mp3'
                            filePath = os.path.join(self._mp3Dir, fileName)
                            logging.debug('mp3 path: %s' %filePath)
                            if not os.path.isfile(filePath):
                                logging.debug('download mp3 file: url - %s, token - %s' %(fileUrl, self._token))
                                headers = { 'access_token': self._token }
                                rsp = requests.get(fileUrl, headers = headers, stream = True, verify = False)
                                logging.debug('download mp3 file: rsp.status_code - %d', rsp.status_code)
                                if rsp.status_code == 200:
                                    with open(filePath, 'wb') as mp3File:
                                        for chunk in rsp.iter_content(chunk_size = 1024):
                                            if chunk:
                                                if self._updateFiniEvent.isSet():
                                                    raise Exception('fini')
                                                mp3File.write(chunk)
                                    logging.debug('download mp3 file done: url - %s' %fileUrl)
                            self._fileList.append({ 'fileId': fileId, 'filePath': filePath, 'pri': str(mp3['pri']) })
                            newList.append({ 'fileId': fileId, 'filePath': filePath, 'pri': str(mp3['pri']) })
                        if self.state == 'stateInit':
                            self.putEvent('evtInitOk', self.evtInitOk)   # 下载完成单个音频文件，通知状态机
                        if str(mp3['pri']) == '1':
                            self.putEvent('evtRadio', self.evtRadio)
                    except Exception, e:
                        if e.message == 'fini':
                            pass
                        else:
                            traceback.print_exc()
                    finally:
                        pass

                # 删除原有音频列表中不需要的文件
                for i in self._fileList:
                    try:
                        if i not in newList:
                            filePath = i['filePath']
                            if os.path.isfile(filePath):
                                os.remove(filePath)
                    except:
                        traceback.print_exc()
                    finally:
                        pass
                self._fileList = newList
                if cbUpdateDone:
                    cbUpdateDone()
        except:
            traceback.print_exc()
        finally:
            logging.debug('mp3FSM.updateThread() fini.')
            self._updateThread = None
            self._updateDoneEvent.set()

    # 清除所有广播文件
    def clearRadio(self):
        logging.debug('mp3FSM.clearRadio().')
        fileList = []
        for i in self._fileList:
            if i['pri'] == '0':
                fileList.append(i)
            else:
                filePath = i['filePath']
                if os.path.isfile(filePath):
                    try:
                        os.remove(filePath)
                    except:
                        traceback.print_exc()
                    finally:
                        pass
        self._fileList = fileList

    # 播放音频列表
    def playThread(self):
        logging.debug('mp3FSM.playThread().')
        try:
            self._playFiniEvent.clear()
            self._playDoneEvent.clear()
            if self._sound:                 # 播放音效
                if os.path.isfile(self._sound):
                    if not mixer.get_init():
                        mixer.init(frequency = 48000)
                    mixer.music.set_volume(self._volume * 0.5)
                    mixer.music.load(self._sound)
                    mixer.music.play(loops = -1, start = 0.0)
                    logging.debug('play mp3 file: %s, start - 0.000000.' %self._sound)
                    while True:
                        self._playFiniEvent.wait(0.5)
                        if self._playFiniEvent.isSet():
                            raise Exception('fini')
                        if self._volume != mixer.music.get_volume() * 2:
                            mixer.music.set_volume(self._volume * 0.5)
            else:                           # 播放音频
                while len(self._playList) > 0:
                    filePath = self._playList[0]['filePath']
                    if os.path.isfile(filePath):
                        if not mixer.get_init():
                            mixer.init(frequency = 48000)
                        mixer.music.set_volume(self._volume * 0.5)
                        mixer.music.load(filePath)
                        mixer.music.play(start = self._playList[0]['pos'])
                        logging.debug('play mp3 file: %s, start - %f.' %(filePath, self._playList[0]['pos']))
                        if self._playList[0]['pri'] == '0':
                            self.clearRadio()
                        while True:
                            self._playFiniEvent.wait(0.5)
                            if self._playFiniEvent.isSet():
                                self._playList[0]['pos'] = float(mixer.music.get_pos()) / 1000
                                raise Exception('fini')
                            else:
                                if not mixer.music.get_busy():      # 播放完毕，切换到下一首
                                    break
                            if self._volume != mixer.music.get_volume() * 2:
                                mixer.music.set_volume(self._volume * 0.5)
                    else:
                        del self._playList[0]
        except Exception, e:
            if e.message == 'fini':
                pass
            else:
                traceback.print_exc()
        finally:
            mixer.music.stop()
            if self._sound:
                mixer.quit()
                self._sound = None
            logging.debug('mp3FSM.playThread() fini.')
            self._playThread = None
            self._playDoneEvent.set()

    # 终止播放
    def playFini(self, quit = False):
        logging.debug('mp3FSM.playFini().')
        if self._playThread:
            self._playFiniEvent.set()
            self._playDoneEvent.wait()
            if quit and mixer.get_init():
                mixer.quit()

    # 开始播放
    def playInit(self, sound = None):
        logging.debug('mp3FSM.playInit().')
        if not self._playThread:
            self._playThread = threading.Thread(target = self.playThread)
            self._playThread.start()

    # 终止音频状态机线程
    def fini(self):
        logging.debug('mp3FSM.fini().')
        if self._fsmThread:
            self.putEvent('fini', None)
            self._fsmDoneEvent.wait()

    # 向音频状态机事件队列发送事件
    def putEvent(self, desc, event):
        if self._eventQueue:
            v = [desc, event]
            if v not in self._eventList and not self._eventQueue.full():
                logging.debug('mp3FSM.putEvent(%s).' %desc)
                self._eventList.append(v)
                self._eventQueue.put(v)
                return True
        return False

    # 从音频状态机事件队列提取事件
    def getEvent(self):
        if self._eventQueue:
            v = self._eventQueue.get(block = True)
            self._eventQueue.task_done()
            logging.debug('mp3FSM.getEvent(%s).' %v[0])
            if v in self._eventList:
                self._eventList.remove(v)
            return True, v[0], v[1]
        return False, None, None

    # 开始更新音频文件
    def updateInit(self, cbDone):
        logging.debug('mp3FSM.updateInit().')
        if not self._updateThread:
            self._updateThread = threading.Thread(target = self.updateThread, args = [cbDone, ])
            self._updateThread.start()

    # 终止更新音频文件
    def updateFini(self):
        logging.debug('mp3FSM.updateFini().')
        if self._updateThread:
            self._updateFiniEvent.set()
            self._updateDoneEvent.wait()

    # 播放音效
    def playSound(self, sound):
        logging.debug('mp3FSM.playSound(%s).' %sound)
        self.playFini()
        self.playInit(sound)

    # 关闭音效
    def stopSound(self):
        logging.debug('mp3FSM.stopSound().')
        self.playFini()

    # 播放按键回调函数
    def cbButtonPlay(self):
        logging.debug('mp3FSM.cbButtonPlay().')
        self.putEvent('evtButtonPlay', self.evtButtonPlay)

    # 音量增加键回调函数
    def cbButtonIncVolume(self):
        volume = self._volume + VOLUME_INV
        self._volume = volume if volume < VOLUME_MAX else VOLUME_MAX
        logging.debug('mp3FSM.cbButtonIncVolume(%f).' %self._volume)

    # 音量减少键回调函数
    def cbButtonDecVolume(self):
        volume = self._volume - VOLUME_INV
        self._volume = volume if volume > VOLUME_MIN else VOLUME_MIN
        logging.debug('mp3FSM.cbButtonDecVolume(%f).' %self._volume)

    # 广播模拟按键回调函数
    def cbButtonRadio(self):
        logging.debug('mp3FSM.cbButtonRadio().')
        self.updateInit(None)

    # 视频模拟按键动作
    def cbButtonImx(self):
        logging.debug('mp3FSM.cbButtonImx().')
        if self.state == 'stateImx':
            self.putEvent('evtImxOff', self.evtImxOff)
        else:
            self.putEvent('evtImxOn', self.evtImxOn)

    # 更新音频列表
    def actUpdate(self):
        logging.debug('mp3FSM.actUpdate().')
        self.updateInit(None)

    # 处理播放按键
    def actButtonPlay(self):
        logging.debug('mp3FSM.actButtonPlay().')
        if not self._playThread:                # 开始播放政策
            del self._playList[:]
            for i in self._fileList:
                if i['pri'] == '0':
                    self._playList.append({ 'fileId': i['fileId'], 'filePath': i['filePath'], 'pri': '0', 'pos': 0.0 })
        else:
            self.playFini()
            if self._playList[0]['pri'] == '1': # 正在播放广播
                while len(self._playList) > 0 and self._playList[0]['pri'] == '1':
                    del self._playList[0]
            else:                               # 正在播放政策
                del self._playList[:]
        self.clearRadio()
        if len(self._playList) > 0:
            self.playInit()

    # 处理广播播放
    def actRadio(self):
        logging.debug('mp3FSM.actRadio().')
        self.playFini()
        playList = []
        for i in self._fileList:
            if i['pri'] == '1':
                playList.append({ 'fileId': i['fileId'], 'filePath': i['filePath'], 'pri': '1', 'pos': 0.0 })
        for i in self._playList:
            if i['pri'] == '0':
                playList.append(i)
        self._playList = playList
        if len(self._playList) > 0:
            self.playInit()

    # 处理视频开始
    def actImxOn(self):
        logging.debug('mp3FSM.actImxOn().')
        self.playFini(quit = True)

    # 处理视频结束
    def actImxOff(self):
        logging.debug('mp3FSM.actImxOff().')
        if len(self._playList) > 0:
            self.playInit()


###############################################################################
# 测试程序
if __name__ == '__main__':
    try:
        hostName, portNumber, robotId = 'https://ttyoa.com', '8098', 'b827eb319c88'
        server = serverAPI(hostName = hostName, portNumber = portNumber, robotId = robotId)
        ret, token = server.login()
        if ret:
            mp3 = mp3FSM(hostName = hostName, portNumber = portNumber, token = token, getMp3List = server.getMp3List)
            button = buttonAPI()
            button.setMuteCallback(mp3.cbButtonPlay)
            button.setPlayCallback(mp3.cbButtonPlay)
            button.setIncVolumeCallback(mp3.cbButtonIncVolume)
            button.setDecVolumeCallback(mp3.cbButtonDecVolume)
            if platform.system().lower() == 'windows':
                button.setRadioCallback(mp3.cbButtonRadio)
                button.setImxCallback(mp3.cbButtonImx)
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        mp3.fini()
        sys.exit(0)
