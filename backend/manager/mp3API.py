#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import requests
from pygame import mixer
import string
import logging
import time
import platform
import traceback

if __name__ == '__main__':
    import sys
    import threading
    sys.path.append('..')

from manager import serverAPI as server
from utility import setLogging

__all__ = [
        'init',
        'update',
        'playPolicy',
        'stopPolicy',
        'haltPolicy',
        'playRadio',
        'stopRadio',
        'haveRadio',
        'clearRadio',
        'getVolume',
        'setVolume',
        ]

# mp3 文件保存路径
if platform.system().lower() == 'windows':
    MP3_DIR_ = os.getcwd()
elif platform.system().lower() == 'linux':
    MP3_DIR_ = '/ram'
else:
    raise NotImplementedError


MP3_LIST_URL_POSTFIX = '/medical/robot/listMp3'         # 音频列表地址后缀
MP3_FILE_URL_POSTFIX = '/medical/basic/file/download'   # 音频文件地址后缀


# 局部变量
_volume         = 0.5
_token          = ''
_hostName       = None
_portNumber     = 0

_mp3Dir         = MP3_DIR_

_mp3FileDict    = {}
_mp3PrioDict    = {}

_radioPlay      = False
_radioDict      = {}

_policyPlay     = False
_policyStop     = False
_policyDict     = {}
_policyFileId   = None
_policyStart    = 0.0


# 更新本地音频文件
def updateFileLocal():
    global _mp3Dir, _mp3FileDict, _mp3PrioDict

    ret = False
    logging.debug('mp3API.updateFileLocal().')
    try:
        _mp3FileDict.clear()
        _mp3PrioDict.clear()
        for fileName in os.listdir(_mp3Dir):
            postFix = string.split(fileName, '.')[-1].lower()
            if postFix == 'mp3':
                fileId  = string.split(fileName, '.')[0];
                _mp3FileDict[fileId] = os.path.join(_mp3Dir, fileName)
                _mp3PrioDict[fileId] = 0
        logging.debug('updateFileInit() success.')
        ret = True
    except:
        traceback.print_exc()
    finally:
        logging.debug('mp3API.updateFileLocal() %s.' %('success' if ret else 'failed'))
        return ret


# 更新音频文件
def updateFile(mp3List, cbRadio = None):
    global _mp3Dir, _mp3FileDict, _mp3PrioDict, _radioDict, _policyDict, _token

    newList = []
    updateFileLocal()
    logging.debug('mp3API.updateFile().')
    for mp3 in mp3List:
        try:
            postFix = ''
            if 'fileName' in mp3 and mp3['fileName']:
                postFix  = string.split(mp3['fileName'], '.')[-1].lower()
            if 'fileId' in mp3 and mp3['fileId'] and postFix == 'mp3':
                fileId   = mp3['fileId']
                priority = mp3['pri']
                mp3Url   = _hostName + ':' + _portNumber + MP3_FILE_URL_POSTFIX + '?fileId=' + fileId
                logging.debug('update mp3 file: url - %s' %mp3Url)
                if _mp3FileDict.has_key(fileId):
                    # 字典中已经存在该音频文件
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
                            logging.debug('download mp3 file: url - %s, token - %s' %(mp3Url, _token))
                            headers = { 'access_token': _token }
                            rsp = requests.get(mp3Url, headers = headers, stream = True, verify = False)
                            logging.debug('download mp3 file: rsp.status_code - %d', rsp.status_code)
                            if rsp.status_code == 200:
                                with open(mp3Path, 'wb') as mp3File:
                                    for chunk in rsp.iter_content(chunk_size = 1024):
                                        if chunk:
                                            mp3File.write(chunk)
                                logging.debug('download mp3 file done: url - %s' %mp3Url)
                                _mp3FileDict[fileId] = mp3Path
                                _mp3PrioDict[fileId] = priority;
                                newList.append(fileId)
                            else:
                                logging.debug('error when retriving mp3 file.')
                                return False
                        except:
                            logging.debug('error when retriving mp3 file.')
                            traceback.print_exc()
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
                logging.debug('remove mp3 file %s failed.' %mp3Path)
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

    # 如果有广播文件，则调用广播回调函数
    if len(_radioDict) > 0 and cbRadio:
        cbRadio()

    logging.debug('mp3API.updateFile() done.')
    return True


# 更新音频文件
def update():
    logging.debug('mp3API.update().')
    ret, mp3List = server.getMp3List()
    if ret:
        return updateFile(mp3List)
    return False


# 获取下一首文件编码
def nextFileId(fileDict, fileId):
    logging.debug('mp3API.nextFileId(%s).' %fileId)
    try:
        index = fileDict.keys().index(fileId) + 1
        if index < len(fileDict.keys()):
            return list(fileDict.keys())[index]
        return None
    except:
        traceback.print_exc()
        return None


# 播放广播文件
def playRadio():
    global _radioDict, _radioPlay, _volume
    logging.debug('mp3API.playRadio().')
    try:
        if len(_radioDict) > 0:
            fileId = None
            _radioPlay = True
            while _radioPlay and len(_radioDict) > 0:
                if not fileId:
                    fileId = list(_radioDict.keys())[0]
                mp3Path = _radioDict[fileId]
                if os.path.isfile(mp3Path):
                    # 开始播放广播
                    logging.debug('play radio: %s start.' %mp3Path)
                    if not mixer.get_init():
                        mixer.init()
                    mixer.music.set_volume(_volume)
                    mixer.music.load(mp3Path)
                    mixer.music.play()
                    while _radioPlay:
                        if not mixer.music.get_busy():
                            # 播放完毕，切换到下一首
                            logging.debug('play radio: %s finished.' %mp3Path)
                            fileId = nextFileId(_radioDict, fileId)
                            if not fileId:
                                _radioPlay = False
                            break
                        time.sleep(1)
                        if _volume != mixer.music.get_volume():
                            mixer.music.set_volume(_volume)
                    mixer.music.stop()
                    mixer.quit()
                else:
                    # 广播文件不存在，切换到下一首
                    fileId = nextFileId(_radioDict, fileId)
                    if not fileId:
                        _radioPlay = False
    except:
        traceback.print_exc()
    finally:
        logging.debug('mp3API.playRadio() stop.')


