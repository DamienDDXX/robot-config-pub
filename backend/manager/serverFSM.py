#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import Queue
import logging
import threading
from transitions import Machine, State

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from utility import setLogging
from manager import serverAPI, mp3FSM

__all__ = [
        'init',
        'fini',
        'putEvent',
        'getEvent',
        'setPlayUpdated'
        ]

# HEARTBEAT_INV   = 10 * 60
HEARTBEAT_INV   = 60

# 局部变量
_hostName       = None
_portNumber     = None
_token          = None
_robotId        = None

_playVer        = None
_confVer        = None
_playUpdated    = False
_confUpdated    = False

_loginThread    = None
_configThread   = None
_heartbeatThread = None

_eventQueue     = None
_eventList      = []

_fsmThread      = None
_fsmFini        = False

_fsm            = None
_machine        = None
_states         = [
        State(name = 'stateLogin',      on_enter = 'actLogin',      ignore_invalid_triggers = True),
        State(name = 'stateConfig',     on_enter = 'actConfig',     ignore_invalid_triggers = True),
        State(name = 'stateHeartbeat',  on_enter = 'actHeartbeat',  ignore_invalid_triggers = True),
        ]
_transitions    = [
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


# 后台登录线程
#   如果登录失败，每隔 30s 重新登录
def loginThread():
    global _loginThread, _fsm, _fsmFini, _hostName, _portNumber, _token
    logging.debug('serverFSM.loginThread().')
    try:
        while True:
            ret, _token = serverAPI.login()
            if ret:
                raise Exception('login')
            logging.debug('login failed')
            logging.debug('retry to login in 30s.')
            for wait in range(0, 30):
                if _fsmFini:
                    raise Exception('fini')
                time.sleep(1)
    except Exception, e:
        if e.message == 'login':
            mp3FSM.init(_hostName, _portNumber, _token)
            putEvent(_fsm.evtLoginOk)
    finally:
        _loginThread = None
        logging.debug('serverFSM.loginThread() fini.')


# 后台获取配置
#   如果失败，间隔 30s 后重新获取
#   尝试 6 次后重新登录
def configThread():
    global _configThread, _fsm, _fsmFini, _confUpdated
    logging.debug('serverFSM.configThread().')
    try:
        for retry in range(0, 6):
            ret, vsvrIp, vsvrIp, personList = serverAPI.getConfig()
            if ret:
                raise Exception('config')
            logging.debug('get config failed.')
            logging.debug('retry to get config in 30s.')
            for wait in range(0, 30):
                if _fsmFini:
                    raise Exception('fini')
                time.sleep(1)
        raise Exception('abort')
    except Exception, e:
        if e.message == 'config':
            # TODO:
            #   配置视频服务器
            #   配置蓝牙手环管理
            _confUpdated = True     # 配置更新成功
            putEvent(_fsm.evtConfigOk)
        elif e.message == 'abort':
            putEvent(_fsm.evtFailed)
    finally:
        _configThread = None
        logging.debug('serverFSM.configThread() fini.')


# 后台心跳同步处理
#   如果失败，间隔 30s 后重新同步
#   尝试 6 次后重新登录
def heartbeatThread():
    from manager import mp3FSM

    global _heartbeatThread, _fsm, _fsmFini, _playVer, _confVer, _playUpdated, _confUpdated
    logging.debug('serverFSM.heartbeatThread().')
    try:
        for wait in range(0, HEARTBEAT_INV):    # 等待心跳时间间隔
            if _fsmFini:
                raise Exception('fini')
            time.sleep(1)

        for retry in range(0, 6):
            ret, playVer, confVer = serverAPI.heatbeat(playVer = _playVer if _playUpdated else None,
                                                       confVer = _confVer if _confUpdated else None)
            if ret:
                _playVer, _playUpdated = playVer, False if playVer else _playUpdated
                _confVer, _confUpdated = confVer, False if confVer else _confUpdated
                if playVer:
                    mp3FSM.updatePlay()         # 更新音频列表
                    _playUpdated = True
                if _confVer:
                    putEvent(_fsm.evtConfig)    # 重新更新配置
                raise Exception('ok')

            logging.debug('heartbeat failed.')
            logging.debug('retry to heatbeat in 30s.')
            for wait in range(0, 30):
                if _fsmFini:
                    raise Exception('fini')
                time.sleep(1)
        logging.debug('heatbeat timeout.')
        raise Exception('fail')
    except Exception as e:
        if e.message == 'ok':
            putEvent(_fsm.evtHeartbeat)
        elif e.message == 'fail':
            putEvent(_fsm.evtFailed)
    finally:
        _heartbeatThread = None
        logging.debug('serverFSM.heartbeatThread() fini.')


# 系统服务器状态机类定义
class serverFSM(object):
    # 登录服务器
    def actLogin(self):
        global _loginThread
        logging.debug('serverFSM.actLogin().')
        if not _loginThread:
            _loginThread = threading.Thread(target = loginThread)
            _loginThread.start()

    # 获取配置
    def actConfig(self):
        global _configThread
        logging.debug('serverFSM.actConfig().')
        if not _configThread:
            _configThread = threading.Thread(target = configThread)
            _configThread.start()

    # 心跳同步
    def actHeartbeat(self):
        global _heartbeatThread
        logging.debug('serverFSM.actHeartbeat().')
        if not _heartbeatThread:
            _heartbeatThread = threading.Thread(target = heartbeatThread)
            _heartbeatThread.start()


# 向系统服务器状态机事件队列中放事件
def putEvent(event):
    global _eventQueue, _eventList
    if _eventQueue:
        if event not in _eventList and not _eventQueue.full():
            logging.debug('serverFSM.putEvent().')
            _eventList.append(event)
            _eventQueue.put(event)
            return True
    return False


# 从系统服务器状态机事件队列中取事件
def getEvent():
    global _eventQueue, _eventList
    if _eventQueue:
        if not _eventQueue.empty():
            event = _eventQueue.get()
            logging.debug('serverFSM.getEvent().')
            _eventQueue.task_done()
            if event in _eventList:
                _eventList.remove(event)
            return event
    return None


# 设置音频更新完成
def setPlayUpdated():
    global _playVer, _playUpdated
    logging.debug('serverFSM.setPlayUpdated().')
    _playUpdated = True


# 系统服务器状态机后台线程
def fsmThread():
    global _fsmFini, _fsmThread, _fsm, _hostName, _portNumber, _token, _robotId
    logging.debug('serverFSM.fsmThread().')
    try:
        _fsmFini = False
        _fsm.to_stateLogin()    # 切换到登录状态
        while True:
            if _fsmFini:
                raise Exception('fini')
            event = getEvent()
            if event:
                event()
                logging.debug('serverFSM: state - %s', _fsm.state)
            time.sleep(0.5)
    finally:
        _fsmThread = None
        logging.debug('serverFSM.fsmThread() fini.')


# 初始化系统服务状态机
def init(hostName, portNumber, robotId):
    global _hostName, _portNumber, _robotId
    global _fsm, _machine, _states, _transitions
    global _eventQueue, _eventList
    global _fsmThread
    logging.debug('serverFSM.init().')
    if not _fsm:
        _hostName, _portNumber, _robotId = hostName, portNumber, robotId
        _fsm = serverFSM()
        _machine = Machine(_fsm, states = _states, transitions = _transitions, ignore_invalid_triggers = True)
        _eventQueue = Queue.Queue(5)
        del _eventList[:]
        if not _fsmThread:
            serverAPI.init(_hostName, _portNumber, _robotId)
            _fsmThread = threading.Thread(target = fsmThread)
            _fsmThread.start()


# 终止系统服务器状态机
def fini():
    global _fsmFini, _fsmThread, _loginThread, _configThread, _heartbeatThread
    logging.debug('serverFSM.fini().')
    if _fsmThread:
        _fsmFini = True
        while _fsmThread or _loginThread or _configThread or _heartbeatThread:
            time.sleep(0.5)
    mp3FSM.fini()



###############################################################################
# 测试程序
if __name__ == '__main__':
    try:
        hostName, portNumber, robotId = 'https://ttyoa.com', '8098', 'b827eb319c88'
        init(hostName, portNumber, robotId)
        while (1):
            time.sleep(1)
    except KeyboardInterrupt:
        fini()
        sys.exit(0)
