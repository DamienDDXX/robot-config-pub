#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import time
import Queue
import logging
import platform
import threading
from transitions import Machine, State

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from utility import setLogging

from manager.mp3FSM import mp3FSM
from manager.serverAPI import serverAPI
from manager.buttonAPI import buttonAPI
if platform.system().lower() == 'linux':
    from manager.imxFSM import imxFSM
    from manager.bandFSM import bandFSM

__all__ = [
        'serverFSM',
        ]

base_dir = os.path.dirname(os.path.abspath(__file__))
if platform.system().lower() == 'windows':
    HEARTBEAT_INV = 2 * 60
    CALL_SOUND_FILEPATH = os.path.join(base_dir, '..\static\mp3\\dudu.mp3')
elif platform.system().lower() == 'linux':
    HEARTBEAT_INV = 10 * 60
    CALL_SOUND_FILEPATH = os.path.join(base_dir, '../static/mp3/dudu.mp3')
else:
    raise NotImplementedError

# 系统服务器状态机类定义
class serverFSM(object):
    # 初始化
    def __init__(self, hostName, portNumber, robotId, heartbeatInv = HEARTBEAT_INV):
        self._hostName = hostName
        self._portNumber = portNumber
        self._robotId = robotId
        self._heartbeatInv = heartbeatInv
        self._serverAPI = serverAPI(hostName = hostName, portNumber = portNumber, robotId = robotId)

        self._confVer = None
        self._playVer = None
        self._confUpdated = False
        self._playUpdated = False

        self._loginThread = None
        self._configThread = None
        self._heartbeatThread = None

        self._mp3FSM = None
        self._imxFSM = None
        self._bandFSM = None
        self._buttonAPI = buttonAPI()

        self._states = [
            State(name = 'stateLogin',      on_enter = 'actLogin',      ignore_invalid_triggers = True),
            State(name = 'stateConfig',     on_enter = 'actConfig',     ignore_invalid_triggers = True),
            State(name = 'stateHeartbeat',  on_enter = 'actHeartbeat',  ignore_invalid_triggers = True),
        ]
        self._transitions = [
            # 初始状态 ------->
            {
                'trigger':  'evtLoginOk',
                'source':   'stateLogin',
                'dest':     'stateConfig'
            },
            # 配置状态 ------->
            {
                'trigger':  'evtConfigOk',
                'source':   'stateConfig',
                'dest':     'stateHeartbeat'
            },
            {
                'trigger':  'evtFailed',
                'source':   'stateConfig',
                'dest':     'stateLogin'
            },
            # 心跳状态 ------->
            {
                'trigger':  'evtConfig',
                'source':   'stateHeartbeat',
                'dest':     'stateConfig'
            },
            {
                'trigger':  'evtHeartbeat',
                'source':   'stateHeartbeat',
                'dest':     'stateHeartbeat'
            },
            {
                'trigger':  'evtFailed',
                'source':   'stateHeartbeat',
                'dest':     'stateLogin'
            }
        ]

        # 启动状态机线程
        self._eventList = []
        self._eventQueue = Queue.Queue(5)
        self._machine = Machine(self, states = self._states, transitions = self._transitions, ignore_invalid_triggers = True)
        self._finiEvent = threading.Event()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    # 登录服务器
    def actLogin(self):
        logging.debug('serverFSM.actLogin().')
        if not self._loginThread:
            self._loginThread = threading.Thread(target = self.loginThread)
            self._loginThread.start()

    # 获取配置
    def actConfig(self):
        logging.debug('serverFSM.actConfig().')
        if not self._configThread:
            self._configThread = threading.Thread(target = self.configThread)
            self._configThread.start()

    # 心跳同步
    def actHeartbeat(self):
        logging.debug('serverFSM.actHeartbeat().')
        if not self._heartbeatThread:
            self._heartbeatThread = threading.Thread(target = self.heartbeatThread)
            self._heartbeatThread.start()

    # 向系统服务器状态机事件队列中放事件
    def putEvent(self, desc, event):
        if self._eventQueue:
            v = [desc, event]
            if v not in self._eventList and not self._eventQueue.full():
                logging.debug('serverFSM.putEvent(%s).' %desc)
                self._eventList.append(v)
                self._eventQueue.put(v)
                return True
        return False

    # 从系统服务器状态机事件队列中取事件
    def getEvent(self):
        if self._eventQueue:
            v = self._eventQueue.get(block = True)
            self._eventQueue.task_done()
            logging.debug('serverFSM.getEvent(%s).' %v[0])
            if v in self._eventList:
                self._eventList.remove(v)
            return True, v[0], v[1]
        return False, None, None

    # 设置音频更新完成
    def playUpdated(self):
        logging.debug('serverFSM.playUpdated().')
        self._playUpdated = True

    # 设置配置更新完成
    def confUpdated(self):
        logging.debug('serverFSM.confUpdated().')
        self._confUpdated = True

    # 后台登录线程
    #   如果登录失败，每隔 30s 重新登录
    def loginThread(self):
        logging.debug('serverFSM.loginThread().')
        try:
            while True:
                ret, self._token = self._serverAPI.login()
                if ret:
                    raise Exception('login')
                logging.debug('login failed')
                logging.debug('retry to login in 30s.')
                self._finiEvent.wait(30)
                if self._finiEvent.isSet():
                    raise Exception('fini')
        except Exception, e:
            if e.message == 'login':
                # 登录成功
                if not self._mp3FSM:
                    # 创建音频管理状态机
                    self._mp3FSM = mp3FSM(hostName = self._hostName, portNumber = self._portNumber, token = self._token, getMp3List = self._serverAPI.getMp3List)
                    self._buttonAPI.setPlayCallback(self._mp3FSM.cbButtonPlay)
                    self._buttonAPI.setIncVolumeCallback(self._mp3FSM.cbButtonIncVolume)
                    self._buttonAPI.setDecVolumeCallback(self._mp3FSM.cbButtonDecVolume)
                    if platform.system().lower() == 'windows':
                        self._buttonAPI.setRadioCallback(self._mp3FSM.cbButtonRadio)
                        self._buttonAPI.setImxCallback(self._mp3FSM.cbButtonImx)
                self.putEvent('evtLoginOk', self.evtLoginOk)
        finally:
            self._loginThread = None
            logging.debug('serverFSM.loginThread() fini.')

    # 进入视频通话模式回调函数
    def cbEntryImxMode(self):
        logging.debug('serverFSM.cbEntryImxMode().')
        self._mp3FSM.actImxOn()
        self._mp3FSM.putEvent('evtImxOn', self._mp3FSM.evtImxOn)

    # 退出视频通话模式回调函数
    def cbExitImxMode(self):
        logging.debug('serverFSM.cbExitImxMode().')
        self._mp3FSM.actImxOff()
        self._mp3FSM.putEvent('evtImxOff', self._mp3FSM.evtImxOff)

    # 呼叫音效开关回调函数
    def cbCallSound(self, onOff):
        logging.debug('serverFSM.cbCallSound().')
        if onOff:
            self._mp3FSM.playSound(CALL_SOUND_FILEPATH)
        else:
            self._mp3FSM.stopSound()

    # 后台获取配置
    #   如果失败，间隔 30s 后重新获取
    #   尝试 6 次后重新登录
    def configThread(self):
        logging.debug('serverFSM.configThread().')
        try:
            for retry in range(0, 6):
                ret, vsvrIp, vsvrPort, personList = self._serverAPI.getConfig()
                if ret:
                    raise Exception('config')
                logging.debug('get config failed.')
                logging.debug('retry to get config in 30s.')
                self._finiEvent.wait(30)
                if self._finiEvent.isSet():
                    raise Exception('fini')
            raise Exception('abort')
        except Exception, e:
            if e.message == 'config':
                if platform.system().lower() == 'linux':
                    # 配置视频服务器
                    personId = personList[0]['personId']
                    if not self._imxFSM:
                        self._imxFSM = imxFSM(server = vsvrIp, port = vsvrPort, personId = personId, getDoctorList = self._serverAPI.getDoctorList)
                        self._imxFSM.setExitIdleCallback(self.cbEntryImxMode)
                        self._imxFSM.setEntryIdleCallback(self.cbExitImxMode)
                        self._imxFSM.setCallSoundCallback(self.cbCallSound)
                        self._buttonAPI.setCallCallback(self._imxFSM.cbButtonCall)
                        self._buttonAPI.setMuteCallback(self._imxFSM.cbButtonMute)

                    # 配置蓝牙手环
                    if not self._bandFSM:
                        _, mac = bracelet.get_bracelet_mac(1)
                        self._bandFSM = bandFSM(mac = mac)

                self._confUpdated = True     # 配置更新成功
                self.putEvent('evtConfigOk', self.evtConfigOk)
            elif e.message == 'abort':
                self.putEvent('evtFailed', self.evtFailed)
        finally:
            self._configThread = None
            logging.debug('serverFSM.configThread() fini.')

    # 后台心跳同步处理
    #   如果失败，间隔 30s 后重新同步
    #   尝试 6 次后重新登录
    def heartbeatThread(self):
        logging.debug('serverFSM.heartbeatThread().')
        try:
            self._finiEvent.wait(self._heartbeatInv)
            if self._finiEvent.isSet():
                raise Exception('fini')
            for retry in range(0, 6):
                ret, playVer, confVer = self._serverAPI.heatbeat(playVer = self._playVer if self._playUpdated else None,
                                                                 confVer = self._confVer if self._confUpdated else None)
                if ret:
                    if playVer and playVer != self._playVer:
                        self._playVer = playVer
                        self._playUpdated = False
                        self._mp3FSM.update(self.playUpdated)   # 更新音频列表
                    if confVer and confVer != self._confVer:
                        self._confVer = confVer
                        self._confUpdated = False
                        self.putEvent('evtConfig', self.evtConfig)   # 重新更新配置
                    raise Exception('ok')
                logging.debug('heartbeat failed.')
                logging.debug('retry to heatbeat in 30s.')
                self._finiEvent.wait(30)
                if self._finiEvent.isSet():
                    raise Exception('fini')
            logging.debug('heatbeat timeout.')
            raise Exception('fail')
        except Exception as e:
            if e.message == 'ok':
                self.putEvent('evtHeartbeat', self.evtHeartbeat)
            elif e.message == 'fail':
                self.putEvent('evtFailed', self.evtFailed)
        finally:
            self._heartbeatThread = None
            logging.debug('serverFSM.heartbeatThread() fini.')

    # 系统服务器状态机后台线程
    def fsmThread(self):
        logging.debug('serverFSM.fsmThread().')
        try:
            self._finiEvent.clear()
            self.to_stateLogin()    # 切换到登录状态
            while True:
                ret, desc, event = self.getEvent()
                if ret:
                    if desc == 'fini':
                        raise Exception('fini')
                    else:
                        event()
                        logging.debug('serverFSM: state - %s', self.state)
        finally:
            self._finiEvent.set()
            self._eventQueue.queue.clear()
            self._eventQueue = None
            del self._eventList[:]
            self._fsmThread = None
            logging.debug('serverFSM.fsmThread() fini.')

    # 终止系统服务器状态机
    def fini(self):
        logging.debug('serverFSM.fini().')
        if self._mp3FSM:
            self._mp3FSM.fini()
        if platform.system().lower() == 'linux':
            if self._imxFSM:
                self._imxFSM.fini()
            if self._bandFSM:
                self._bandFSM.finit()
        if self._fsmThread:
            self.putEvent('fini', None)
            while self._fsmThread or self._loginThread or self._configThread or self._heartbeatThread:
                time.sleep(0.5)
        self._fsmThread = None


###############################################################################
# 测试程序
if __name__ == '__main__':
    try:
        fsm = serverFSM(hostName = 'https://ttyoa.com', portNumber = '8098', robotId = 'b827eb319c88')
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        fsm.fini()
        sys.exit(0)