# 停止播放广播
def stopRadio():
    global _radioPlay
    logging.debug('mp3API.stopRadio().')
    _radioPlay = False


# 判定是否有广播文件
def haveRadio():
    logging.debug('mp3API.haveRadio().')
    return len(_radioDict) > 0


# 清除所有广播文件
def clearRadio():
    global _radioDict
    logging.debug('mp3API.clearRadio().')
    for fileId in list(_radioDict.keys()):
        mp3Path = _mp3FileDict[fileId]
        if os.path.isfile(mp3Path):
            try:
                os.remove(mp3Path)
                del _mp3FileDict[fileId]
                del _mp3PrioDict[fileId]
            except:
                traceback.print_exc()
            finally:
                pass
    _radioDict.clear()


# 播放政策文件
def playPolicy():
    global _policyFileId, _policyDict, _policyStart, _policyPlay
    logging.debug('mp3API.playPolicy().')
    try:
        if len(_policyDict) > 0:
            _policyPlay = True
            while _policyPlay and len(_policyDict) > 0:
                if _policyFileId in _policyDict.keys():
                    # 恢复上次播放
                    start = _policyStart
                else:
                    # 重新开始播放
                    start = 0.0
                    _policyFileId = list(_policyDict.keys())[0]

                mp3File = _policyDict[_policyFileId]
                if os.path.isfile(mp3File):
                    # 开始播放政策文件
                    logging.debug('play policy: %s %s.' %(mp3File, 'start' if start == 0.0 else 'resume'))
                    if not mixer.get_init():
                        mixer.init()
                    mixer.music.set_volume(_volume)
                    mixer.music.load(mp3File)
                    mixer.music.play(start = start)

                    _policyStart = start
                    start = time.time()
                    finished = False
                    while _policyPlay:
                        if not mixer.music.get_busy():
                            # 播放完毕，切换到下一首
                            logging.debug('play policy: %s finished.' %mp3File)
                            finished = True
                            _policyStart = 0.0
                            _policyFileId = nextFileId(_policyDict, _policyFileId)
                            if not _policyFileId:
                                _policyPlay = False     # 播放结束
                            break
                        time.sleep(1)
                        if _volume != mixer.music.get_volume():
                            mixer.music.set_volume(_volume)
                    mixer.music.stop()
                    mixer.quit()
                    if not finished:
                        _policyStart += time.time() - start
                else:
                    # 政策文件不存在，切换到下一首
                    _policyStart = 0.0
                    _policyFileId = nextFileId(_policyDict, _policyFileId)
                    if not _policyFileId:
                        _policyPlay = False
    except:
        traceback.print_exc()
    finally:
        if _policyStop:
            _policyFileId = None
            _policyStart  = 0.0
        logging.debug('mp3API.playPolicy() %s.' %('halt' if _policyFileId else 'stop'))


# 停止播放政策
def stopPolicy():
    global _policyPlay, _policyStop
    logging.debug('mp3API.stopPolicy().')
    _policyPlay = False
    _policyStop = True


# 暂停播放政策
def haltPolicy():
    global _policyPlay, _policyStop
    logging.debug('mp3API.haltPolicy().')
    _policyPlay = False
    _policyStop = False


# 获取播放音量
def getVolume():
    global _volume
    logging.debug('mp3API.getVolume().')
    return _volume


# 设置播放音量
def setVolume(volume = 0.5):
    global _volume
    logging.debug('mp3API.setVolume(%f).' %volume)
    _volume = volume


# 初始化音频接口
def init(hostName, portNumber, token, volume = 0.5, mp3Dir = MP3_DIR_):
    global _hostName, _portNumber, _token, _mp3Dir, _volume
    logging.debug('mp3API.init().')
    _hostName = hostName
    _portNumber = portNumber
    _token = token
    _mp3Dir = mp3Dir
    _volume = volume
    if platform.system().lower() == 'linux':
        # 挂载虚拟盘
        os.system('sudo mount -t tmpfs -o size=50m,mode=0777 tmpfs /ram')


################################################################################
# 测试程序
if __name__ == '__main__':
    try:
        hostName    = 'https://ttyoa.com'
        portNumber  = '8098'
        robotId     = 'b827eb319c88'
        server.init(hostName, portNumber, robotId)
        ret, token = server.login()
        if ret:
            init(hostName, portNumber, token)
            if update():
                thr = threading.Thread(target = playPolicy)
                thr.start()
                time.sleep(10)
                haltPolicy()
                time.sleep(5)
                logging.debug('thread is %s.'  %('alive' if thr.isAlive() else 'not alive'))
                time.sleep(10)
                thr = threading.Thread(target = playPolicy)
                thr.start()
                while True:
                    time.sleep(1)
                    logging.debug('thread is %s.'  %('alive' if thr.isAlive() else 'not alive'))
    except KeyboardInterrupt:
        pass
    finally:
        stopRadio()
        stopPolicy()
