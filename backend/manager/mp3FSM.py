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

import manager.mp3API    as mp3
import manager.buttonAPI as button


__all__ = [
        'init',
        'fini',
        'putEvent',
        'getEvent'
        ]


logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(filename)s[line:%(lineno)d] - %(thread)d - %(levelname)s - %(message)s')


# 局部变量
_radioThread    = None
_policyThread   = None
_updateThread   = None

_eventQueue     = None
_eventList      = []

_fsmThread      = None
_fsmFini        = False

_fsm            = None
_machine        = None
_states         = [
        State(name = 'stateInit',       on_entry = 'entryInit',     on_exit = 'exitInit',   ignore_invalid_triggers = True),
        State(name = 'stateIdle',       on_entry = 'entryIdle',     on_exit = 'exitIdle',   ignore_invalid_triggers = True),
        State(name = 'stateUpdate',     on_entry = 'entryUpdate',   on_exit = 'exitUpdate', ignore_invalid_triggers = True),
        State(name = 'stateUpdateEx',   on_entry = 'entryUpdate',   on_exit = 'exitUpdate', ignore_invalid_triggers = True),
        State(name = 'statePolicy',     on_entry = 'entryPolicy',   on_exit = 'exitPolicy', ignore_invalid_triggers = True),
        State(name = 'stateRadio',      on_entry = 'entryRadio',    on_exit = 'exitRadio',  ignore_invalid_triggers = True),
        State(name = 'stateRadioEx',    on_entry = 'entryRadio',    on_exit = 'exitRadio',  ignore_invalid_triggers = True)
        ]
_transitions    = [
        # 初始状态 ------->
        {
            'trigger':  'evtInitOk',
            'source':   'stateInit',
            'dest':     'stateIdle'
        },
        # 空闲状态 ------->
        {
            'trigger':  'evtBtnPlay',
            'source':   'stateIdle',
            'dest':     'statePolicy'
        },
        {
            'trigger':  'evtRadio',
            'source':   'stateIdle',
            'dest':     'stateRadio'
        },
        {
            'trigger':  'evtUpdate',
            'source':   'stateIdle',
            'dest':     'stateUpdate'
        },
        # 更新状态 ------->
        {
            'trigger':  'evtRelease',
            'source':   'stateUpdate',
            'dest':     'stateIdle'
        },
        # 更新状态 ------->
        {
            'trigger':  'evtRelease',
            'source':   'stateUpdateEx',
            'dest':     'statePolicy'
        },
        # 政策播放状态 --->
        {
            'trigger':  'evtRelease',
            'source':   'statePolicy',
            'dest':     'stateIdle'
        },
        {
            'trigger':  'evtBtnPlay',
            'source':   'statePolicy',
            'dest':     'stateIdle'
        },
        {
            'trigger':  'evtRadio',
            'source':   'statePolicy',
            'dest':     'stateRadioEx'
        },
        {
            'trigger':  'evtUpdate',
            'source':   'statePolicy',
            'dest':     'stateUpdateEx',
        },
        # 广播播放状态
        {
            'trigger':  'evtBtnPlay',
            'source':   'stateRadio',
            'dest':     'stateIdle'
        },
        {
            'trigger':  'evtRelease',
            'source':   'stateRadio',
            'dest':     'stateIdle'
        },
        # 广播播放状态
        {
            'trigger':  'evtBtnPlay',
            'source':   'stateRadioEx',
            'dest':     'statePolicy'
        },
        {
            'trigger':  'evtRelease',
            'source':   'stateRadioEx',
            'dest':     'statePolicy'
        },
        ]


# 播放按键动作
def actBtnPlay():
    global _fsm, _fsmThread
    logging.debug('mp3FSM.actBtnPlay().')
    if _fsmThread:
        putEvent(_fsm.evtBtnPlay)


# 音频更新完成处理
def actUpdateDone():
    global _fsm
    logging.debug('mp3FSM.actUpdateDone().')
    if mp3.haveRadio():
        putEvent(_fsm.evtRadio)     # 如果更新完成后，有广播文件，则发送广播事件


# 广播播放完成，发送释放事件
def actRadioDone():
    global _fsm
    logging.debug('mp3FSM.actRadioDone().')
    putEvent(_fsm.evtRelease)


# 政策播放完成，发送释放事件
def actPolicyDone():
    global _fsm
    logging.debug('mp3FSM.actPolicyDone().')
    putEvent(_fsm.evtRelease)


# 后台下载音频列表
#   如果更新失败，则间隔 60s 后重新下载
def updateThread(callback):
    global _fsm, _updateThread

    logging.debug('mp3FSM.updateThread().')
    while not _fsmFini:
        if mp3.update():
            putEvent(_fsm.evtInitOk)
            break;
        for i in range(0, 60):
            time.sleep(1)
            if _fsmFini:
                break;
    _updateThread = None
    if callback:
        callback()
    logging.debug('mp3FSM.updateThread() fini.')


# 后台播放广播
def radioThread(callback):
    global _fsm, _radioThread

    logging.debug('mp3FSM.radioThread().')
    mp3.playRadio()   # 播放广播
    putEvent(_fsm.evtRelease)
    _radioThread = None
    if callback:
        callback()
    logging.debug('mp3FSM.radioThread() fini.')


