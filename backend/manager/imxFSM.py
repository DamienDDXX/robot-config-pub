#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import Queue
import threading
from transitions import Machine, State

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from manager import imxAPI
from utility import setLogging
if platform.system().lower() == 'windows':
    import manager.buttonSIM as button
elif platform.system().lower() == 'linux':
    import manager.buttonAPI as button
else:
    raise NotImplementedError

__all__ = [
        'init',
        'fini',
        'reInit',
        'putEvent',
        'getEvent',
        ]

ROLE_VD     = 14    # 乡村医生 - Village Doctor
ROLE_PHD    = 3     # 公共卫生医生 - Public Health Doctor
ROLE_NURSE  = 2     # 护士
ROLE_GP     = 1     # 全科医生 - General Practitioner
ROLE_SERVER = 15    # 在线服务员

# 呼叫顺序：村医 -> 公共卫生医师 -> 护士 -> 全科医生 -> 在线服务员
_callOrdList = [ ROLE_VD, ROLE_PHD, ROLE_NURSE, ROLE_GP, ROLE_SERVER ]

# 局部变量
_server     = None
_port       = None
_personId   = None
_userId     = None
_destId     = None
_autoAccept = False
_callCancel = False

_eventList  = []
_eventQueue = None

_fsmFini    = False
_fsmThread  = None

_fsm        = None
_machine    = None
_states     = [
        State(name = 'stateOffline',    on_enter = 'actLogin',      ignore_invalid_triggers = True),
        State(name = 'stateIdle',                                   ignore_invalid_triggers = True),
        State(name = 'stateCall',       on_enter = 'actCall',       ignore_invalid_triggers = True),
        State(name = 'stateWaitAccept', on_enter = 'actWaitCall',   ignore_invalid_triggers = True),
        State(name = 'stateIncoming',   on_enter = 'actAccept',     ignore_invalid_triggers = True),
        State(name = 'stateEstablished',                            ignore_invalid_triggers = True),
        ]
_transitions = [
        # 任意状态 -------> 离线状态
        {
            'trigger':  'evtOffline',
            'source':   '*',
            'dest':     'stateOffline',
            'before':   'actLogout'
        },
        # 任意状态 -------> 空闲状态
        {
            'trigger':  'evtRelease',
            'source':   '*',
            'dest':     'stateIdle',
            'before':   'actHangup'
        },
        # 离线状态 ------->
        {
            'trigger':  'evtLoginOk',
            'source':   'stateOffline',
            'dest':     'stateIdle'
        },
        # 空闲状态 ------->
        {
            'trigger':  'evtBtnCall',
            'source':   'stateIdle',
            'dest':     'stateCall'
        },
        {
            'trigger':  'evtIncomming',
            'source':   'stateIdle',
            'dest':     'stateWaitAccept'
        },
        # 呼出状态 ------->
        {
            'trigger':  'evtBtnCall',
            'source':   'stateCall',
            'dest':     'stateIdle',
            'before':   'actHangup'
        },
        {
            'trigger':  'evtAccept',
            'source':   'stateCall',
            'dest':     'stateEstablished'
        },
        # 等待接听 ------->
        {
            'trigger':  'evtBtnCall',
            'source':   'stateWaitAccept',
            'dest':     'stateIncoming'
        },
        # 正在呼入 ------->
        {
            'trigger':  'evtAccept',
            'source':   'stateIncoming',
            'dest':     'stateEstablished'
        },
        # 建立状态 ------->
        {
            'trigger':  'evtBtnCall',
            'source':   'stateEstablished',
            'dest':     'stateIdle',
            'before':   'actHangup'
        }
        ]


# 后台登录线程
#   如果登录失败，30s 后再次登录
def loginThread(event):
    global _fsmFini, _loginThread
    logging.debug('imxFSM.loginThread().')
    try:
        while True:
            if imxAPI.login():
                raise 'login'
            for wait in range(0, 30):
                time.sleep(1)
                if _fsmFini:
                    raise Exception('fini')
    except Exception, e:
        if e.message == 'login' and event:
            putEvent(event)
    finally:
        _loginThread = None
        logging.debug('imxFSM.loginThread() fini.')


# 对在线医生进行优先级排序
def sortDoctor(doctorList):
    logging.debug('imxFSM.sortDoctor().')
    sortList = []
    for order in _callOrdList:
        for doctor in doctorList:
            if doctor['onlineSts'] == 'online' and str(order) in doctor['role'] and doctor not in sortList:
                sortList.append[doctor]
    return sortList


# 获取下一个在线医生
def nextDoctor(doctorList, doctorId):
    logging.debug('imxFSM.nextDoctor(%s).' %str(doctorId))
    if len(doctorList) > 0:
        if not doctorId:
            return doctorList[0]['id']
        for i in range(0, len(doctorList)):
            if doctorId == doctorList[i]['id']:
                i = i + 1
                if i < len(doctorList):
                    return doctorList[i]['id']
    return None


