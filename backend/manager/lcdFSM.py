#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import time
import random
import Queue
import logging
import platform
import threading
from transitions import Machine, State

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from manager.lcdAPI import lcdAPI

__all__ = [
        'lcdFSM'
        ]

# 液晶状态机管理类定义
class lcdFSM(object):
    # 初始化
    def __init__(self):
        self._lcdAPI = lcdAPI()

        self._aliveThread = None
        self._aliveFiniEvent = threading.Event()
        self._aliveDoneEvent = threading.Event()

        self._blinkThreak = None
        self._blinkFiniEvent = threading.Event()
        self._blinkDoneEvent = threading.Event()

        self._states = [
                State(name = 'stateIdle',       on_enter = 'actIdle',       ignore_invalid_triggers = True),
                State(name = 'stateOffline',    on_enter = 'actOffLine',    ignore_invalid_triggers = True),
                State(name = 'stateException',  on_enter = 'actException',  ignore_invalid_triggers = True),
                State(name = 'statePlay',       on_enter = 'actPlay',       ignore_invalid_triggers = True),
                State(name = 'stateImx',        on_enter = 'actImx',        ignore_invalid_triggers = True),
                ]
        self._transitions = [
                {
                    'trigger':  'evtPlay',
                    'source':   '*',
                    'dest':     'statePlay',
                },
                {
                    'trigger':  'evtImx',
                    'source':   '*',
                    'dest':     'stateImx',
                },
                {
                    'trigger':  'evtOffline',
                    'source':   '*',
                    'dest':     'stateOffline',
                },
                {
                    'trigger':  'evtException',
                    'source':   '*',
                    'dest':     'stateException',
                },
                {
                    'trigger':  'evtIdle',
                    'source':   '*',
                    'dest':     'stateIdle',
                }
            ]
        self._machine = Machine(self, states = self._states, transitions = self._transitions, ignore_invalid_triggers = True)
        self._eventQueue = Queue.Queue(5)
        self._eventList = []
        self._fsmDoneEvent = threading.Event()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    def fsmThread(self):
        logging.debug('lcdFSM.fsmThread().')
        try:
            self.aliveInit()
            self.blinkInit()

            self._fsmDoneEvent.clear()
            self.to_stateIdle()
            while True:
                ret, desc, event = self.getEvent()
                if ret:
                    if desc == 'fini':
                        raise Exception('fini')
                    else:
                        event()
                        logging.debug('lcdFSM: state - %s', self.state)
        finally:
            self.aliveFini()
            self.blinkFini()

            self._eventQueue.queue.clear()
            self._eventQueue = None
            del self._eventList[:]
            logging.debug('lcdFSM.fsmThread() fini.')
            self._fsmThread = None
            self._fsmDoneEvent.set()

    def fini(self):
        logging.debug('lcdFSM.fini().')
        if self._fsmThread:
            self.putEvent('fini', None)
            self._fsmDoneEvent.wait()

    def aliveThread(self):
        logging.debug('lcdFSM.aliveThread().')
        try:
            self._aliveFiniEvent.clear()
            self._aliveDoneEvent.clear()
            while True:
                for wait in range(0, 3 * 60):
                    time.sleep(1)
                    if self._aliveFiniEvent.isSet():
                        raise Exception('fini')
                self._lcdAPI.notify_alive()
        except Exception, e:
            pass
        finally:
            logging.debug('lcdFSM.aliveThread() fini.')
            self._aliveThread = None
            self._aliveDoneEvent.set()

    def aliveInit(self):
        logging.debug('lcdFSM.aliveInit().')
        if not self._aliveThread:
            self._aliveThread = threading.Thread(target = self.aliveThread)
            self._aliveThread.start()

    def aliveFini(self):
        logging.debug('lcdFSM.aliveFini().')
        if self._aliveThread:
            self._aliveFiniEvent.set()
            self._aliveDoneEvent.wait()

    def blinkThread(self):
        logging.debug('lcdFSM.blinkThread().')
        try:
            while True:
                wait = random.randint(3, 12)
                for wait in range(wait):
                    if self._blinkFiniEvent.isSet():
                        raise Exception('fini')
                    time.sleep(1)
                self._lcdAPI.page_blink()
                time.sleep(1)
                if self.state == 'stateIdle':
                    self._lcdAPI.page_wait()
                elif self.state == 'statePlay':
                    self._lcdAPI.page_listen()
                elif self.state == 'statePlay':
                    self._lcdAPI.page_listen()
                elif self.state == 'stateImx':
                    self._lcdAPI.page_happy()
                elif self.state == 'StateOffline':
                    self._lcdAPI.page_sad()
                elif self.state == 'stateException':
                    self._lcdAPI.page_fail()
        except Exception, e:
            pass
        finally:
            logging.debug('lcdFSM.blinkThread() fini.')
            self._blinkThreak = None
            self._blinkDoneEvent.set()

    def blinkInit(self):
        logging.debug('lcdFSM.blinkInit().')
        if not self._blinkThreak:
            self._blinkThreak = threading.Thread(target = self.blinkThread)
            self._blinkThreak.start()

    def blinkFini(self):
        logging.debug('lcdFSM.blinkFini().')
        if self._blinkThreak:
            self._blinkFiniEvent.set()
            self._blinkDoneEvent.wait()

    def actIdle(self):
        logging.debug('lcdFSM.actIdle().')
        self._lcdAPI.page_smile()

    def actOffLine(self):
        logging.debug('lcdFSM.actOffLine().')
        self._lcdAPI.page_sad()

    def actException(self):
        logging.debug('lcdFSM.actException().')
        self._lcdAPI.page_fail()

    def actPlay(self):
        logging.debug('lcdFSM.actPlay().')
        self._lcdAPI.page_listen()

    def actImx(self):
        logging.debug('lcdFSM.actPlay().')
        self._lcdAPI.page_happy()

    # 向状态机事件队列发送事件
    def putEvent(self, desc, event):
        if self._eventQueue:
            v = [desc, event]
            if v not in self._eventList and not self._eventQueue.full():
                logging.debug('lcdFSM.putEvent(%s).' %desc)
                self._eventList.append(v)
                self._eventQueue.put(v)
                return True
        return False

    # 从状态机事件队列提取事件
    def getEvent(self):
        if self._eventQueue:
            v = self._eventQueue.get(block = True)
            self._eventQueue.task_done()
            logging.debug('lcdFSM.getEvent(%s).' %v[0])
            if v in self._eventList:
                self._eventList.remove(v)
            return True, v[0], v[1]
        return False, None, None


###############################################################################
# 测试程序
if __name__ == '__main__':
    try:
        fsm = lcdFSM()
        while True:
            time.sleep(15)
            fsm.putEvent('evtPlay', fsm.evtPlay)
            time.sleep(15)
            fsm.putEvent('evtImx', fsm.evtImx)
            time.sleep(15)
            fsm.putEvent('evtOffline', fsm.evtOffline)
            time.sleep(15)
            fsm.putEvent('evtIdle', fsm.evtIdle)
    except KeyboardInterrupt:
        fsm.fini()
        sys.exit(0)