# 后台播放政策
def policyThread(callback):
    global _fsm, _policyThread

    logging.debug('mp3FSM.policyThread().')
    mp3.playPolicy()  # 播放政策
    putEvent(_fsm.evtRelease)
    _policyThread = None
    if callback:
        callback()
    logging.debug('mp3FSM.policyThread() fini.')


class mp3Fsm(object):
    # 进入初始状态
    def entryInit(self):
        global _hostName, _portNumber, _token, _updateThread

        logging.debug('mp3FSM.entryInit().')
        mp3.init(_hostName, _portNumber, _token)
        if not _updateThread:
            # 启动后台下载音频播放列表
            _updateThread = threading.Thread(target = updateThread, args = [None, ])
            _updateThread.start()
            time.sleep(0.5)

    # 退出初始状态
    def exitInit(self):
        logging.debug('mp3FSM.exitInit().')

    # 进入空闲状态
    def entryIdle(self):
        logging.debug('mp3FSM.entryIdle().')
        mp3.stopPolicy()    # 停止播放政策

    # 退出空闲状态
    def exitIdle(self):
        logging.debug('mp3FSM.exitIdle().')

    # 进入更新状态
    def entryUpdate(self):
        global _updateThread

        logging.debug('mp3FSM.entryUpdate().')
        if not _updateThread:
            # 启动后台更新音频
            _updateThread = threading.Thread(target = updateThread, args = [actUpdateDone, ])
            _updateThread.start()
            time.sleep(0.5)

    # 退出更新状态
    def exitUpdate(self):
        logging.debug('mp3FSM.exit().')

    # 进入政策播放状态
    def entryPolicy(self):
        global _policyThread

        logging.debug('mp3FSM.entryPolicy().')
        if not _policyThread:
            # 启动后台播放政策
            _policyThread = threading.Thread(target = policyThread, args = [actPolicyDone, ])
            _policyThread.start()
            time.sleep(0.5)

    # 退出政策播放状态
    def exitPolicy(self):
        logging.debug('mp3FSM.exitPolicy().')

    # 进入广播播放状态
    def entryRadio(self):
        global _policyThread, _radioThread

        logging.debug('mp3FSM.entryRadio().')
        if _policyThread:
            mp3.stopPolicy()    # 暂停播放政策
            while _policyThread:
                time.sleep(1)   # 等待线程结束

        if not _radioThread:
            # 启动后台播放广播
            _radioThread = threading.Thread(target = radioThread, args = [actRadioDone, ])
            _radioThread.start()
            time.sleep(0.5)

    # 退出广播播放状态
    def exitRadio(self):
        logging.debug('mp3FSM.exitRadio().')
        if _radioThread:
            mp3.stopRadio()     # 停止播放广播
            while _radioThread:
                time.sleep(1)   # 等待线程结束


# 向音频状态机事件队列中放事件
def putEvent(event):
    global _eventQueue, _eventList

    logging.debug('mp3FSM.putEvent().')
    if _eventQueue:
        if event not in _eventList and not _eventQueue.full():
            _eventList.append(event)
            _eventQueue.put(event)
            return True
    return False


# 从音频状态机事件队列中取事件
def getEvent():
    global _eventQueue, _eventList

    logging.debug('mp3FSM.getEvent().')
    if _eventQueue:
        if not _eventQueue.empty():
            event = _eventQueue.get()
            _eventQueue.task_done()
            if event in _eventList:
                _eventList.remove(event)
            return event
    return None


# 音频状态机后台线程
def fsmThread():
    global _fsmFini, _fsmThread, _fsm

    logging.debug('mp3FSM.fsmThread().')

    button.init()
    button.setPlayCallback(actBtnPlay)

    _fsmFini = False
    _fsm.to_stateInit()
    while not _fsmFini:
        time.sleep(1)
        event = getEvent()
        if event:
            event()
            logging.debug('mp3FSM: state - %s' %_fsm.state)
    button.setPlayCallback(None)
    _fsmThread = None
    logging.debug('mp3FSM.fsmThread() fini.')


# 初始化音频状态机
def init(hostName, portNumber, token):
    global _hostName, _portNumber, _token
    global _fsm, _machine, _states
    global _eventQueue, _eventList
    global _fsmThread

    logging.debug('mp3FSM.init(%s, %d, %s).' %(hostName, portNumber, token))
    if not _fsm:
        _hostName = hostName
        _portNumber = portNumber
        _token = token
        _fsm = mp3Fsm()
        _machine = Machine(_fsm, states = _states, transitions = _transitions, initial = 'stateInit', ignore_invalid_triggers = True)
        _eventQueue = Queue.Queue(5)
        del _eventList[:]

        if not _fsmThread:
            _fsmThread = threading.Thread(target = fsmThread)
            _fsmThread.start()


# 终止音频状态机
def fini():
    global _fsmFini, _fsmThread, _radioThread, _policyThread

    logging.debug('mp3FSM.fini().')
    if _radioThread:
        mp3.stopRadio()
    if _policyThread:
        mp3.stopPolicy()
    if _fsmThread:
        _fsmFini = True

    while _fsmThread or _radioThread or _policyThread:
        time.sleep(1)


###############################################################################
# 测试程序
if __name__ == '__main__':