# 后台呼叫线程
#   依次根据在线医生的优先级进行呼叫
def callThread(doctorList, state, evtOk, evtFail):
    global _fsm, _fsmFini, _callThread, _callCancel
    logging.debug('imxFSM.callThread().')
    try:
        _callCancel = False,
        doctorId, doctorList = None, sortDoctor(doctorList)
        while True:
            doctorId = nextDoctor(doctorList, doctorId)
            if not doctorId:
                raise Exception('no answer')        # 遍历呼叫所有的医生，无应答
            imxAPI.call(doctorId)                   # 呼叫医生
            for wait in range(0, 2 * 30):           # 等待 30s 接听
                if imxAPI.accepted():
                    raise Exception('accepted')
                if _callCancel:
                    # 居民放弃呼叫
                    raise Exception('abort')
                if _fsmFini:
                    # 退出状态机
                    raise Exception('fini')
                time.sleep(0.5)
            imxAPI.hangup()
            time.sleep(1)
    except Exception as e:
        if e == 'accepted':
            logging.debug('call success: doctorId - %s.' %doctorId)
            if (state == None or _fsm.state == state) and evtOk:
                putEvent(evtOk)
        else:
            imxAPI.hangup()
            logging.debug('call failed: reason - %s.' %e)
            if (state == None or _fsm.state == state) and evtFail:
                putEvent(evtFail)
    finally:
        _callThread = None
        logging.debug('imxFSM.callThread() fini.')


# 视频状态机管理类定义
class imxFsm(object):
    # 登录
    def actLogin(self):
        global _loginThread
        logging.debug('imxFSM.actLogin().')
        if not _loginThread:
            # 启动后台登录
            _loginThread = threading.Thread(target = loginThread, args = [_fsm.evtLoginOk, ])
            _loginThread.start()

    # 登出
    def actLogout(self):
        logging.debug('imxFSM.actLogout().')
        imxAPI.logout()

    # 呼叫
    def actCall(self):
        from manager import serverAPI
        global _fsm, _personId, _callThread
        logging.debug('imxFSM.actCall().')
        ret, doctorList = serverAPI.getDoctorList(_personId)
        if ret:
            if not _callThread:
                # 启动后台呼叫
                _callThread = threading.Thread(target = callThread, args = [doctorList, _fsm.evtAccept, _fsm.evtRelease, ])
                _callThread.start()
        else:
            # 获取医生列表失败
            putEvent(_fsm.evtRelease)

    # 等待接听
    def actWaitCall(self):
        logging.debug('imxFSM.actWaitCall().')
        if _autoAccept:
            # 自动接入
            putEvent(_fsm.evtBtnCall)

    # 接听
    def actAccept(self):
        logging.debug('imxFSM.actAccept().')
        imxAPI.accept()

    # 挂断
    def actHangup(self):
        global _callCancel
        logging.debug('imxFSM.actHangup().')
        _callCancel = True
        imxAPI.hangup()

    # 拒接
    def actDecline(self):
        logging.debug('imxFSM.actDecline().')
        imxAPI.Decline()


# 向视频管理状态事件队列中放事件
def putEvent(event):
    global _eventQueue, _eventList
    if _eventQueue:
        if event not in _eventList and not _eventQueue.full():
            logging.debug('imxFSM.putEvent().')
            _eventList.append(event)
            _eventQueue.put(event)
            return True
    return False


# 从视频管理状态事件队列中取事件
def getEvent():
    global _eventQueue, _eventList
    if _eventQueue:
        if not _eventQueue.empty():
            logging.debug('imxFSM.getEvent().')
            event = _eventQueue.get()
            _eventQueue.task_done()
            if event in _eventList:
                _eventList.remove(event)
            return event
    return None


# 视频状态机后台线程
def fsmThread():
    global _server, _port, _personId
    global _fsmFini, _fsmThread
    logging.debug('imxFSM.fsmThread().')
    try:
        button.init()
        cb = button.setCallCallback(actBtnCall)
        imx.init(_server, _port, _personId)
        imx.getSDKVersion()
        _fsmFini = False
        while True:
            if _fsmFini:
                raise Exception('fini')
            event = getEvent()
            if event:
                event()
            time.sleep(0.5)
    except Exception, e:
        pass
    finally:
        _fsmThread = None
        imx.logout()
        imx.fini()
        button.setCallCallback(cb)
        logging.debug('imxFSM.fsmThread(). fini')


# 初始化视频状态机
def init(server, port, personId):
    global _fsm, _machine, _states
    global _server, _port, _personId
    global _eventQueue, _eventList
    global _fsmFini, _fsmThread
    logging.debug('imxFSM.init(%s, %s, %s)' %(server, port, personId))
    if not _fsm:
        _server, _port, _personId = server, port, personId
        _fsm = imxFsm()
        _machine = Machine(_fsm, states = _states, transitions = _transitions, initial = 'stateOffline')
        _eventQueue = Queue.Queue(5)
        del _eventList[:]
        if not _fsmThread:
            _fsmThread = threading.Thread(target = fsmThread)
            _fsmThread.start()


# 终止视频状态机
def fini():
    global _fsmFini, _fsmThread, _eventList, _eventQueue
    logging.debug('imxFSM.fini().')
    if _fsmThread:
        _fsmFini = True
        while _fsmThread:
            time.sleep(0.5)
    del _eventList[:]
    _eventQueue = None


################################################################################
# 测试程序
if __name__ == '__main__':
    import manager.serverAPI
    try:
        hostName, portNumber, robotId = 'https://ttyoa.com', '8098', 'b827eb319c88'
        manager.serverAPI.init(hostName, portNumber, robotId)
        ret, token = manager.serverAPI.login()
        if ret:
    except KeyboardInterrupt:
        fini()
        sys.exit(0)
