#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import json
import requests
from pygame import mixer
import threading
import logging
import time
import sys
import platform
import traceback


__all__ = [
        'mp3Init'
        'mp3ListInit',
        'mp3ListUpdateStart',
        'mp3ListUpdateStop'
        'mp3TestStart'
        'mp3TestStop'
        ]


logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(levelname)s- %(message)s')


# mp3 文件保存路径
if platform.system().lower() == 'windows':
    MP3_DIR_ = os.getcwd()
elif platform.system().lower() == 'linux':
    MP3_DIR_ = '/home/pi/robot/mp3List'
else:
    raise NotImplementedError


MP3_LIST_URL_POSTFIX = '/medical/robot/listMp3'         # 音频列表地址后缀
MP3_FILE_URL_POSTFIX = '/medical/basic/file/download'   # 音频文件地址后缀


# 局部变量
_pause          = False
_mp3Dir         = MP3_DIR_
_volume         = 0.5

_hostName       = None
_portNumber     = None

_mp3FileDict    = {}
_mp3PrioDict    = {}

_radioDict      = {}
_policyDict     = {}

_radioPlay      = False     # 广播播放标识
_radioStart     = 0.0       # 广播播放起始位置，用于恢复播放
_radioFileId    = None      # 广播播放文件标识

_policyPlay     = False     # 政策播放标识
_policyStart    = 0.0       # 政策播放起始位置，用于恢复播放
_policyFileId   = None      # 政策播放文件标识

_playStop       = False
_updateStop     = False

_updateThread   = None
_updateEvent    = None

_testThread     = None
_testStop       = False


# 初始化本地文件播放列表
#
#   遍历本地所有的音频文件
def mp3ListInitLocal():
    global _mp3Dir, _mp3FileDict, _mp3PrioDict
    try:
        for fileName in os.listdir(_mp3Dir):
            postFix = str.split(fileName, '.')[-1].lower()
            if postFix == 'mp3':
                fileId  = str.split(fileName, '.')[0];
                _mp3FileDict[fileId] = os.path.join(_mp3Dir, fileName)
                _mp3PrioDict[fileId] = 0
        logging.debug('mp3InitLocalList() success.')
        return True
    except:
        logging.debug('mp3InitLocalList() failed.')
        return False


# 创建更新音频列表后台线程
def mp3ListInitUpdate():
    global _updateEvent, _updateThread
    logging.debug('mp3ListInitUpdate() start...')
    if not _updateEvent:
        logging.debug('create _updateEvent.')
        _updateEvent = threading.Event()
        _updateEvent.clear()
    if not _updateThread:
        logging.debug('create _updateThread.')
        _updateThread = threading.Thread(target = mp3ListUpdateThread)
        _updateThread.start()


# 创建播放音频列表后台线程
def mp3ListInitPlay():
    global _playEvent, _playThread
    if not _playEvent:
        logging.debug('create _playEvent.')
        _playEvent = threading.Event()
        _playEvent.clear()
    if not _playThread:
        logging.debug('create _playThread.')
        _playThread = threading.Thread(target = mp3ListPlayThread)
        _playThread.start()


# 音频管理模块初始化
def mp3ListInit(mp3Dir = MP3_DIR_, volume = 0.5):
    global _pause, _mp3Dir, _volume, _mp3FileDict, _mp3PrioDict, _radioDict, _policyDict

    _pause          = False              # 播放暂停标识
    _mp3Dir         = mp3Dir             # 文件保存目录
    _volume         = volume             # 音量管理

    _mp3FileDict    = {}                 # mp3 文件管理字典
    _mp3PrioDict    = {}                 # mp3 文件优先级管理字典

    _radioDict      = {}                 # 广播文件管理字典
    _policyDict     = {}                 # 政策文件管理字典

    _radioPlay      = False              # 广播播放标识
    _radioStart     = 0.0                # 广播播放起始位置，用于恢复播放
    _radioFileId    = None               # 广播播放文件标识

    _policyPlay     = False              # 政策播放标识
    _policyStart    = 0.0                # 政策播放起始位置，用于恢复播放
    _policyFileId   = None               # 政策播放文件标识

    _playThread     = None               # mp3 播放线程
    _playStop       = False

    mp3ListInitLocal()                  # 初始化本地音频文件
    mp3ListInitUpdate()                 # 创建更新音频列表后台线程
    mp3ListInitPlay()                   # 创建播放音频列表后台线程


