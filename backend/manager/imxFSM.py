#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import Queue
import logging
import threading
import traceback
if __name__ == '__main__':
    import sys
    sys.path.append('..')
    from manager.serverAPI import serverAPI
    from manager.buttonAPI import buttonAPI
from transitions import Machine, State
from manager.imxAPI import imxAPI
from utility import setLogging


__all__ = [
        'imxFSM',
        ]

# 呼叫顺序：村医 -> 公共卫生医师 -> 护士 -> 全科医生 -> 在线服务员
ROLE_VD     = 14    # 乡村医生 - Village Doctor
ROLE_PHD    = 3     # 公共卫生医生 - Public Health Doctor
ROLE_NURSE  = 2     # 护士
ROLE_GP     = 1     # 全科医生 - General Practitioner
ROLE_SERVER = 15    # 在线服务员


# 视频状态机类
class imxFSM(object):
    # 初始化
    def __init__(self, server, port, personId, getDoctorList):
        logging.debug('imxFSM.__init__(%s, %s, %s)' %(server, port, personId))
        self._server = server
        self._port = port
        self._personId = personId
        self._getDoctorList = getDoctorList
        self._doctor = None
        self._doctorList = []
        self._orderList = [ ROLE_VD, ROLE_PHD, ROLE_NURSE, ROLE_GP, ROLE_SERVER ]
        self._autoMode = False

        self._cbExitIdle = None
        self._cbEntryIdle = None
        self._cbCallSound = None

        self._imxAPI = imxAPI(server = self._server, port = self._port, personId = self._personId)
        self._imxAPI.setCallEventUnknown(self.cbCallEventUnknown)
        self._imxAPI.setCallEventCalling(self.cbCallEventCalling)
        self._imxAPI.setCallEventIncoming(self.cbCallEventIncoming)
        self._imxAPI.setCallEventProceeding(self.cbCallEventProceeding)
        self._imxAPI.setCallEventAccept(self.cbCallEventAccept)
        self._imxAPI.setCallEventDecline(self.cbCallEventDecline)
        self._imxAPI.setCallEventBusy(self.cbCallEventBusy)
        self._imxAPI.setCallEventUnreachable(self.cbCallEventUnreachable)
        self._imxAPI.setCallEventOffline(self.cbCallEventOffline)
        self._imxAPI.setCallEventHangup(self.cbCallEventHangup)
        self._imxAPI.setCallEventRelease(self.cbCallEventRelease)
        self._imxAPI.setCallEventTimeout(self.cbCallEventTimeout)
        self._imxAPI.setCallEventSomeerror(self.cbCallEventSomeerror)

        self._timerThread = None
        self._timerFiniEvent = threading.Event()
        self._timerDoneEvent = threading.Event()

        self._states = [
            State(name = 'stateInit',       on_enter = 'actInit',                           ignore_invalid_triggers = True),
            State(name = 'stateOffline',    on_enter = 'actLogin',                          ignore_invalid_triggers = True),
            State(name = 'stateIdle',       on_enter = 'entryIdle', on_exit = 'exitIdle',   ignore_invalid_triggers = True),
            State(name = 'stateCall',       on_enter = 'actCall',                           ignore_invalid_triggers = True),
            State(name = 'stateWaitAccept', on_enter = 'actWaitCall',                       ignore_invalid_triggers = True),
            State(name = 'stateIncoming',   on_enter = 'actAccept',                         ignore_invalid_triggers = True),
            State(name = 'stateEstablished',on_enter = 'entryEstablished',                  ignore_invalid_triggers = True),
        ]
        self._transitions = [
            # 初始状态
            {
                'trigger':  'evtInit',
                'source':   'stateInit',
                'dest':     'stateInit',
            },
            {
                'trigger':  'evtInitOk',
                'source':   'stateInit',
                'dest':     'stateOffline',
            },
            # 任意状态 -------> 离线状态
            {
                'trigger':  'evtOffline',
                'source':   '*',
                'dest':     'stateOffline',
                'before':   'actLogout'
            },
            # 离线状态 ------->
            {
                'trigger':  'evtLogin',
                'source':   'stateOffline',
                'dest':     'stateOffline'
            },
            {
                'trigger':  'evtLoginOk',
                'source':   'stateOffline',
                'dest':     'stateIdle'
            },
            # 空闲状态 ------->
            {
                'trigger':  'evtBtnCall',
                'source':   'stateIdle',
                'dest':     'stateCall',
                'before':   'actCallInit'
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
            {
                'trigger':  'evtNoAnswer',
                'source':   'stateCall',
                'dest':     'stateIdle'
            },
            {
                'trigger':  'evtRelease',
                'source':   'stateCall',
                'dest':     'stateCall'
            },
            # 等待接听 ------->
            {
                'trigger':  'evtBtnCall',
                'source':   'stateWaitAccept',
                'dest':     'stateIncoming'
            },
            {
                'trigger':  'evtRelease',
                'source':   'stateWaitAccept',
                'dest':     'stateIdle'
            },
            # 正在呼入 ------->
            {
                'trigger':  'evtAccept',
                'source':   'stateIncoming',
                'dest':     'stateEstablished'
            },
            {
                'trigger':  'evtRelease',
                'source':   'stateIncoming',
                'dest':     'stateIdle'
            },
            # 建立状态 ------->
            {
                'trigger':  'evtBtnCall',
                'source':   'stateEstablished',
                'dest':     'stateIdle',
                'before':   'actHangup'
            },
            {
                'trigger':  'evtRelease',
                'source':   'stateEstablished',
                'dest':     'stateIdle',
            }
        ]

        self._machine = Machine(self, states = self._states, transitions = self._transitions, ignore_invalid_triggers = True)
        self._eventQueue = Queue.Queue(5)
        self._eventList = []
        self._fsmDoneEvent = threading.Event()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    # 终止视频状态机
    def fini(self):
        logging.debug('imxFSM.fini().')
        if self._fsmThread:
            self.putEvent('fini', None)
            self._fsmDoneEvent.wait()

    # 向视频状态机事件队列发送事件
    def putEvent(self, desc, event):
        if self._eventQueue:
            v = [desc, event]
            if v not in self._eventList and not self._eventQueue.full():
                logging.debug('imxFSM.putEvent(%s).' %desc)
                self._eventList.append(v)
                self._eventQueue.put(v)
                return True
        return False

    # 从视频状态机事件队列提取事件
    def getEvent(self):
        if self._eventQueue:
            v = self._eventQueue.get(block = True)
            self._eventQueue.task_done()
            logging.debug('imxFSM.getEvent(%s).' %v[0])
            if v in self._eventList:
                self._eventList.remove(v)
            return True, v[0], v[1]
        return False, None, None

    # 定时器线程
    def timerThread(self, timeout, desc, event):
        logging.debug('imxFSM.timerThread(%d, %s).' %(timeout, desc))
        self._timerDoneEvent.clear()
        self._timerFiniEvent.clear()
        self._timerFiniEvent.wait(timeout)
        if not self._timerFiniEvent.isSet() and event:
            self.putEvent(desc, event)
        self._timerThread = None
        self._timerDoneEvent.set()
        logging.debug('imxFSM.timerThread(%d, %s) fini.' %(timeout, desc))

    # 启动定时器
    def timerInit(self, timeout, desc, event):
        logging.debug('imxFSM.timerInit(%d, %s).' %(timeout, desc))
        if self._timerThread:
            self.timerFini()
        self._timerThread = threading.Thread(target = self.timerThread, args = [timeout, desc, event, ])
        self._timerThread.start()

    # 停止定时器
    def timerFini(self):
        logging.debug('imxFSM.timerFini().')
        if self._timerThread:
            self._timerFiniEvent.set()
            self._timerDoneEvent.wait()

    # 对在线医生列表进行优先级排序
    def sortDoctorList(self, doctorList):
        logging.debug('imxFSM.sortDoctor().')
        sortList = []
        for order in self._orderList:
            for doctor in doctorList:
                if doctor['onlineSts'] == 'idle' and str(order) in doctor['role'] and doctor not in sortList:
                    sortList.append(doctor)
        return sortList

    # 初始化动作
    def actInit(self):
        logging.debug('imxFSM.actInit().')
        if self._imxAPI.init():
            self.putEvent('evtInitOk', self.evtInitOk)
        else:
            self.timerInit(timeout = 10, desc = 'evtInit', event = self.evtInit)

    # 登录动作
    def actLogin(self):
        logging.debug('imxFSM.actLogin().')
        if self._imxAPI.login():
            # TODO:
            #   液晶显示图标
            #   音频播放通知
            self.putEvent('evtLoginOk', self.evtLoginOk)
        else:
            self.timerInit(timeout = 30, desc = 'evtLogin', event = self.evtLogin)

    # 设置呼叫音效回调函数
    def setCallSoundCallback(self, cb):
        self._cbCallSound, cb = cb, self._cbCallSound
        return cb

    # 设置进入空闲状态动作回调函数
    def setEntryIdleCallback(self, cb):
        self._cbEntryIdle, cb = cb, self._cbEntryIdle
        return cb

    # 进入空闲状态动作
    def entryIdle(self):
        logging.debug('imxFSM.entryIdle().')
        if self._cbEntryIdle:
            self._cbEntryIdle()

    # 设置退出空闲状态动作回调函数
    def setExitIdleCallback(self, cb):
        self._cbExitIdle, cb = cb, self._cbExitIdle
        return cb

    # 退出空闲状态动作
    def exitIdle(self):
        logging.debug('imxFSM.exitIdle().')
        if self._cbExitIdle:
            self._cbExitIdle()

    # 进入通话状态
    def entryEstablished(self):
        logging.debug('imxFSM.entryEstablished().')

    # 登出
    def actLogout(self):
        logging.debug('imxFSM.actLogout().')
        self._imxAPI.logout()

    # 呼叫初始化
    def actCallInit(self):
        logging.debug('imxFSM.actCallInit().')
        self._doctor = None
        del self._doctorList[:]
        ret, doctorList = self._getDoctorList(self._personId)
        if ret:
            self._doctorList = self.sortDoctorList(doctorList)

    # 呼叫
    def actCall(self):
        logging.debug('imxFSM.actCall().')
        # 依次呼叫下一位医生
        try:
            if len(self._doctorList) == 0:
                self._doctor = None
            elif not self._doctor:
                self._doctor = self._doctorList[0]
            else:
                i = self._doctorList.index(self._doctor) + 1
                self._doctor = self._doctorList[i] if i < len(self._doctorList) else None
        except:
            self._doctor = None
            traceback.print_exc()
        finally:
            if self._doctor:
                self._imxAPI.call(str(self._doctor['id']))
            else:
                self.putEvent('evtNoAnswer', self.evtNoAnswer)

    # 等待接听
    def actWaitCall(self):
        logging.debug('imxFSM.actWaitCall().')
        if self._autoMode:
            self.putEvent('evtBtnCall', self.evtBtnCall)  # 自动接入

    # 接听
    def actAccept(self):
        logging.debug('imxFSM.actAccept().')
        self._imxAPI.accept()

    # 挂断
    def actHangup(self):
        logging.debug('imxFSM.actHangup().')
        self._imxAPI.hangup()

    # 拒接
    def actDecline(self):
        logging.debug('imxFSM.actDecline().')
        self._imxAPI.Decline()

    # 呼叫按键回调函数
    def cbButtonCall(self):
        logging.debug('imxFSM.cbButtonCall().')
        self.putEvent('evtBtnCall', self.evtBtnCall)

    # 接入模式按键回调函数
    def cbButtonMute(self):
        logging.debug('imxFSM.cbButtonMute().')
        self._autoMode = not self._autoMode
        # TODO:
        #   通知屏幕更改显示状态

    # 关闭音效
    def callSoundFini(self, desc, event):
        logging.debug('imxFSM.callSoundFini().')
        if self._cbCallSound:
            self._cbCallSound(False)
        if event:
            self.putEvent(desc, event)

    # 开启音效
    def callSoundInit(self, desc, event):
        logging.debug('imxFSM.callSoundInit().')
        if self._cbCallSound:
            self._cbCallSound(True)
        if event:
            self.putEvent(desc, event)

    # 呼叫事件回调函数 - 未知错误
    def cbCallEventUnknown(self):
        logging.debug('imxFSM.cbCallEventUnknown().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 正在外呼
    def cbCallEventCalling(self):
        logging.debug('imxFSM.cbCallEventCalling().')
        self.callSoundInit(None, None)                      # 启动 <嘟嘟> 音效

    # 呼叫事件回调函数 - 正在呼入
    def cbCallEventIncoming(self):
        logging.debug('imxFSM.cbCallEventIncoming().')
        self.callSoundInit(None, None)                      # 启动 <嘟嘟> 音效

    # 呼叫事件回调函数 - 正在处理
    def cbCallEventProceeding(self):
        logging.debug('imxFSM.cbCallEventProceeding().')

    # 呼叫事件回调函数 - 接听
    def cbCallEventAccept(self):
        logging.debug('imxFSM.cbCallEventAccept().')
        self.callSoundFini('evtAccept', self.evtAccept)     # 关闭 <嘟嘟> 音效
        self._imxAPI.activeMedia()

    # 呼叫事件回调函数 - 拒接
    def cbCallEventDecline(self):
        logging.debug('imxFSM.cbCallEventDecline().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 远端忙
    def cbCallEventBusy(self):
        logging.debug('imxFSM.cbCallEventBusy().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 不可达
    def cbCallEventUnreachable(self):
        logging.debug('imxFSM.cbCallEventUnreachable().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 离线
    def cbCallEventOffline(self):
        logging.debug('imxFSM.cbCallEventOffline().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 对方挂断
    def cbCallEventHangup(self):
        logging.debug('imxFSM.cbCallEventHangup().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 释放
    def cbCallEventRelease(self):
        logging.debug('imxFSM.cbCallEventRelease().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 超时无人接听
    def cbCallEventTimeout(self):
        logging.debug('imxFSM.cbCallEventTimeout().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 呼叫事件回调函数 - 某些错误
    def cbCallEventSomeerror(self):
        logging.debug('imxFSM.cbCallEventSomeerror().')
        self.callSoundFini('evtRelease', self.evtRelease)   # 关闭 <嘟嘟> 音效

    # 视频状态机后台线程
    def fsmThread(self):
        logging.debug('imxFSM.fsmThread().')
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
                        logging.debug('imxFSM: state - %s' %self.state)
        finally:
            self.timerFini()
            self._eventQueue.queue.clear()
            self._eventQueue = None
            del self._eventList[:]
            self._fsmThread = None
            self._fsmDoneEvent.set()
            self._imxAPI.logout()
            self._imxAPI.fini()
            logging.debug('imxFSM.fsmThread(). fini')


################################################################################
# 测试程序
if __name__ == '__main__':
    try:
        hostName, portNumber, robotId = 'https://ttyoa.com', '8098', 'b827eb319c88'
        server = serverAPI(hostName, portNumber, robotId)
        ret, _ = server.login()
        if ret:
            ret, vsvrIp, vsvrPort, personList = server.getConfig()
            if ret and len(personList) > 0:
                personId = personList[0]['personId']
                imx = imxFSM(server = vsvrIp, port = vsvrPort, personId = personId, getDoctorList = server.getDoctorList)
                button = buttonAPI()
                button.setCallCallback(imx.cbButtonCall)
                button.setMuteCallback(imx.cbButtonMute)
                while True:
                    time.sleep(1)
    except KeyboardInterrupt:
        imx.fini()
        sys.exit(0)
