#!/usr/bin/python
# -*- coding: utf8 -*-

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
if platform.system().lower() == 'windows':
    from manager import bandSIM as band
elif platform.system().lower() == 'linux':
    from manager import bandAPI as band
else:
    raise NotImplementedError

__all__ = [
        'init',
        'fini',
        'putEvent',
        'getEvent'
        ]

MONITOR_INV = 30 * 60

# 局部变量
_mac            = None
_inv            = MONITOR_INV
_eventList      = []
_eventQueue     = None

_fsmThread      = None
_fsmFini        = False

_timerThread    = None
_scanThread     = None
_monitorThread  = None

_fsm            = None
_machine        = None
_states         = [
        State(name = 'stateInit',   on_enter = 'actInit',       ignore_invalid_triggers = True),    # 初始状态
        State(name = 'stateError',  on_enter = 'actReinit',     ignore_invalid_triggers = True),    # 错误状态
        State(name = 'stateIdle',   on_enter = 'actIdle',       ignore_invalid_triggers = True),    # 空闲状态
        State(name = 'stateScan',   on_enter = 'actScan',       ignore_invalid_triggers = True),    # 扫描状态
        State(name = 'stateMonitor',on_enter = 'actMonitor',    ignore_invalid_triggers = True)     # 监控状态
        ]
_transitions     = [
        # 初始状态 ------->
        {
            'trigger':  'evtInitOk',
            'source':   'stateInit',
            'dest':     'stateIdle'
        },
        {
            'trigger':  'evtError',
            'source':   'stateInit',
            'dest':     'stateError'
        },
        # 错误状态 ------->
        {
            'trigger':  'evtInit',
            'source':   'stateError',
            'dest':     'stateInit'
        },
        # 空闲状态 ------->
        {
            'trigger':  'evtMonitor',
            'source':   'stateIdle',
            'dest':     'stateMonitor'
        },
        {
            'trigger':  'evtScan',
            'source':   'stateIdle',
            'dest':     'stateScan',
        },
        # 扫描状态 ------->
        {
            'trigger':  'evtRelease',
            'source':   'stateScan',
            'dest':     'stateIdle'
        },
        # 监控状态 ------->
        {
            'trigger':  'evtRelease',
            'source':   'stateMonitor',
            'dest':     'stateIdle',
        },
        ]


# 定时器线程
def timerThread(timeout, event):
    global _fsmFini, _timerThread
    logging.debug('bandFSM.timerThread().')
    for i in range(0, 2 * timeout):
        if _fsmFini:
            break
        time.sleep(0.5)
    if not _fsmFini and event:
        putEvent(event)
    logging.debug('bandFSM.timerThread() fini.')


# 扫描手环线程
def scanThread(event):
    global _scanThread
    logging.debug('bandFSM.scanThread().')
    band.scan()
    if event:
        putEvent(event)
    logging.debug('bandFSM.scanThread() fini.')
    _scanThread = None


# 手环监控线程
def monitorThread(event):
    global _monitorThread
    logging.debug('bandFSM.monitorThread().')
    band.monitor()
    if event:
        putEvent(event)
    logging.debug('bandFSM.monitorThread() fini.')
    _monitorThread = None


# 手环管理状态机类
class bandFSM(object):
    # 初始化
    def actInit(self):
        global _fsm
        logging.debug('bandFSM.actInit().')
        if band.init():
            putEvent(_fsm.evtInitOk)
        else:
            putEvent(_fsm.evtError)

    # 重新初始化
    def actReinit(self):
        global _fsm, _timerThread
        logging.debug('bandFSM.actReinit().')
        if not _timerThread:
            # 30s 后重新初始化
            _timerThread = threading.Thread(target = timerThread, args = [30, _fsm.evtInit, ])
            _timerThread.start()

    # 空闲处理
    def actIdle(self):
        global _timerThread, _mac, _inv
        logging.debug('bandFSM.actIdle().')
        if _mac and not _timerThread:
            # 间隔指定时间后监控健康数据
            _timerThread = threading.Thread(target = timerThread, args = [_inv, _fsm.evtMonitor])

    # 扫描手环
    def actScan(self):
        global _fsm, _scanThread
        logging.debug('bandFSM.actScan().')
        if not _scanThread:
            _scanThread = threading.Thread(target = scanThread, args = [_fsm.evtRelease, ])
            _scanThread.start()

    # 手环监控
    def actMonitor(self):
        global _fsm, _monitorThread
        logging.debug('bandFSM.actMonitor().')
        if not _monitorThread:
            _monitorThread = threading.Thread(target = monitorThread, args = [_fsm.evtRelease, ])
            _monitorThread.start()


# 向手环管理状态机事件队列中放事件
def putEvent(event):
    global _eventQueue, _eventList
    logging.debug('bandFSM.putEvent().')
    if _eventQueue:
        if event not in _eventList and not _eventQueue.full():
            _eventList.append(event)
            _eventQueue.put(event)
            return True
    return False


# 从手环管理状态机事件队列中取事件
def getEvent():
    global _eventQueue, _eventList
    if _eventQueue:
        if not _eventQueue.empty():
            logging.debug('bandFSM.getEvent().')
            event = _eventQueue.get()
            _eventQueue.task_done()
            if event in _eventList:
                _eventList.remove(event)
            return event
    return None


# 手环服务器状态机后台线程
def fsmThread():
    global _fsmFini, _fsmThread, _fsm
    logging.debug('bandFSM.fsmThread().')
    _fsmFini = False
    _fsm.to_stateIdle()
    while not _fsmFini:
        time.sleep(0.5)
        event = getEvent()
        if event:
            event()
            logging.debug('bandFSM: state - %s', _fsm.state)
    _fsmThread = None
    logging.debug('bandFSM.fsmThread() fini.')


# 初始化手环管理状态机
def init(mac = None, inv = MONITOR_INV):
    global _mac, _inv
    global _fsm, _machine, _states, _transitions
    global _eventList, _eventQueue
    global _fsmThread
    logging.debug('bandFSM.init().')
    if not _fsm:
        _mac, _inv = mac, inv
        _fsm = bandFSM()
        _machine = Machine(_fsm, states = _states, transitions = _transitions, ignore_invalid_triggers = True)
        _eventQueue = Queue.Queue(5)
        del _eventList[:]
        if not _fsmThread:
            _fsmThread = threading.Thread(target = fsmThread)
            _fsmThread.start()


# 终止手环管理状态机
def fini():
    global _fsmFini, _fsmThread, _eventList, _eventQueue
    logging.debug('bandFSM.fini().')
    if _fsmThread:
        _fsmFini = False
        while _fsmThread:
            time.sleep(0.5)
    del _eventList[:]
    _eventQueue = None


################################################################################
# 测试程序
if __name__ == '__main__':
    try:
        ret, mac = band.getBand()
        if ret:
            init(mac, 1 * 60)
            while (1):
                time.sleep(1)
    except KeyboardInterrupt:
        fini()
        sys.exit(0)

