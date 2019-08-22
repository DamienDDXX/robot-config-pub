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
from manager import mp3API
if platform.system().lower() == 'windows':
    import manager.buttonSIM as button
elif platform.system().lower() == 'linux':
    import manager.buttonAPI as button
else:
    raise NotImplementedError

__all__ = [
        'init',
        'fini',
        'putEvent',
        'getEvent',
        'updatePlay',
        'pause',
        'resume',
        ]

# 局部变量
_volume_min     = 0.00
_volume_max     = 1.00
_volume_inv     = 0.05
_radioThread    = None
_policyThread   = None
_updateThread   = None

_playSuspend    = False

_eventQueue     = None
_eventList      = []

_fsmThread      = None
_fsmFini        = False

_fsm            = None
_machine        = None
_states         = [
        State(name = 'stateInit',    on_enter = 'actUpdate',     ignore_invalid_triggers = True),
        State(name = 'stateIdle',                                ignore_invalid_triggers = True),
        State(name = 'statePause',                               ignore_invalid_triggers = True),
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
        # 暂停状态 ------->
        {
            'trigger':  'evtResume',
            'source':   'statePause',
            'dest':     'stateIdle',
        },
        #          -------> 暂停状态
        {
            'trigger':  'evtPause',
            'source':   '*',
            'dest':     'statePause',
            'before':   'actPause'
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
    volume = mp3API.getVolume()
    volume = (volume + _volume_inv) if (volume + _volume_inv) < _volume_max else _volume_max
    mp3API.setVolume(volume)


# 音量减少按键动作
def cbBtnDecVolume():
    global _volume_inv, _volume_min, _volume_max
    logging.debug('mp3FSM.cbBtnDecVolume().')
    volume = mp3API.getVolume()
    volume = (volume - _volume_inv) if (volume - _volume_inv) > _volume_min else _volume_min
    mp3API.setVolume(volume)


# 广播模拟按键动作
def cbBtnRadio():
    logging.debug('mp3FSM.cbBtnRadio().')
    update(cbUpdateDone)


# 视频模拟按键动作
def cbBtnImx():
    global _fsm
    logging.debug('mp3FSM current state: %s.' %_fsm.state)


# 音频播放结束
def cbPlayDone():
    global _fsm, _playSuspend
    logging.debug('mp3FSM.cbPlayDone().')
    if not _playSuspend:
        putEvent(_fsm.evtRelease)


# 后台下载音频列表
#   如果更新失败，则间隔 60s 后重新下载
def updateThread(callback):
    from manager import serverFSM
    global _fsm, _updateThread
    logging.debug('mp3FSM.updateThread().')
    try:
        while True:
            if mp3API.update():
                serverFSM.setPlayUpdated()  # 通知服务器音频列表更新完成
                raise Exception('done')
            for i in range(0, 60):
                if _fsmFini:
                    raise Exception('fini')
                time.sleep(1)
    except Exception, e:
        if e.message == 'done' and callback:
            callback()
    finally:
        _updateThread = None
        logging.debug('mp3FSM.updateThread() fini.')


# 后台播放广播
def radioThread(callback):
    global _fsm, _radioThread
    logging.debug('mp3FSM.radioThread().')
    mp3API.playRadio()   # 播放广播
    _radioThread = None
    if callback:
        callback()
    logging.debug('mp3FSM.radioThread() fini.')


# 后台播放政策
def policyThread(callback):
    global _fsm, _policyThread
    logging.debug('mp3FSM.policyThread().')
    mp3API.playPolicy()  # 播放政策
    _policyThread = None
    if callback:
        callback()
    logging.debug('mp3FSM.policyThread() fini.')


# 音频状态机管理类定义
class mp3Fsm(object):
    # 更新音频列表
    def actUpdate(self):
        global _hostName, _portNumber, _token
        logging.debug('mp3FSM.actUpdate().')
        mp3API.init(_hostName, _portNumber, _token)
        update(cbInitOk)

    # 更新完成处理
    def actUpdateDone(self):
        logging.debug('mp3FSM.actUpdateDone().')
        cbUpdateDone()

    # 暂停处理
    def actPause(self):
        logging.debug('mp3FSM.actPause().')
        actStopRadio(self)
        actStopPolicy(self)

    # 启动播放广播
    def actPlayRadio(self):
        global _radioThread, _playSuspend
        logging.debug('mp3FSM.actPlayRadio().')
        if not _radioThread:
            _playSuspend = False
            _radioThread = threading.Thread(target = radioThread, args = [cbPlayDone, ])
            _radioThread.start()
            time.sleep(0.5)

    # 停止播放广播
    def actStopRadio(self):
        global _radioThread, _playSuspend
        logging.debug('mp3FSM.actStopRadio().')
        if _radioThread:
            _playSuspend = True
            mp3API.stopRadio()
            while _radioThread:
                time.sleep(0.5)

    # 启动播放政策
    def actPlayPolicy(self):
        global _policyThread, _playSuspend
        logging.debug('mp3FSM.actPlayPolicy().')
        if not _policyThread:
            _playSuspend  = False
            _policyThread = threading.Thread(target = policyThread, args = [cbPlayDone, ])
            _policyThread.start()

    # 停止播放政策
    def actStopPolicy(self):
        global _policyThread, _playSuspend
        logging.debug('mp3FSM.actStopPolicy().')
        if _policyThread:
            _playSuspend = True
            mp3API.stopPolicy()
            while _policyThread:
                time.sleep(0.5)

    # 暂停播放政策
    def actHaltPolicy(self):
        global _policyThread, _playSuspend
        logging.debug('mp3FSM.actHaltPolicy().')
        if _policyThread:
            _playSuspend = True
            mp3API.haltPolicy()
            while _policyThread:
                time.sleep(0.5)


# 向音频状态机事件队列中放事件
def putEvent(event):
    global _eventQueue, _eventList
    if _eventQueue:
        if event not in _eventList and not _eventQueue.full():
            logging.debug('mp3FSM.putEvent().')
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
        button.setImxCallback(cbBtnImx)

    # 启动状态机事件循环
    try:
        _fsmFini = False
        _fsm.to_stateInit()
        while True:
            if _fsmFini:
                raise Exception('fini')
            time.sleep(0.5)
            event = getEvent()
            if event:
                event()
                logging.debug('mp3FSM: state - %s' %_fsm.state)
    except Exception, e:
        pass
    finally:
        _fsmThread = None
        button.setPlayCallback(None)
        logging.debug('mp3FSM.fsmThread() fini.')


# 初始化音频状态机
def init(hostName, portNumber, token):
    global _hostName, _portNumber, _token
    global _fsm, _machine, _states, _transitions
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
    if mp3API.haveRadio():
        putEvent(_fsm.evtRadio)     # 通知播放广播


# 更新音频文件
def update(callback):
    global _updateThread
    logging.debug('mp3FSM.update().')
    if not _updateThread:
        # 启动后台更新音频文件
        _updateThread = threading.Thread(target = updateThread, args = [callback, ])
        _updateThread.start()


# 更新音频列表
def updatePlay():
    logging.debug('mp3FSM.updatePlay().')
    update(cbUpdateDone)


# 暂停音频状态机
def pause():
    logging.debug('mp3FSM.pause().')
    putEvent(evtPause)


# 恢复音频状态机
def resume():
    logging.debug('mp3FSM.resume().')
    putEvent(evtResume)


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
    import manager.serverAPI
    try:
        hostName    = 'https://ttyoa.com'
        portNumber  = '8098'
        robotId     = 'b827eb319c88'
        manager.serverAPI.init(hostName, portNumber, robotId)
        ret, token = manager.serverAPI.login()
        if ret:
            init(hostName, portNumber, token)
            while (1):
                time.sleep(1)
    except KeyboardInterrupt:
        fini()
        sys.exit(0)
