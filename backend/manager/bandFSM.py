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
from data_access import bracelet
from manager.bandAPI import bandAPI

__all__ = [
        'bandFSM',
        ]

# 宏定义
MONITOR_INV = 30 * 60

# 手环管理状态机类
class bandFSM(object):
    # 初始化
    def __init__(self, mac = None, inv = MONITOR_INV):
        self._bandAPI = bandAPI()
        self._mac = mac
        self._inv = inv

        self._timerThread = None
        self._timerFiniEvent = threading.Event()
        self._timerDoneEvent = threading.Event()

        self._scanThread = None
        self._monitorThread = None
        self._states = [
            State(name = 'stateInit',    on_enter = 'actInit',    ignore_invalid_triggers = True),    # 初始状态
            State(name = 'stateError',   on_enter = 'actReinit',  ignore_invalid_triggers = True),    # 错误状态
            State(name = 'stateIdle',    on_enter = 'actIdle',    ignore_invalid_triggers = True),    # 空闲状态
            State(name = 'stateScan',    on_enter = 'actScan',    ignore_invalid_triggers = True),    # 扫描状态
            State(name = 'stateMonitor', on_enter = 'actMonitor', ignore_invalid_triggers = True)     # 监控状态
        ]
        self._transitions = [
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

        self._machine = Machine(self, states = self._states, transitions = self._transitions, ignore_invalid_triggers = True)
        self._eventQueue = Queue.Queue(5)
        self._eventList = []

        self._fsmDoneEvent = threading.Event()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    # 初始化
    def actInit(self):
        logging.debug('bandFSM.actInit().')
        if self._bandAPI.init():
            self.putEvent('evtInitOk', self.evtInitOk)
        else:
            self.putEvent('evtError', self.evtError)

    # 重新初始化
    def actReinit(self):
        logging.debug('bandFSM.actReinit().')
        self.timerInit(30, 'evtInit', self.evtInit)

    # 空闲处理
    def actIdle(self):
        logging.debug('bandFSM.actIdle().')
        if self._mac:
            self.timerInit(self._inv, 'evtMonitor', self.evtMonitor)    # 间隔指定时间后监控健康数据

    # 扫描手环
    def actScan(self):
        logging.debug('bandFSM.actScan().')
        if not self._scanThread:
            self._scanThread = threading.Thread(target = self.scanThread, args = ['evtRelease', self.evtRelease, ])
            self._scanThread.start()

    # 手环监控
    def actMonitor(self):
        logging.debug('bandFSM.actMonitor().')
        if not self._monitorThread:
            self._monitorThread = threading.Thread(target = self.monitorThread, args = ['evtRelease', self.evtRelease, ])
            self._monitorThread.start()

    # 向手环管理状态机事件队列中放事件
    def putEvent(self, desc, event):
        if self._eventQueue:
            v = [desc, event]
            if v not in self._eventList and not self._eventQueue.full():
                logging.debug('bandFSM.putEvent(%s).' %desc)
                self._eventList.append(v)
                self._eventQueue.put(v)
                return True
        return False

    # 从手环管理状态机事件队列中取事件
    def getEvent(self):
        if self._eventQueue:
            v = self._eventQueue.get(block = True)
            self._eventQueue.task_done()
            logging.debug('bandFSM.getEvent(%s).' %v[0])
            if v in self._eventList:
                self._eventList.remove(v)
            return True, v[0], v[1]
        return False, None, None

    # 手环服务器状态机后台线程
    def fsmThread(self):
        logging.debug('bandFSM.fsmThread().')
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
                        logging.debug('bandFSM: state - %s', self.state)
        finally:
            self.timerFini()
            self._eventQueue.queue.clear()
            self._eventQueue = None
            del self._eventList[:]
            self._fsmThread = None
            self._fsmDoneEvent.set()
            logging.debug('bandFSM.fsmThread() fini.')

    # 定时器线程
    def timerThread(self, timeout, desc, event):
        logging.debug('bandFSM.timerThread(%s).' %desc)
        self._timerDoneEvent.clear()
        self._timerFiniEvent.clear()
        self._timerFiniEvent.wait(timeout)
        if not self._timerFiniEvent.isSet() and event:
            self.putEvent(desc, event)
        self._timerThread = None
        self._timerDoneEvent.set()
        logging.debug('bandFSM.timerThread(%s) fini.' %desc)

    # 启动定时器
    def timerInit(self, timeout, desc, event):
        logging.debug('bandFSM.timerInit(%s).' %desc)
        if self._timerThread:
            self.timerFini()
        self._timerThread = threading.Thread(target = self.timerThread, args = [timeout, desc, event, ])
        self._timerThread.start()

    # 停止定时器
    def timerFini(self):
        logging.debug('bandFSM.timerFini().')
        if self._timerThread:
            self._timerFiniEvent.set()
            self._timerDoneEvent.wait()

    # 扫描手环线程
    def scanThread(self, desc, event):
        logging.debug('bandFSM.scanThread(%s).' %desc)
        self._bandAPI.scan()
        if event:
            self.putEvent(desc, event)
        logging.debug('bandFSM.scanThread(%s) fini.' %desc)
        self._scanThread = None

    # 手环监控线程
    def monitorThread(self, desc, event):
        logging.debug('bandFSM.monitorThread(%s).' %desc)
        self._bandAPI.monitor(self._mac)
        if event:
            self.putEvent(desc, event)
        logging.debug('bandFSM.monitorThread(%s) fini.' %desc)
        self._monitorThread = None

    # 终止手环管理状态机
    def fini(self):
        logging.debug('bandFSM.fini().')
        if self._fsmThread:
            self.putEvent('fini', None)
            self._fsmDoneEvent.wait()


################################################################################
# 测试程序
if __name__ == '__main__':
    try:
        _, mac = bracelet.get_bracelet_mac(1)
        fsm = bandFSM(mac = mac, inv = 1 * 60)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        fsm.fini()
        sys.exit(0)

