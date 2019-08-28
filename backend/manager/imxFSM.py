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

from manager.buttonAPI import buttonAPI, gButtonAPI
from manager.serverAPI import serverAPI, gServerAPI
from manager.imxAPI import imxAPI, gImxAPI
from manager.mp3FSM import mp3FSM, gMp3FSM

from utility import setLogging

__all__ = [
        'imxFSM',
        'gImxFSM',
        ]

# 呼叫顺序：村医 -> 公共卫生医师 -> 护士 -> 全科医生 -> 在线服务员
ROLE_VD     = 14    # 乡村医生 - Village Doctor
ROLE_PHD    = 3     # 公共卫生医生 - Public Health Doctor
ROLE_NURSE  = 2     # 护士
ROLE_GP     = 1     # 全科医生 - General Practitioner
ROLE_SERVER = 15    # 在线服务员

# 局部变量


# 视频状态机类
class imxFSM(object):
    # 初始化
    def __init__(self, server, port, personId):
        global gImxFSM, gButtonAPI
        gImxFSM = self

        self._server = server
        self._port = port
        self._personId = personId
        self._doctorId = None
        self._orderList = [ ROLE_VD, ROLE_PHD, ROLE_NURSE, ROLE_GP, ROLE_SERVER ]

        self._autoAccept = False
        self._callCancel = False

        self._callThread = None
        self._loginThread = None

        self._states = [
            State(name = 'stateOffline',    on_enter = 'actLogin',                          ignore_invalid_triggers = True),
            State(name = 'stateIdle',       on_enter = 'entryIdle', on_exit = 'exitIdle',   ignore_invalid_triggers = True),
            State(name = 'stateCall',       on_enter = 'actCall',                           ignore_invalid_triggers = True),
            State(name = 'stateWaitAccept', on_enter = 'actWaitCall',                       ignore_invalid_triggers = True),
            State(name = 'stateIncoming',   on_enter = 'actAccept',                         ignore_invalid_triggers = True),
            State(name = 'stateEstablished',                                                ignore_invalid_triggers = True),
        ]
        self._transitions = [
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

        self._machine = Machine(self, states = self._states, transitions = self._transitions, ignore_invalid_triggers = True)
        self._eventQueue = Queue.Queue(5)
        self._eventList = []
        self._finiEvent = threading.Event()
        self._fsmThread = threading.Thread(target = self.fsmThread)
        self._fsmThread.start()

    # 终止视频状态机
    def fini(self):
        logging.debug('imxFSM.fini().')
        self._finiEvent.set()
        while self._fsmThread:
            time.sleep(0.5)
        del self._eventList[:]
        self._eventQueue = None

    # 向视频状态机事件队列发送事件
    def putEvent(self, event):
        if self._eventQueue:
            if event not in self._eventList and not self._eventQueue.full():
                logging.debug('imxFSM.putEvent().')
                self._eventList.append(event)
                self._eventQueue.put(event)
                return True
        return False

    # 从视频状态机事件队列提取事件
    def getEvent(self):
        if self._eventQueue:
            if not self._eventQueue.empty():
                logging.debug('imxFSM.getEvent().')
                event = self._eventQueue.get()
                self._eventQueue.task_done()
                if event in self._eventList:
                    self._eventList.remove(event)
                return event
        return None

    # 后台登录线程
    #   如果登录失败，30s 后再次登录
    def loginThread(self, event):
        logging.debug('imxFSM.loginThread().')
        try:
            while True:
                if self._imxAPI.login():
                    raise Exception('login')
                self._finiEvent.wait(30)
                if self._finiEvent.isSet():
                    raise Exception('fini')
        except Exception, e:
            if e.message == 'login' and event:
                # TODO:
                #   液晶显示图标
                #   音频播放通知
                self.putEvent(event)
        finally:
            self._loginThread = None
            logging.debug('imxFSM.loginThread() fini.')

    # 对在线医生列表进行优先级排序
    def sortDoctorList(self, doctorList):
        logging.debug('imxFSM.sortDoctor().')
        sortList = []
        for order in self._orderList:
            for doctor in doctorList:
                if doctor['onlineSts'] == 'idle' and str(order) in doctor['role'] and doctor not in sortList:
                    sortList.append[doctor]
        return sortList

    # 后台呼叫线程
    #   依次根据在线医生的优先级进行呼叫
    def callThread(self, doctorList, state, evtOk, evtFail):
        logging.debug('imxFSM.callThread().')
        try:
            self._callCancel, doctorList = False, self.sortDoctorList(doctorList)
            for doctor in doctorList:   # 遍历呼叫所有的医生
                if not doctor['id']:
                    continue
                doctorId = doctor['id']
                self._imxAPI.call(doctorId)
                for wait in range(0, 2 * 30):
                    if self._imxAPI.accepted():
                        raise Exception('accepted') # 接听呼叫
                    if self._callCancel:
                        raise Exception('abort')    # 居民放弃呼叫
                    if self._finiEvent.isSet():
                        raise Exception('fini')     # 退出状态机
                    time.sleep(0.5)
                self._imxAPI.hangup()
                time.sleep(1)
            raise Exception('no answer')
        except Exception as e:
            if e == 'accepted':
                logging.debug('call success: doctorId - %s.' %doctorId)
                if (state == None or self.state == state) and evtOk:
                    self.putEvent(evtOk)
            else:
                self._imxAPI.hangup()
                logging.debug('call failed: reason - %s.' %e)
                if (state == None or self.state == state) and evtFail:
                    self.putEvent(evtFail)
        finally:
            self._callThread = None
            logging.debug('imxFSM.callThread() fini.')

    # 登录动作
    def actLogin(self):
        logging.debug('imxFSM.actLogin().')
        if not self._loginThread:
            self._loginThread = threading.Thread(target = self.loginThread, args = [self.evtLoginOk, ])
            self._loginThread.start()

    # 进入空闲状态动作
    def entryIdle(self):
        global gMp3FSM
        logging.debug('imxFSM.entryIdle().')
        if gMp3FSM:
            gMp3FSM.putEvent(gMp3FSM.evtImxOff)

    # 退出空闲状态动作
    def exitIdle(self):
        global gMp3FSM
        logging.debug('imxFSM.exitIdle().')
        if gMp3FSM:
            gMp3FSM.putEvent(gMp3FSM.evtImxOn)

    # 登出
    def actLogout(self):
        logging.debug('imxFSM.actLogout().')
        self._imxAPI.logout()

    # 呼叫
    def actCall(self):
        global gServerAPI
        logging.debug('imxFSM.actCall().')
        ret, doctorList = gServerAPI.getDoctorList(self._personId)
        if ret:
            if not self._callThread:
                # 启动后台呼叫
                self._callThread = threading.Thread(target = self.callThread, args = [doctorList, self.evtAccept, self.evtRelease, ])
                self._callThread.start()
        else:
            # 获取医生列表失败
            self.putEvent(self.evtRelease)

    # 等待接听
    def actWaitCall(self):
        logging.debug('imxFSM.actWaitCall().')
        if self._autoAccept:
            self.putEvent(self.evtBtnCall)  # 自动接入

    # 接听
    def actAccept(self):
        logging.debug('imxFSM.actAccept().')
        self._imxAPI.accept()

    # 挂断
    def actHangup(self):
        logging.debug('imxFSM.actHangup().')
        self._callCancel = True
        self._imxAPI.hangup()

    # 拒接
    def actDecline(self):
        logging.debug('imxFSM.actDecline().')
        self._imxAPI.Decline()

    # 呼叫按键回调函数
    def cbButtonCall(self):
        logging.debug('imxFSM.cbButtonCall().')
        self.putEvent(self.evtBtnCall)

    # 接入模式按键回调函数
    def cbButtonMute(self):
        logging.debug('imxFSM.cbButtonMute().')
        self._autoAccept = not self._autoAccept
        # TODO:
        #   通知屏幕更改显示状态

    # 视频状态机后台线程
    def fsmThread(self):
        global gButtonAPI
        logging.debug('imxFSM.fsmThread().')
        try:
            if not gButtonAPI:
                gButtonAPI = buttonAPI()
            gButtonAPI.setCallCallback(self.cbButtonCall)
            gButtonAPI.setCallCallback(self.cbButtonMute)

            self._imxAPI = imxAPI(server = self._server, port = self._port, personId = self._personId)
            self._finiEvent.clear()
            while True:
                self._finiEvent.wait(0.5)
                if self._finiEvent.isSet():
                    raise Exception('fini')
                event = self.getEvent()
                if event:
                    event()
                    logging.debug('imxFSM: state - %s' %self.state)
        finally:
            self._fsmThread = None
            self._imxAPI.logout()
            self._imxAPI.fini()
            logging.debug('imxFSM.fsmThread(). fini')


################################################################################
# 测试程序
if __name__ == '__main__':
    global gServerAPI
    try:
        hostName, portNumber, robotId = 'https://ttyoa.com', '8098', 'b827eb319c88'
        if not gServerAPI:
            gServerAPI = serverAPI(hostName, portNumber, robotId)
        ret, _ = gServerAPI.login()
        if ret:
            ret, vsvrIp, vsvrPort, personList = gServerAPI.getConfig()
            print(vsvrIp, vsvrPort, personList)
            if ret and len(personList) > 0:
                personId = personList[0]['personId']
                gImxFSM = imxFSM(server = vsvrIp, port = vsvrPort, personId = personId)
                while True:
                    time.sleep(1)
    except KeyboardInterrupt:
        if gImxFSM:
            gImxFSM.fini()
        sys.exit(0)