# 启动更新音频列表
def mp3ListUpdateStart(mp3FileUrl, mp3List, token):
    global _updateEvent, _mp3FileUrl, _mp3List, _token
    logging.debug('mp3ListUpdateStart() start ...')
    _mp3FileUrl = mp3FileUrl
    _mp3List    = mp3List
    _token      = token
    _updateEvent.set()      # 启动后台更新音频文件


# 结束音频文件后台程序
def mp3ListUpdateStop():
    global _updateStop, _updateEvent
    _updateStop = True
    _updateEvent.set()


# 执行更新音频列表
def mp3ListUpdateExec():
    global _mp3List, _mp3FileUrl, _mp3FileDict, _mp3PrioDict, _radioDict, _policyDict
    logging.debug('mp3ListUpdateExec() start ...')
    newList = []
    for mp3 in _mp3List:
        try:
            postFix = ''
            if 'fileName' in mp3 and mp3['fileName']:
                postFix = str.split(mp3['fileName'], '.')[-1].lower()
            if 'fileId' in mp3 and mp3['fileId'] and postFix == 'mp3':
                fileId   = mp3['fileId']
                priority = mp3['pri']
                mp3Url   = _mp3FileUrl + '?fileId=' + fileId
                logging.debug('mp3 file url: %s' %mp3Url)

                exists = False
                if sys.version_info.major == 2:
                    # for python 2
                    exists = _mp3FileDict.has_key(fileId)
                elif sys.version_info.major == 3:
                    # for python 3
                    exists = _mp3FileDict.__contains__(fileId)
                if exists:
                    # 字典中已经存在该音频文件
                    logging.debug('update mp3 file: %s is exists.' %_mp3FileDict[fileId])
                    _mp3PrioDict[fileId] = priority
                    newList.append(fileId)
                else:
                    # 字典中没有该音频文件，重新下载
                    if not os.path.exists(_mp3Dir):
                        logging.debug('make mp3 dir.')
                        os.mkdirs(_mp3Dir)
                    mp3Name = fileId + '.mp3'
                    mp3Path = os.path.join(_mp3Dir, mp3Name)
                    logging.debug('mp3 path: %s' %mp3Path)
                    if not os.path.isfile(mp3Path):
                        try:
                            logging.debug('download mp3 file from %s start...' %mp3Url)
                            headers = { 'access_token': _token }
                            rsp = requests.get(mp3Url, headers = headers, stream = True)
                            logging.debug('download mp3 file: rsp.status_code - %d', rsp.status_code)
                            if rsp.status_code == 200:
                                with open(mp3Path, 'wb') as mp3File:
                                    for chunk in rsp.iter_content(chunk_size = 1024):
                                        if chunk:
                                            mp3File.write(chunk)
                                logging.debug('download mp3 file from %s done.' %mp3Url)
                                _mp3FileDict[fileId] = mp3Path
                                _mp3PrioDict[fileId] = priority;
                                newList.append(fileId)
                            else:
                                logging.debug('error when retriving mp3 file.')
                        except:
                            logging.debug('error when retriving mp3 file.')
                            return False
                    else:
                        logging.debug('%s is exists.' %mp3Name)
                        _mp3FileDict[fileId] = mp3Path
                        _mp3PrioDict[fileId] = priority;
                        newList.append(fileId)
        except:
            logging.debug('download mp3 file failed: %s' %mp3)
            traceback.print_exc()
            return False

    # 删除原有 mp3 列表中不再需要的文件
    oldList = list(_mp3FileDict.keys())
    for fileId in list(set(oldList) - set(newList)):
        mp3Path = _mp3FileDict[fileId]
        if os.path.isfile(mp3Path):
            try:
                logging.debug('remove mp3 file %s.' %mp3Path)
                os.remove(mp3Path)
                del _mp3FileDict[fileId]
                del _mp3PrioDict[fileId]
            except:
                logging.warning('remove mp3 file %s failed.' %mp3Path)
                traceback.print_exc()
                return False


    # 将下载好的音频文件分类管理
    _radioDict.clear()
    _policyDict.clear()
    for fileId in _mp3PrioDict.keys():
        mp3Path = _mp3FileDict[fileId]
        if os.path.isfile(mp3Path):
            if _mp3PrioDict[fileId] == '0':
                _policyDict[fileId] = mp3Path
            else:
                _radioDict[fileId]  = mp3Path

    if len(_radioDict) > 0:
        # 立即播放广播文件
        # mp3ListPlayRadio()
        pass

    logging.warning('mp3ListUpdateExec() done.')
    return True


