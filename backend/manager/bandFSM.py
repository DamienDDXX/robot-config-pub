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
from manager.bandAPI import bandAPI

__all__ = [
        'bandFSM',
        ]

MONITOR_INV = 30 * 60


# 手环管理状态机类
class bandFSM(object):
    # 初始化
    def __init__(self, inv = MONITOR_INV):
        self._bandAPI = bandAPI()
        self._inv = inv
        _, self._mac = self._bandAPI.getBand()
        self._timerThread = None
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
        self._finiEvent = threading.Event()
        self._finiEvent.clear()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    # 初始化
    def actInit(self):
        logging.debug('bandFSM.actInit().')
        if self.bandAPI.init():
            self.putEvent(self.evtInitOk)
        else:
            self.putEvent(self.evtError)

    # 重新初始化
    def actReinit(self):
        logging.debug('bandFSM.actReinit().')
        if not self._timerThread:
            # 30s 后重新初始化
            self._timerThread = threading.Thread(target = self.timerThread, args = [30, self.evtInit, ])
            self._timerThread.start()

    # 空闲处理
    def actIdle(self):
        logging.debug('bandFSM.actIdle().')
        if self._mac and not self._timerThread:
            # 间隔指定时间后监控健康数据
            self._timerThread = threading.Thread(target = self.timerThread, args = [self._inv, self.evtMonitor])

    # 扫描手环
    def actScan(self):
        logging.debug('bandFSM.actScan().')
        if not self._scanThread:
            self._scanThread = threading.Thread(target = self.scanThread, args = [self.evtRelease, ])
            self._scanThread.start()

    # 手环监控
    def actMonitor(self):
        logging.debug('bandFSM.actMonitor().')
        if not self._monitorThread:
            self._monitorThread = threading.Thread(target = self.monitorThread, args = [self.evtRelease, ])
            self._monitorThread.start()

    # 向手环管理状态机事件队列中放事件
    def putEvent(self, event):
        logging.debug('bandFSM.putEvent().')
        if self._eventQueue:
            if event not in self._eventList and not self._eventQueue.full():
                self._eventList.append(event)
                self._eventQueue.put(event)
                return True
        return False

    # 从手环管理状态机事件队列中取事件
    def getEvent(self):
        if self._eventQueue:
            if not self._eventQueue.empty():
                logging.debug('bandFSM.getEvent().')
                event = self._eventQueue.get()
                self._eventQueue.task_done()
                if event in self._eventList:
                    self._eventList.remove(event)
                return event
        return None

    # 手环服务器状态机后台线程
    def fsmThread(self):
        logging.debug('bandFSM.fsmThread().')
        try:
            self._finiEvent.clear()
            self.to_stateIdle()
            while True:
                self._finiEvent.wait(0.5)
                if self._finiEvent.isSet():
                    raise Exception('fini')
                event = self.getEvent()
                if event:
                    event()
                    logging.debug('bandFSM: state - %s', self.state)
        except Exception:
            pass
        finally:
            self._fsmThread = None
            logging.debug('bandFSM.fsmThread() fini.')

    # 定时器线程
    def timerThread(self, timeout, event):
        logging.debug('bandFSM.timerThread().')
        self._finiEvent.wait(timeout)
        if not self._finiEvent.isSet() and event:
            self.putEvent(event)
        logging.debug('bandFSM.timerThread() fini.')

    # 扫描手环线程
    def scanThread(self, event):
        logging.debug('bandFSM.scanThread().')
        self.bandAPI.scan()
        if event:
            self.putEvent(event)
        logging.debug('bandFSM.scanThread() fini.')
        self._scanThread = None

    # 手环监控线程
    def monitorThread(self, event):
        logging.debug('bandFSM.monitorThread().')
        self.bandAPI.monitor()
        if event:
            self.putEvent(event)
        logging.debug('bandFSM.monitorThread() fini.')
        self._monitorThread = None

    # 终止手环管理状态机
    def fini(self):
        logging.debug('bandFSM.fini().')
        if self._fsmThread:
            self._finiEvent.set()
            while self._fsmThread:
                time.sleep(0.5)
        del self._eventList[:]
        self._eventQueue = None


################################################################################
# 测试程序
if __name__ == '__main__':
    try:
        bf = bandFSM(inv = 3 * 60)
        while (1):
            time.sleep(1)
    except KeyboardInterrupt:
        bf.fini()
        sys.exit(0)

