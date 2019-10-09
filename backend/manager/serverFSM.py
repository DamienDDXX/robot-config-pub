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

from utility import setLogging, audioRecord

from manager.mp3FSM import mp3FSM
from manager.lcdFSM import lcdFSM
from manager.serverAPI import serverAPI
from manager.buttonAPI import buttonAPI
if platform.system().lower() == 'linux':
    from manager.imxFSM import imxFSM
    from manager.bandFSM import bandFSM
    from data_access import bracelet
    from utility import audioRecord

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
        self._softVer = 1.01
        self._confUpdated = False
        self._playUpdated = False

        self._loginThread = None
        self._loginFiniEvent = threading.Event()
        self._loginDoneEvent = threading.Event()

        self._configThread = None
        self._configFiniEvent = threading.Event()
        self._configDoneEvent = threading.Event()

        self._heartbeatThread = None
        self._heartbeatFiniEvent = threading.Event()
        self._heartbeatDoneEvent = threading.Event()

        self._mp3FSM = None
        self._imxFSM = None
        self._bandFSM = None
        self._lcdFSM = lcdFSM()
        self._buttonAPI = buttonAPI()
        self._buttonAPI.setPowerCallback(self._lcdFSM._lcdAPI.backlit_switch)
        self._buttonAPI.setIncVolumeCallback(audioRecord.incVolume)
        self._buttonAPI.setDecVolumeCallback(audioRecord.decVolume)

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

        # 初始化麦克风灵敏度和扬声器音量
        audioRecord.captureInit()
        audioRecord.volumeInit()

        # 播放启动音效
        audioRecord.soundStartup(wait = True)

        # 启动状态机线程
        self._eventList = []
        self._eventQueue = Queue.Queue(5)
        self._machine = Machine(self, states = self._states, transitions = self._transitions, ignore_invalid_triggers = True)
        self._fsmDoneEvent = threading.Event()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    # 登录服务器
    def actLogin(self):
        logging.debug('serverFSM.actLogin().')
        self.loginInit()

    # 获取配置
    def actConfig(self):
        logging.debug('serverFSM.actConfig().')
        self.configInit()

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
            self._loginDoneEvent.clear()
            self._loginFiniEvent.clear()
            while True:
                ret, self._token = self._serverAPI.login()
                if ret:
                    raise Exception('login')
                logging.debug('login failed')
                logging.debug('retry to login in 30s.')
                self._loginFiniEvent.wait(30)
                if self._loginFiniEvent.isSet():
                    raise Exception('fini')
        except Exception, e:
            if e.message == 'login':
                # 登录成功
                self._lcdFSM.lcdIdle()
                audioRecord.soundConnected(wait = True)
                if not self._mp3FSM:
                    # 创建音频管理状态机
                    self._mp3FSM = mp3FSM(hostName = self._hostName,
                                          portNumber = self._portNumber,
                                          token = self._token,
                                          getMp3List = self._serverAPI.getMp3List,
                                          lcdPlay = self._lcdFSM.lcdPlay,
                                          lcdIdle = self._lcdFSM.lcdIdle)
                    self._buttonAPI.setPlayCallback(self._mp3FSM.cbButtonPlay)
                    if platform.system().lower() == 'windows':
                        self._buttonAPI.setRadioCallback(self._mp3FSM.cbButtonRadio)
                        self._buttonAPI.setImxCallback(self._mp3FSM.cbButtonImx)
                self.putEvent('evtLoginOk', self.evtLoginOk)
        finally:
            logging.debug('serverFSM.loginThread() fini.')
            self._loginThread = None
            self._loginDoneEvent.set()

    # 启动登录
    def loginInit(self):
        logging.debug('serverFSM.loginInit().')
        if not self._loginThread:
            self._loginThread = threading.Thread(target = self.loginThread)
            self._loginThread.start()

    # 终止登录
    def loginFini(self):
        logging.debug('serverFSM.loginFini().')
        if self._loginThread:
            self._loginFiniEvent.set()
            self._loginDoneEvent.wait()

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

    # 后台获取配置
    #   如果失败，间隔 30s 后重新获取
    #   尝试 6 次后重新登录
    def configThread(self):
        logging.debug('serverFSM.configThread().')
        try:
            self._configDoneEvent.clear()
            self._configFiniEvent.clear()
            for retry in range(0, 6):
                ret, vsvrIp, vsvrPort, personList = self._serverAPI.getConfig()
                if ret:
                    raise Exception('config')
                logging.debug('get config failed.')
                logging.debug('retry to get config in 30s.')
                self._configFiniEvent.wait(30)
                if self._configFiniEvent.isSet():
                    raise Exception('fini')
            raise Exception('abort')
        except Exception, e:
            if e.message == 'config':
                if platform.system().lower() == 'linux':
                    # 配置视频服务器
                    personId = personList[0]['personId']
                    if not self._imxFSM:
                        self._imxFSM = imxFSM(server = vsvrIp,
                                              port = vsvrPort,
                                              personId = personId,
                                              getDoctorList = self._serverAPI.getDoctorList,
                                              saveCallLog = self._serverAPI.saveCallLog,
                                              lcdImx = self._lcdFSM.lcdImx,
                                              lcdIdle = self._lcdFSM.lcdIdle)
                        self._imxFSM.setExitIdleCallback(self.cbEntryImxMode)
                        self._imxFSM.setEntryIdleCallback(self.cbExitImxMode)
                        self._buttonAPI.setCallCallback(self._imxFSM.cbButtonCall)
                        self._buttonAPI.setMuteCallback(self._imxFSM.cbButtonMute)

                    # 配置蓝牙手环
                    if not self._bandFSM:
                        _, mac = bracelet.get_bracelet_mac(1)
                        self._bandFSM = bandFSM(mac = mac)

                self._confUpdated = True     # 配置更新成功
                self.putEvent('evtConfigOk', self.evtConfigOk)
            elif e.message == 'abort':
                self._lcdFSM.lcdOffline()
                audioRecord.soundOffline(wait = True)
                self.putEvent('evtFailed', self.evtFailed)
        finally:
            logging.debug('serverFSM.configThread() fini.')
            self._configThread = None
            self._configDoneEvent.set()

    # 开始配置
    def configInit(self):
        logging.debug('serverFSM.configInit().')
        if not self._configThread:
            self._configThread = threading.Thread(target = self.configThread)
            self._configThread.start()

    # 终止配置
    def configFini(self):
        logging.debug('serverFSM.configFini().')
        if self._configThread:
            self._configFiniEvent.set()
            self._configDoneEvent.wait()

    # 后台心跳同步处理
    #   如果失败，间隔 30s 后重新同步
    #   尝试 6 次后重新登录
    def heartbeatThread(self):
        logging.debug('serverFSM.heartbeatThread().')
        try:
            self._heartbeatDoneEvent.clear()
            self._heartbeatFiniEvent.clear()
            self._heartbeatFiniEvent.wait(self._heartbeatInv)
            if self._heartbeatFiniEvent.isSet():
                raise Exception('fini')
            for retry in range(0, 6):
                ret, playVer, confVer, softVer = self._serverAPI.heatbeat(playVer = self._playVer if self._playUpdated else None,
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
                    if softVer and softVer != self._softVer:
                        # TODO:
                        #   启动更新机器人固件操作
                        pass
                    raise Exception('ok')
                logging.debug('heartbeat failed.')
                logging.debug('retry to heatbeat in 30s.')
                self._heartbeatFiniEvent.wait(30)
                if self._heartbeatFiniEvent.isSet():
                    raise Exception('fini')
            logging.debug('heatbeat timeout.')
            raise Exception('fail')
        except Exception as e:
            if e.message == 'ok':
                self.putEvent('evtHeartbeat', self.evtHeartbeat)
            elif e.message == 'fail':
                self._lcdFSM.lcdOffline()
                audioRecord.soundOffline(wait = True)
                self.putEvent('evtFailed', self.evtFailed)
        finally:
            logging.debug('serverFSM.heartbeatThread() fini.')
            self._heartbeatThread = None
            self._heartbeatDoneEvent.set()

    # 启动心跳同步
    def heatbeatInit(self):
        logging.debug('serverFSM.heatbeatInit().')
        if not self._heartbeatThread:
            self._heartbeatThread = threading.Thread(target = self.heartbeatThread)
            self._heartbeatThread.start()

    # 终止心跳同步
    def heatbeatFini(self):
        logging.debug('serverFSM.heatbeatFini().')
        if self._heartbeatThread:
            self._heartbeatFiniEvent.set()
            self._heartbeatDoneEvent.wait()

    # 系统服务器状态机后台线程
    def fsmThread(self):
        logging.debug('serverFSM.fsmThread().')
        try:
            self._fsmDoneEvent.clear()
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
            self.loginFini()
            self.configFini()
            self.heatbeatFini()

            self._eventQueue.queue.clear()
            self._eventQueue = None
            del self._eventList[:]
            logging.debug('serverFSM.fsmThread() fini.')
            self._fsmThread = None
            self._fsmDoneEvent.set()

    # 终止系统服务器状态机
    def fini(self):
        logging.debug('serverFSM.fini().')
        if self._mp3FSM:
            self._mp3FSM.fini()
        if platform.system().lower() == 'linux':
            if self._imxFSM:
                self._imxFSM.fini()
            if self._bandFSM:
                self._bandFSM.fini()
        if self._fsmThread:
            self.putEvent('fini', None)
            self._fsmDoneEvent.wait()


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