# 后台更新音频文件程序
def mp3ListUpdateThread():
    global _updateStop, _updateEvent, _updateThread

    logging.debug('mp3ListUpdateThread() start...')

    _updateStop = False
    _updateEvent.clear()
    while not _updateStop:
        _updateEvent.wait()
        if _updateEvent.isSet and not _updateStop:
            if mp3ListUpdateExec():
                # 更新音频文件成功
                logging.debug('mp3ListUpdateThread() done.')
                _updateEvent.clear()
            else:
                # 更新音频文件失败，30 秒后重新下载
                logging.debug('mp3ListUpdateThread() failed.')
                for wait in range(0, 60):
                    time.sleep(0.5)
                    if _updateStop:
                        break

    _updateStop   = False
    _updateThread = None
    _updateEvent.clear()
    logging.debug('mp3ListUpdateThread() stop...')


# 后台播放音频文件程序
def mp3ListPlayThread():
    global _playStop, _playEvent, _playThread

    logging.debug('mp3ListPlayThread() start...')
    _playStop = False
    _playEvent.clear()
    while not _playStop:
        if _playPause:
            # 暂停状态
            logging.debug('play paused.')
            while _playPause and not _playStop:
                time.sleep(1)

        elif _playRadio and len(_radioDict) > 0:
            # 广播播放状态
            logging.debug('play radio.')
            if _radioFileId in list(_radioDict.keys()):
                # 恢复上次播放
                logging.debug('play radio resume.')
                start = _radioStart
            else:
                # 首次播放
                logging.debug('play radio begin.')
                start = 0.0
                _radioFileId = list(_radioDict.keys())[0]

            mp3Path = _radioDict[_radioFileId]
            if os.path.isfile(mp3Path):
                # 开始播放广播文件
                mixer.music.set_volume(_volume)
                mixer.music.load(mp3Path)
                mixer.music.play(start = start)
                _radioStart = start

                start = time.time()
                while not _playStop:
                    if not mixer.music.get_busy():
                        # 播放完毕，切换到下一首
                        logging.debug('play radio finish.')
                        mixer.music.stop()
                        _radioStart  = 0.0
                        _radioFileId = nextRadioFileId(_radioFileId)
                        if not _radioFileId:
                            _radioPlay  = False
                        break
                    elif _playPause:
                        # 暂停播放
                        logging.debug('play radio paused.')
                        mixer.music.stop()
                        _radioStart += time.time() - start
                    elif not _radioPlay:
                        # 退出播放
                        mixer.music.stop()
                        _radioFileId = None
                        _radioStart  = 0.0
                        break;
                    else:
                        time.sleep(1)
            else:
                # 广播文件不存在，切换到下一首
                _radioStart  = 0.0
                _radioFileId = nextRadioFileId(_radioFileId)
                if not _radioFileId:
                    _radioPlay = False


