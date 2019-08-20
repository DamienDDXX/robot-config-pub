#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import Queue
import threading
import logging
from transitions import Machine, State

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from manager import bandAPI as band

__all__ = [
        'init',
        'fini',
        'putEvent',
        'getEvent'
        ]

logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(filename)s[line:%(lineno)d] - %(thread)d - %(levelname)s - %(message)s')

# 局部变量
_mac        = None
_inv        = 30 * 60
_eventList  = []
_eventQueue = None

_fsmThread  = None
_fsmFini    = False

_errorTimeoutThread = None
_monitorInvThread   = None

_fsm        = None
_machine    = None
_states     = [
        State(name = 'stateInit',   on_enter = 'entryInit',     on_exit = 'exitInit'),      # 初始状态
        State(name = 'stateError',  on_enter = 'entryError',    on_exit = 'exitError'),     # 错误状态
        State(name = 'stateIdle',   on_enter = 'entryIdle',     on_exit = 'exitIdle'),      # 空闲状态
        State(name = 'stateScan',   on_enter = 'entryScan',     on_exit = 'exitScan'),      # 扫描状态
        State(name = 'stateMonitor',on_enter = 'entryMonitor',  on_exit = 'exitMonitor')    # 监控状态
        ]
_transitios = [
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


# 错误超时处理
#   间隔 30s 重新初始化
def errorTimeout():
    global _machine, _errorTimeoutThread
    logging.debug('bandFSM.errorTimeout().')
    while True:
        time.sleep(30)
        if putEvent(_machine.evtInit):
            break
    _errorTimeoutThread = None


# 定时监控处理
def monitorInv():
    global _machine, _monitorInvThread
    logging.debug('bandFSM.monitorInv().')
    time.sleep(_inv)
    putEvent(_machine.evtMonitor)
    _monitorInvThread = None


class bandFsm(object):
    # 进入初始化状态
    def entryInit(self):
        global _machine
        logging.debug('bandFSM.entryInit().')
        if band.init():
            putEvent(_machine.evtInitOk)
        else:
            putEvent(_machine.evtInitError)

    # 退出初始化状态
    def exitInit(self):
        logging.debug('bandFSM.exitInit().')

    # 进入错误状态
    def entryError(self):
        global _errorTimeoutThread
        logging.debug('bandFSM.entryError().')

        # TODO:
        #   通知液晶屏显示蓝牙错误状态

        # 启动手环错误处理线程，30s 后重新初始化
        if not _errorTimeoutThread:
            _errorTimeoutThread = threading.Thread(target = errorTimeout)
            _errorTimeoutThread.start()
            time.sleep(0.5)

    # 退出错误状态
    def exitError(self):
        logging.debug('bandFSM.exitError().')

    # 进入空闲状态
    def entryIdle(self):
        # 如果有手环配置，启动手环连接线程，指定时间间隔后连接手环
        global _mac, _monitorInvThread
        logging.debug('bandFSM.entryIdle().')
        if _mac:
            if not _monitorInvThread:
                _monitorInvThread = threading.Thread(target = monitorInv)
                _monitorInvThread.start()
                time.sleep(0.5)

    # 退出空闲状态
    def exitIdle(self):
        logging.debug('bandFSM.exitIdle().')

    # 进入扫描状态
    def entryScan(self):
        global _machine
        logging.debug('bandFSM.entryScan().')
        band.scan()
        putEvent(_machine.evtRelease)

    # 退出扫描状态
    def exitScan(self):
        logging.debug('bandFSM.exitScan().')

    # 进入监控状态
    def entryMonitor(self):
        global _machine
        logging.debug('bandFSM.entryMonitor().')
        if _mac:
            band.monitor(_mac)
        putEvent(_machine.evtRelease)

    # 退出监控状态
    def exitMonitor(self):
        logging.debug('bandFSM.exitMonitor().')


# 向手环状态事件队列中放事件
def putEvent(event):
    logging.debug('bandFSM.putEvent().')
    global _eventQueue, _eventList
    if _eventQueue:
        if event not in _eventList and not _eventQueue.full():
            _eventList.append(event)
            _eventQueue.put(event)
            return True
    return False


# 从手环状态事件队列中取事件
def getEvent():
    global _eventQueue, _eventList
    logging.debug('bandFSM.getEvent().')
    if _eventQueue:
        if not _eventQueue.empty():
            event = _eventQueue.get()
            _eventQueue.task_done()
            if event in _eventList:
                _eventList.remove(event)
            return event
    return None


# 手环状态机后台线程
def fsmThread():
    global _fsmFini, _fsmThread, _machine
    logging.debug('bandFSM.fsmThread().')
    while not _fsmFini:
        time.sleep(1)
        event = getEvent()
        if event:
            event()
            logging.debug('bandFSM(): state - %s' %_machine.state)
    _fsmThread = None


# 初始化手环状态机
def init(mac = None, inv = 30 * 60):
    global _fsm, _machine, _states, _transitios, _mac, _inv
    global _eventQueue, _eventList
    global _fsmThread, _fsmFini

    logging.debug('bandFSM.init().')
    if not _fsm:
        _mac = mac
        _inv = inv
        _fsm = bandFsm()
        _machine = Machine(_fsm, states = _states, transitions = _transitios, initial = 'stateInit', ignore_invalid_triggers = True)
        _eventQueue = Queue.Queue(5)
        del _eventList[:]

        if not _fsmThread:
            _fsmFini = False
            _fsmThread = threading.Thread(target = fsmThread)
            _fsmThread.start()


# 终止手环状态机
def fini():
    global _fsmFini, _fsmThread
    if _fsmThread:
        _fsmFini = True
        while _fsmThread:
            time.sleep(1)

