#!/usr/bin/python
# -*- coding: utf8 -*-


import time
import Queue
import platform
import logging
import threading
from transitions import Machine, State

if __name__ == '__main__':
    import sys
    sys.path.append('..')

from utility import setLogging
import manager.mp3API as mp3
import manager.serverAPI as server
if platform.system().lower() == 'windows':
    import manager.buttonSIM as button
elif platform.system().lower() == 'linux':
    import manager.buttonAPI as button
else:
    raise NotImplementedError

__all__ = [
        'init',
        'fini',
        'update',
        'putEvent',
        'getEvent'
        ]


# 局部变量
_volume_min     = 0.00
_volume_max     = 1.00
_volume_inv     = 0.05
_radioThread    = None
_policyThread   = None
_updateThread   = None
_radioCallback  = None
_policyCallback = None

_eventQueue     = None
_eventList      = []

_fsmThread      = None
_fsmFini        = False

_fsm            = None
_machine        = None
_states         = [
        State(name = 'stateInit',    on_enter = 'actUpdate',     ignore_invalid_triggers = True),
        State(name = 'stateIdle',                                ignore_invalid_triggers = True),
        State(name = 'statePolicy',  on_enter = 'actPlayPolicy', ignore_invalid_triggers = True),
        State(name = 'stateRadio',   on_enter = 'actPlayRadio',  ignore_invalid_triggers = True),
        State(name = 'stateRadioEx', on_enter = 'actPlayRadio',  ignore_invalid_triggers = True),
        ]