# mp3 测试线程
def mp3TestThread(mp3File):
    global _testThread, _testStop
    if not _testStop:
        mixer.init()
        mixer.music.set_volume(1)
        mixer.music.load(mp3File)
        mixer.music.play(start = 0.0)
        while not _testStop and mixer.music.get_busy():
            time.sleep(0.5)
        mixer.music.stop()
    _testThread = None


# 启动 mp3 测试
def mp3TestStart(mp3File):
    global _testThread, _testStop
    if not _testThread:
        _testStop   = False
        _testThread = threading.Thread(target = mp3TestThread, args = [mp3File, ])
        _testThread.start()


# 停止 mp3 测试
def mp3TestStop():
    global _testThread, _testStop
    if _testThread:
        _testStop = True
        while _testThread:
            time.sleep(0.5)


# mp3 管理模块
#   政策播放文件
#   广播播放文件
class _mp3Manager(object):
    #
    # mp3Dir     - 播放文件保存目录
    # volume     - 播放音量
    #
    def __init__(self, mp3Dir = MP3_DIR_, volume = 0.5):
        global gMp3Manager
        gMp3Manager = self

        self._pause         = False             # 播放暂停标识
        self._mp3Dir        = mp3Dir            # 文件保存目录
        self._volume        = volume            # 音量管理

        self._token         = None
        self._mp3ListUrl    = ''
        self._mp3FileUrl    = ''

        self._mp3FileDict   = {}                # mp3 文件管理字典
        self._mp3PrioDict   = {}                # mp3 文件优先级管理字典

        self._radioDict     = {}                # 广播文件管理字典
        self._policyDict    = {}                # 政策文件管理字典

        self._radioPlay     = False             # 广播播放标识
        self._radioStart    = 0.0               # 广播播放起始位置，用于恢复播放
        self._radioFileId   = None              # 广播播放文件标识

        self._policyPlay    = False             # 政策播放标识
        self._policyStart   = 0.0               # 政策播放起始位置，用于恢复播放
        self._policyFileId  = None              # 政策播放文件标识

        self._playThread    = None              # mp3 播放线程

        self._stopEvent     = threading.Event() # 停止事件
        self._stopEvent.clear()

        self._updateEvent   = threading.Event() # 列表更新事件
        self._updateEvent.clear()
        self._updateDone    = False             # 更新完成标志
        self._updateThread  = None

        self.initMp3List()


    # 初始化现有的 mp3 列表
    def initMp3List(self):
        try:
            for fileName in os.listdir(self._mp3Dir):
                postFix = str.split(fileName, '.')[-1].lower()
                if postFix == 'mp3':
                    fileId  = str.split(fileName, '.')[0];
                    self._mp3FileDict[fileId] = os.path.join(self._mp3Dir, fileName)
                    self._mp3PrioDict[fileId] = 0
        except:
            logging.debug('mp3Manager.initMp3List() failed.')


    # 更新语音播放列表
    def updateMp3List(self):
        ret = True
        logging.debug('mp3Manager.updateMp3List() start ...')
        try:
            newList = []
            headers = { 'access_token': self._token }
            rsp = requests.get(self._mp3ListUrl, headers = headers)
            if rsp.status_code == 200:
                js = rsp.json()
                logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
                if 'data' in js:
                    mp3List = js['data']
                    for mp3 in mp3List:
                        try:
                            postFix  = '';
                            if 'fileName' in mp3 and mp3['fileName']:
                                postFix = str.split(mp3['fileName'], '.')[-1].lower()

                            if 'fileId' in mp3 and mp3['fileId'] and postFix == 'mp3':
                                fileId   = mp3['fileId']
                                priority = mp3['pri']
                                mp3Url   = self._mp3FileUrl + '?fileId=' + fileId
                                logging.debug('mp3 file url: %s' %mp3Url)
                                exists = False
                                if sys.version_info.major == 2:
                                    # for python 2
                                    exists = self._mp3FileDict.has_key(fileId)
                                elif sys.version_info.major == 3:
                                    # for python 3
                                    exists = self._mp3FileDict.__contains__(fileId)

                                if exists:
                                    # 字典中已经存在该 mp3 文件
                                    logging.debug('update mp3 file: %s is exists.' %self._mp3FileDict[fileId])
                                    self._mp3PrioDict[fileId] = priority
                                    newList.append(fileId)
                                else:
                                    # 字典中没有该 mp3 文件
                                    if not os.path.exists(self._mp3Dir):
                                        logging.debug('make mp3 dir.')
                                        os.mkdirs(self._mp3Dir)

                                    mp3Name = fileId + '.mp3'
                                    mp3Path = os.path.join(self._mp3Dir, mp3Name)
                                    logging.debug('mp3 path: %s' %mp3Path)
                                    if not os.path.isfile(mp3Path):
                                        try:
                                            logging.debug('download mp3 file from %s start...' %mp3Url)
                                            rsp = requests.get(mp3Url, stream = True)
                                            if rsp.status_code == 200:
                                                with open(mp3Path, 'wb') as mp3_file:
                                                    for chunk in rsp.iter_content(chunk_size = 1024):
                                                        if chunk:
                                                            mp3_file.write(chunk)
                                                logging.debug('download mp3 file from %s done.' %mp3Url)
                                                self._mp3FileDict[fileId] = mp3Path
                                                self._mp3PrioDict[fileId] = priority;
                                                newList.append(fileId)
                                            else:
                                                logging.warning('error when retriving mp3 file.')
                                        except:
                                            logging.warning('error when retriving mp3 file.')
                                            return False
                                    else:
                                        logging.debug('%s is exists.' %mp3Name)
                                        self._mp3FileDict[fileId] = mp3Path
                                        self._mp3PrioDict[fileId] = priority;
                                        newList.append(fileId)
                        except:
                            logging.warning('download mp3 file failed: %s' %mp3)
                            return False

                    # 删除原有 mp3 列表中不再需要的文件
                    oldList = list(self._mp3FileDict.keys())
                    for fileId in list(set(oldList) - set(newList)):
                        mp3Path = self._mp3FileDict[fileId]
                        if os.path.isfile(mp3Path):
                            try:
                                logging.debug('remove mp3 file %s.' %mp3Path)
                                os.remove(mp3Path)
                                del self._mp3FileDict[fileId]
                                del self._mp3PrioDict[fileId]
                            except:
                                logging.warning('remove mp3 file %s failed.' %mp3Path)
                                return False
                        else:
                            del self._mp3FileDict[fileId]
                            del self._mp3PrioDict[fileId]
            else:
                logging.warning('get mp3 list from %s failed.' %self._mp3ListUrl)
        except:
            logging.warning('get mp3 list from %s failed.' %self._mp3ListUrl)
            return False

        # 将下载的 mp3 文件分类别管理
        self._radioDict.clear()
        self._policyDict.clear()
        for fileId in self._mp3PrioDict.keys():
            mp3Path = self._mp3FileDict[fileId]
            if os.path.isfile(mp3Path):
                if self._mp3PrioDict[fileId] == 0:
                    self._policyDict[fileId] = mp3Path
                else:
                    self._radioDict[fileId]  = mp3Path

        if len(self._radioDict) > 0:
            self._radioPlay = True      # 立即播放广播文件

        self._updateDone = True
        logging.warning('mp3Manager.updateMp3List() done.')

        return True


    # 判断是否处于播放状态
    def isPlaying(self):
        if not self._pause:
            if self._policyPlay or self._radioPlay:
                return True
        return False


    # 增加音量
    def incVolume(self):
        if not self._pause:
            if self._policyPlay or self._radioPlay:
                if self._volume < 1:
                    logging.debug('current volume: %f' %self._volume)
                    self._volume += 0.1
                    mixer.music.set_volume(self._volume)


    # 减少音量
    def decVolume(self):
        if not self._pause:
            if self._policyPlay or self._radioPlay:
                if self._volume > 0:
                    logging.debug('current volume: %f' %self._volume)
                    self._volume -= 0.1
                    mixer.music.set_volume(self._volume)


    # 下载更新管理线程
    def updateThread(self):
        logging.debug('mp3Manager.updateThread() start...')
        while not self._stopEvent.isSet():
            self._updateEvent.wait(2)
            if self._updateEvent.isSet():
                if self.updateMp3List():
                    logging.debug('mp3Manager.updateThread() done.')
                    self._updateEvent.clear()
                else:
                    # 下载更新失败，30 秒后重新下载
                    logging.debug('mp3Manager.updateThread() failed.')
                    time.sleep(30)

        self._updateThread = None
        logging.debug('mp3Manager.updateThread() stop...')


    # 获取下一首广播文件标识
    def nextRadioFileId(self, fileId):
        try:
            index = self._radioDict.keys().index(fileId) + 1
            if index < len(self._radioDict.keys()):
                return list(self._radioDict.keys())[index]
            return None
        except:
            return None


    # 获取下一首政策文件标识
    def nextPolicyFileId(self, fileId):
        try:
            index = self._policyDict.keys().index(fileId) + 1
            if index < len(self._policyDict.keys()):
                return list(self._policyDict.keys())[index]
            return None
        except:
            return None


    # 播放线程
    def playThread(self):
        logging.debug('play thread start...')
        mixer.init()
        mixer.music.set_volume(self._volume)
        while not self._stopEvent.isSet():
            logging.debug('_pause = %d, _radioPlay = %d, _policyPlay = %d' %(self._pause, self._radioPlay, self._policyPlay))
            if self._pause:
                # 暂停状态
                logging.debug('play paused.')
                while self._pause and not self._stopEvent.isSet():
                    time.sleep(1)

            elif self._radioPlay:
                # 广播播放状态
                logging.debug('play radio.')
                if self._radioFileId in self._radioDict.keys():
                    # 恢复上次播放
                    logging.debug('play radio resume.')
                    start = self._radioStart
                else:
                    # 首次播放
                    logging.debug('play radio begin.')
                    start = 0.0
                    self._radioFileId = list(self._radioDict.keys())[0]

                mp3Path = self._radioDict[self._radioFileId]
                if os.path.isfile(mp3Path):
                    # 开始播放广播文件
                    mixer.music.set_volume(self._volume)
                    mixer.music.load(mp3Path)
                    mixer.music.play(start = start)
                    self._radioStart = start

                    start = time.time()
                    while not self._stopEvent.isSet():
                        if not mixer.music.get_busy():
                            # 播放完毕，切换到下一首
                            logging.debug('play radio finish.')
                            mixer.music.stop()
                            self._radioStart  = 0.0
                            self._radioFileId = self.nextRadioFileId(self._radioFileId)
                            if not self._radioFileId:
                                self._radioPlay = False
                            break
                        elif self._pause:
                            # 暂停播放
                            logging.debug('play radio paused.')
                            mixer.music.stop()
                            self._radioStart += time.time() - start
                            break
                        elif not self._radioPlay:
                            # 退出播放
                            logging.debug('play radio stop.')
                            mixer.music.stop()
                            self._radioFileId = None
                            self._radioStart  = 0.0
                            break;
                        else:
                            time.sleep(1)
                else:
                    # 广播文件不存在，切换到下一首
                    self._radioFileId = self.nextRadioFileId(self._radioFileId)
                    self._radioStart  = 0.0
                    if not self._radioFileId:
                        self._radioPlay = False

            elif self._policyPlay and len(self._policyDict) > 0:
                # 政策播放状态
                logging.debug('play policy.')
                if self._policyFileId in self._policyDict.keys():
                    # 恢复上次播放
                    logging.debug('play policy resume.')
                    start = self._policyStart
                else:
                    # 首次播放
                    logging.debug('play policy begin.')
                    start = 0.0
                    self._policyFileId = list(self._policyDict.keys())[0]

                mp3_file = self._policyDict[self._policyFileId]
                if os.path.isfile(mp3_file):
                    # 开始播放政策文件
                    mixer.music.set_volume(self._volume)
                    mixer.music.load(mp3_file)
                    mixer.music.play(start = start)
                    self._policyStart = start

                    start = time.time()
                    while not self._stopEvent.isSet():
                        if not mixer.music.get_busy():
                            # 播放完毕，切换到下一首
                            logging.debug('play policy finish.')
                            mixer.music.stop()
                            self._policyStart  = 0.0
                            self._policyFileId = nextPolicyFileId(self._policyFileId)
                            if not self._policyFileId:
                                self._policyPlay = False
                            break
                        elif self._pause:
                            # 暂停播放
                            logging.debug('play policy paused.')
                            mixer.music.stop()
                            self._policyStart += time.time() - start
                            break;
                        elif not self._policyPlay:
                            # 退出播放
                            logging.debug('play policy stop.')
                            mixer.music.stop()
                            self._policyFileId = None
                            self._policyStart  = 0.0
                            break;
                        else:
                            time.sleep(1)
                else:
                    # 政策文件不存在，切换到下一首
                    self._policyStart  = 0.0
                    self._policyFileId = nextPolicyFileId(self._policyFileId)
                    if not self._policyFileId:
                        self._policyPlay = False

            else:
                time.sleep(1)

        if mixer.music.get_busy():
            mixer.music.stop()
        self._playThread = None
        logging.debug('play thread stop')


    # 暂停播放
    def playPause(self):
        self._pause = True


    # 继续播放
    def playResume(self):
        self._pause = False

    # 停止播放
    def playStop(self):
        if not self._pause:
            if self._radioPlay:
                self._radioPlay = False
            elif self._policyPlay:
                self._policyPlay = False

    # 启动播放
    def playStart(self):
        if not self._pause and not self._radioPlay:
            self._policyPlay = True


    # 更新 mp3 播放列表
    def update(self, hostName, portNumber, token):
        logging.debug('mp3Manager.update().')
        self._updateDone    = False
        self._token         = token
        self._mp3ListUrl    = hostName + ':' + portNumber + MP3_LIST_URL_POSTFIX
        self._mp3FileUrl    = hostName + ':' + portNumber + MP3_FILE_URL_POSTFIX
        self._updateEvent.set()


    # 启动 mp3 播放器
    def start(self):
        logging.debug('mp3Manager.start().')
        self._stopEvent.clear()
        if not self._updateThread:
            self._updateThread = threading.Thread(target = self.updateThread)
            self._updateThread.start()

        if not self._playThread:
            self._playThread = threading.Thread(target = self.playThread)
            self._playThread.start()


    # 关闭 mp3 播放器
    def stop(self):
        logging.debug('mp3Manager.stop().')
        self._stopEvent.set()

        if self._updateThread:
            self._updateThread.join()
            self._updateThread = None

        if self._playThread:
            self._playThread.join()
            self._playThread = None


def main(list_url, file_url):
    hostName = 'http://ttyoa.com'
    portNumber = '8097'
    token = '3d491911000021ac_2'
    mm = _mp3Manager()
    mm.start()
    try:
        while True:
            mm.playStart()
            time.sleep(20)
            mm.playPause()
            time.sleep(20)
            mm.playResume()
            time.sleep(20)
            mm.playStop()
            time.sleep(20)
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
    mm.stop()
    sys.exit(0)


if __name__ == '__main__':
    hostName = 'http://ttyoa.com'
    portNumber = '8097'
    token = '6aa652ab00000dac_2'
    try:
        mm = _mp3Manager()
        mm.start()
        while True:
            time.sleep(2)
            mm.update(hostName, portNumber, token)
            time.sleep(30)
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
    mm.stop()
    sys.exit(0)