_transitions    = [
        # 初始状态 ------->
        {
            'trigger':  'evtInitOk',
            'source':   'stateInit',
            'dest':     'stateIdle',
            'before':   'actUpdateDone'
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
        # 政策播放状态 --->
        {
            'trigger':  'evtRelease',
            'source':   'statePolicy',
            'dest':     'stateIdle'
        },
        {
            'trigger':  'evtBtnPlay',
            'source':   'statePolicy',
            'dest':     'stateIdle',
            'before':   'actStopPolicy'
        },
        {
            'trigger':  'evtRadio',
            'source':   'statePolicy',
            'dest':     'stateRadioEx',
            'before':   'actHaltPolicy'
        },
        # 广播播放状态
        {
            'trigger':  'evtBtnPlay',
            'source':   'stateRadio',
            'dest':     'stateIdle',
            'before':   'actStopRadio',
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
            'dest':     'statePolicy',
            'before':   'actStopRadio'
        },
        {
            'trigger':  'evtRelease',
            'source':   'stateRadioEx',
            'dest':     'statePolicy'
        },
        ]


# 播放按键动作
def cbBtnPlay():
    global _fsm, _fsmThread
    logging.debug('mp3FSM.cbBtnPlay().')
    if _fsmThread:
        putEvent(_fsm.evtBtnPlay)


# 音量增加按键动作
def cbBtnIncVolume():
    global _volume_inv, _volume_min, _volume_max
    logging.debug('mp3FSM.cbBtnIncVolume().')
    volume = mp3.getVolume()
    volume = (volume + _volume_inv) if (volume + _volume_inv) < _volume_max else _volume_max
    mp3.setVolume(volume)


# 音量减少按键动作
def cbBtnDecVolume():
    global _volume_inv, _volume_min, _volume_max
    logging.debug('mp3FSM.cbBtnDecVolume().')
    volume = mp3.getVolume()
    volume = (volume - _volume_inv) if (volume - _volume_inv) > _volume_min else _volume_min
    mp3.setVolume(volume)


# 广播模拟按键动作
def cbBtnRadio():
    update(cbUpdateDone)


# 音频播放结束
def cbPlayDone():
    global _fsm
    logging.debug('mp3FSM.cbPlayDone().')
    putEvent(_fsm.evtRelease)


# 后台下载音频列表
#   如果更新失败，则间隔 60s 后重新下载
def updateThread(callback):
    global _fsm, _updateThread
    logging.debug('mp3FSM.updateThread().')
    while not _fsmFini:
        if mp3.update():
            if _fsm.state == 'stateInit':
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
def radioThread():
    global _fsm, _radioThread, _radioCallback
    logging.debug('mp3FSM.radioThread().')
    mp3.playRadio()   # 播放广播
    _radioThread = None
    if _radioCallback:
        _radioCallback()
    logging.debug('mp3FSM.radioThread() fini.')


# 后台播放政策
def policyThread():
    global _fsm, _policyThread, _policyCallback
    logging.debug('mp3FSM.policyThread().')
    mp3.playPolicy()  # 播放政策
    _policyThread = None
    if _policyCallback:
        _policyCallback()
    logging.debug('mp3FSM.policyThread() fini.')


class mp3Fsm(object):
    # 更新音频列表
    def actUpdate(self):
        global _hostName, _portNumber, _token
        logging.debug('mp3FSM.actUpdate().')
        mp3.init(_hostName, _portNumber, _token)
        update(cbInitOk)

    # 更新完成处理
    def actUpdateDone(self):
        logging.debug('mp3FSM.actUpdateDone().')
        cbUpdateDone()

    # 启动播放广播
    def actPlayRadio(self):
        global _radioThread, _radioCallback
        logging.debug('mp3FSM.actPlayRadio().')
        if not _radioThread:
            _radioCallback = cbPlayDone
            _radioThread   = threading.Thread(target = radioThread)
            _radioThread.start()

    # 停止播放广播
    def actStopRadio(self):
        global _radioThread, _radioCallback
        logging.debug('mp3FSM.actStopRadio().')
        if _radioThread:
            _radioCallback = None
            mp3.stopRadio()
            while _radioThread:
                time.sleep(0.5)

    # 启动播放政策
    def actPlayPolicy(self):
        global _policyThread, _policyCallback
        logging.debug('mp3FSM.actPlayPolicy().')
        if not _policyThread:
            _policyCallback = cbPlayDone
            _policyThread   = threading.Thread(target = policyThread)
            _policyThread.start()

    # 停止播放政策
    def actStopPolicy(self):
        global _policyThread, _policyCallback
        logging.debug('mp3FSM.actStopPolicy().')
        if _policyThread:
            _policyCallback = None
            mp3.stopPolicy()
            while _policyThread:
                time.sleep(0.5)

    # 暂停播放政策
    def actHaltPolicy(self):
        global _policyThread, _policyCallback
        logging.debug('mp3FSM.actHaltPolicy().')
        if _policyThread:
            _policyCallback = None
            mp3.haltPolicy()
            while _policyThread:
                time.sleep(0.5)


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
    if _eventQueue:
        if not _eventQueue.empty():
            logging.debug('mp3FSM.getEvent().')
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

    # 初始化按键
    button.init()
    button.setPlayCallback(cbBtnPlay)
    button.setIncVolumeCallback(cbBtnIncVolume)
    button.setDecVolumeCallback(cbBtnDecVolume)
    if platform.system().lower() == 'windows':
        button.setRadioCallback(cbBtnRadio)

    # 启动状态机事件循环
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
    logging.debug('mp3FSM.init(%s, %s, %s).' %(hostName, portNumber, token))
    if not _fsm:
        _hostName = hostName
        _portNumber = portNumber
        _token = token
        _fsm = mp3Fsm()
        _machine = Machine(_fsm, states = _states, transitions = _transitions, ignore_invalid_triggers = True)
        _eventQueue = Queue.Queue(5)
        del _eventList[:]
        if not _fsmThread:
            _fsmThread = threading.Thread(target = fsmThread)
            _fsmThread.start()


# 音频初始化完成回调函数
def cbInitOk():
    global _fsm
    logging.debug('mp3FSM.cbInitOk()')
    putEvent(_fsm.evtInitOk)


# 音频更新完成回调函数
def cbUpdateDone():
    global _fsm
    logging.debug('mp3FSM.cbUpdateDone()')
    if mp3.haveRadio():
        putEvent(_fsm.evtRadio)


# 更新音频文件
def update(callback):
    global _updateThread
    logging.debug('mp3FSM.update().')
    if not _updateThread:
        # 启动后台更新音频文件
        _updateThread = threading.Thread(target = updateThread, args = [callback, ])
        _updateThread.start()


# 终止音频状态机
def fini():
    global _fsm, _fsmFini, _fsmThread
    logging.debug('mp3FSM.fini().')
    if _fsm:
        _fsm.actStopRadio()     # 停止广播播放线程
        _fsm.actStopPolicy()    # 停止政策播放线程
    if _fsmThread:
        _fsmFini = True         # 停止状态机线程
        while _fsmThread:
            time.sleep(0.5)


###############################################################################
# 测试程序
if __name__ == '__main__':
    try:
        hostName    = 'https://ttyoa.com'
        portNumber  = '8098'
        robotId     = 'b827eb319c88'
        server.init(hostName, portNumber, robotId)
        ret, token = server.login()
        if ret:
            init(hostName, portNumber, token)
            while (1):
                time.sleep(1)
    except KeyboardInterrupt:
        fini()
        sys.exit(0)
