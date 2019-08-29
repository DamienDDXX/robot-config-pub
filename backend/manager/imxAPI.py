#!/usr/bin/python
# -*- coding: utf8 -*-

from ctypes import *  # NOQA
import logging
import threading

if __name__ == '__main__':
    import sys
    import time
    sys.path.append('..')

from utility import setLogging

__all__ = [
        'imxAPI',
        'gImxAPI',
        ]

IMX_LIBRARY_PATH    = '/usr/lib/libimx.so'

# 定义视频分辨率
video_resolution_t  = c_int
vr_qvga             = video_resolution_t(0) # 240p
vr_vga              = video_resolution_t(1) # 480p
vr_hd               = video_resolution_t(2) # 720p

# 定义系统事件类型
sys_event_t         = c_int
se_connecting       = sys_event_t(0)    # 正在连接
se_connect_fail     = sys_event_t(1)    # 连接失败
se_connected        = sys_event_t(2)    # 已连接
se_disconnected     = sys_event_t(3)    # 断开
se_auto_connecting  = sys_event_t(4)    # 正在重连

# 定义登录事件类型
login_event_t       = c_int
le_idle             = login_event_t(0)  # 空闲/已登出
le_connect_timeout  = login_event_t(1)  # 连接超时
le_timeout          = login_event_t(2)  # 登录超时失败
le_logging          = login_event_t(3)  # 正在尝试登录
le_login            = login_event_t(4)  # 登录成功
le_kickout          = login_event_t(5)  # 被踢出
le_normal_leave     = login_event_t(6)  # 正常登出
le_abnormal_leave   = login_event_t(7)  # 异常登出
le_someerror        = login_event_t(8)  # 发生某些错误
le_reject           = login_event_t(9)  # 被服务器拒绝

# 定义呼叫事件类型
call_event_t        = c_int
ce_unknown          = call_event_t(0)   # 未知
ce_calling          = call_event_t(1)   # 正在外呼
ce_incoming         = call_event_t(2)   # 呼入
ce_proceeding       = call_event_t(3)   # 正在处理中
ce_accept           = call_event_t(4)   # 接听
ce_decline          = call_event_t(5)   # 拒绝
ce_busy             = call_event_t(6)   # 远端忙
ce_unreachable      = call_event_t(7)   # 不可达
ce_offline          = call_event_t(8)   # 离线
ce_hangup           = call_event_t(9)   # 远端挂断
ce_release          = call_event_t(10)  # 释放
ce_timeout          = call_event_t(11)  # 超时无人接听
ce_someerror        = call_event_t(12)  # 某些错误

# 定义当前登录状态
router_state_t      = c_int
rs_idle             = router_state_t(0) #
rs_logging          = router_state_t(1) # 正在登录
rs_online           = router_state_t(2) # 在线
rs_unknown          = router_state_t(-1)# 未知

# 定义当前呼叫状态
call_state_t        = c_int
cs_idle             = call_state_t(0)   # 空闲/已断开
cs_calling          = call_state_t(1)   # 呼出...
cs_incoming         = call_state_t(2)   # 有呼入...
cs_accepting        = call_state_t(3)   # 接听中
cs_established      = call_state_t(4)   # 已建立
cs_releasing        = call_state_t(5)   # 正在尝试释放
cs_unknown          = call_state_t(-1)  # 未知

# 定义日志级别
log_level_t         = c_int
ll_trace            = log_level_t(0)
ll_debug            = log_level_t(1)
ll_warn             = log_level_t(2)
ll_error            = log_level_t(3)
ll_none             = log_level_t(4)

# 定义 ImxStateSt 结构体
class imxStateStruct(Structure):
    # ImxStateSt 结构体的 python 版本
    _fields_ = [
            ( 'nLoss', c_int ),
            ( 'nRTT', c_int ),
            ( 'nSendBitrate',  c_int ),
            ]

# 定义 LoginNotify 结构体
class loginNotifyStruct(Structure):
    # LoginNotify 结构体的 python 版本
    _fields_ = [
            ( 'event', login_event_t )
            ]

# 定义长度为 256 的字节数组
chararray256_t  = c_char * 256

# 定义 CallNotify 结构体
class callNotifyStruct(Structure):
    # CallNotify 结构体的 python 版本
    _fields_ = [
            ( 'eEvent', call_event_t ),
            ( 'szCallID', chararray256_t ),
            ( 'szUserID', chararray256_t ),
            ]

# 定义回调函数类型
sys_event_callback_t    = CFUNCTYPE(None, sys_event_t, c_char_p, c_void_p)
net_state_callback_t    = CFUNCTYPE(None, imxStateStruct, c_void_p)
login_callback_t        = CFUNCTYPE(None, loginNotifyStruct, c_void_p)
call_event_callback_t   = CFUNCTYPE(None, callNotifyStruct, c_void_p)

# 全局变量
gImxAPI = None

# 视频接口类
class imxAPI(object):
    # 初始化
    def __init__(self, server, port, personId):
        logging.debug('imxAPI.__init__(%s, %d, %s)' %(server, port, personId))
        global gImxAPI
        gImxAPI = self

        self._server = server
        self._port = port
        self._personId = personId

        self._callId = ''
        self._remoteId = ''

        self._login = False
        self._loginEvent = threading.Event()
        self._loginEvent.clear()

        self._cbCallEventUnkown = None
        self._cbCallEventCalling = None
        self._cbCallEventIncoming = None
        self._cbCallEventProceeding = None
        self._cbCallEventAccept = None
        self._cbCallEventDecline = None
        self._cbCallEventBusy = None
        self._cbCallEventUnreachable = None
        self._cbCallEventOffline = None
        self._cbCallEventHangup = None
        self._cbCallEventRelease = None
        self._cbCallEventTimeout = None
        self._cbCallEventSomeerror = None

        self._cbSysEvent = sys_event_callback_t(self.cbSysEvent)
        self._cbLogin = login_callback_t(self.cbLogin)
        self._cbCallEvent = call_event_callback_t(self.cbCallEvent)
        self._cbNetState = net_state_callback_t(self.cbNetState)
        self._cdll = cdll.LoadLibrary(IMX_LIBRARY_PATH)
        self._cdll.ImxSetLog(c_bool(False))
        self._cdll.ImxInit(c_char_p(self._server),
                           c_ushort(self._port),
                           c_ushort(0),
                           c_char_p(self._personId),
                           vr_vga,
                           c_bool(False),
                           ll_error,
                           ll_error,
                           self._cbSysEvent,
                           self._cbLogin,
                           self._cbCallEvent,
                           self._cbNetState)

    # 终止视频模块
    def fini(self):
        logging.debug('imxAPI.fini().')
        self._cdll.ImxFini()

    # 设置视频模块日志开关
    def setLog(self, onOff):
        logging.debug('imxAPI.setLog(%s)' %('on' if onOff else 'off'))
        self._cdll.ImxSetLog(c_bool(True if onOff else False))

    # 获取视频模块版本信息
    def version(self):
        majVer = c_int(0)
        subVer = c_int(0)
        extVer = c_int(0)
        build  = c_int(0)
        self._cdll.ImxGetSDKVersion(pointer(majVer), pointer(subVer), pointer(extVer), pointer(build))
        version = str(majVer.value) + '.' + str(subVer.value) + '.' + str(extVer.value) + '.' + str(build.value)
        logging.debug('imxAPI.version(): %s' %(version))
        return version

    # 登录视频模块
    def login(self):
        logging.debug('imxAPI.login().')
        ret = False
        self._loginEvent.clear()
        if self._cdll.ImxLogin(c_char_p(self._personId)) == 0:
            self._loginEvent.wait(30)
            if self._loginEvent.isSet() and self._login:
                ret = True
        logging.debug('imxAPI.login(%s) %s.' %(self._personId, 'success' if ret else 'failed'))
        return ret

    # 登出视频模块
    def logout(self):
        logging.debug('imxAPI.logout().')
        ret = False
        self._loginEvent.clear()
        if self._cdll.ImxLogout() == 0:
            self._loginEvent.wait(30)
            if self._loginEvent.isSet() and not self._login:
                ret = True
        logging.debug('imxAPI.logout(%s) %s.' %(self._personId, 'success' if ret else 'failed'))
        return ret

    # 发起视频呼叫
    def call(self, destId):
        logging.debug('imxAPI.call(%s).' %destId)
        error = self._cdll.ImxCall(c_char_p(destId))
        if error == 0:
            logging.debug('imxAPI.call(%s) success.' %destId)
            return True
        logging.debug('imxAPI.call(%s) failed, error code: %d' %(destId, error))
        return False

    # 接听视频呼叫
    def accept(self):
        logging.debug('imxAPI.accept(%s).' %self._callId)
        error = self._cdll.ImxAccept(c_char_p(self._callId))
        if error == 0:
            logging.debug('imxAPI.accept(%s) success.' %self._callId)
            return True
        logging.debug('imxAPI.accept(%s) failed, error code: %d' %(self._callId, error))
        return False

    # 判断是否接听视频
    def accepted(self):
        return True if self._callValue == ce_accept.value else False

    # 拒接视频呼叫
    def decline(self):
        logging.debug('imxAPI.decline(%s).' %self._callId)
        error = self._cdll.ImxDecline(c_char_p(self._callId))
        if error == 0:
            logging.debug('imxAPI.decline(%s) success.' %self._callId)
            return True
        logging.debug('imxAPI.decline(%s) failed, error code: %d' %(self._callId, error))
        return False

    # 挂掉视频呼叫
    def hangup(self):
        logging.debug('imxAPI.hangup(%s).' %self._callId)
        error = self._cdll.ImxHangup(c_char_p(self._callId))
        if error == 0:
            logging.debug('imxAPI.hangup(%s) success.' %self._callId)
            return True
        logging.debug('imxAPI.hangup(%s) failed, error code: %d' %(self._callId, error))
        return False

    # 解析系统事件类型
    def descriptSysEvent(self, event):
        if event == se_connecting.value:
            return u'正在连接'
        elif event == se_connect_fail.value:
            return u'连接失败'
        elif event == se_connected.value:
            return u'连接成功'
        elif event == se_disconnected.value:
            return u'连接断开'
        elif event == se_auto_connecting.value:
            return u'正在重连'
        else:
            return u'未知的系统事件'

    # 解析登录事件类型
    def descriptLoginEvent(self, event):
        if event == le_idle.value:
            return u'空闲/已登出'
        elif event == le_connect_timeout.value:
            return u'连接超时'
        elif event == le_timeout.value:
            return u'登录超时失败'
        elif event == le_logging.value:
            return u'正在尝试登录'
        elif event == le_login.value:
            return u'登录成功'
        elif event == le_kickout.value:
            return u'被踢出'
        elif event == le_normal_leave.value:
            return u'正常登出'
        elif event == le_abnormal_leave.value:
            return u'异常登出'
        elif event == le_someerror.value:
            return u'发生某些错误'
        elif event == le_reject.value:
            return u'被服务器拒绝'
        else:
            return u'未知的登录事件'

    # 解析呼叫事件类型
    def callEventDescript(self, event):
        if event == ce_unknown.value:
            return u'未知'
        elif event == ce_calling.value:
            return u'正在外呼'
        elif event == ce_incoming.value:
            return u'呼入'
        elif event == ce_proceeding.value:
            return u'正在处理中'
        elif event == ce_accept.value:
            return u'接听'
        elif event == ce_decline.value:
            return u'拒绝'
        elif event == ce_busy.value:
            return u'远端忙'
        elif event == ce_unreachable.value:
            return u'不可达'
        elif event == ce_offline.value:
            return u'离线'
        elif event == ce_hangup.value:
            return u'远端挂断'
        elif event == ce_release.value:
            return u'释放'
        elif event == ce_timeout.value:
            return u'超时无人接听'
        elif event == ce_someerror.value:
            return u'某些错误'
        else:
            return u'未知的呼叫事件'

    # 系统事件处理回调函数
    def cbSysEvent(self, event, descript, data):
        logging.debug('imxAPI.cbSysEvent() event: %d, descript: %s' %(event, self.descriptSysEvent(event)))

    # 网络传输状态处理回调函数
    def cbNetState(self, state, data):
        logging.debug('imxAPI.cbNetState() state: nLoss - %d, nRTT - %d, nSendBitrate - %d' %(state.nLoss, state.nRTT, state.nSendBitrate))

    # 登录/登出事件处理回调函数
    def cbLogin(self, notify, data):
        self._loginEvent.set()
        logging.debug('imxAPI.cbLogin() status: %d, descript: %s' %(notify.event, self.descriptLoginEvent(notify.event)))
        if notify.event == le_login.value:
            self._login = True
            logging.debug('user is online.')
        else:
            self._login = False
            logging.debug('user is offline.')

    # 呼叫事件处理回调函数
    def cbCallEvent(self, notify, data):
        logging.debug('imxAPI.cbCallEvent(): event - %d, userId - %s, callId - %s, descript - %s' %(notify.eEvent, notify.szUserID, notify.szCallID, self.callEventDescript(notify.eEvent)))
        if notify.eEvent == ce_unknown.value:       # 未知错误
            if self._cbCallEventUnkown:
                self._cbCallEventUnkown()
        elif notify.eEvent == ce_calling.value:     # 正在外呼
            if self._cbCallEventCalling:
                self._cbCallEventCalling()
        elif notify.eEvent == ce_incoming.value:    # 正在呼入
            logging.debug('incoming call:  caller - %s, callId - %s' %(notify.szUserID, notify.szUserID))
            if self._cbCallEventIncoming:
                self._cbCallEventIncoming()
        elif notify.eEvent == ce_proceeding.value:  # 正在处理
            if self._cbCallEventProceeding:
                self._cbCallEventProceeding()
        elif notify.eEvent == ce_accept.value:      # 接听
            if self._cbCallEventAccept:
                self._cbCallEventAccept()
        elif notify.eEvent == ce_decline.value:     # 拒绝
            if self._cbCallEventDecline:
                self._cbCallEventDecline()
        elif notify.eEvent == ce_busy.value:        # 远端忙
            if self._cbCallEventBusy:
                self._cbCallEventBusy()
        elif notify.eEvent == ce_unreachable.value: # 不可达
            if self._cbCallEventUnreachable:
                self._cbCallEventUnreachable()
        elif notify.eEvent == ce_offline.value:     # 离线
            if self._cbCallEventOffline:
                self._cbCallEventOffline()
        elif notify.eEvent == ce_hangup.value:      # 对方挂断
            if self._cbCallEventHangup:
                self._cbCallEventHangup()
        elif notify.eEvent == ce_release.value:     # 释放
            if self._cbCallEventRelease:
                self._cbCallEventRelease()
        elif notify.eEvent == ce_timeout.value:     # 超时无人接听
            if self._cbCallEventTimeout:
                self._cbCallEventTimeout()
        elif notify.eEvent == ce_someerror.value:   # 某些错误
            if self._cbCallEventSomeerror:
                self._cbCallEventSomeerror()
        else:
            pass

        if notify.eEvent == ce_calling.value or notify.eEvent == ce_incoming.value:
            self._callId = ''
            self._remoteId = ''
            for ch in notify.szCallID:
                self._callId = self._callId + ch
            for ch in notify.szUserID:
                self._remoteId = self._remoteId + ch

    # 设置呼叫事件回调函数 - 未知错误
    def setCallEventUnknown(self, cb):
        self._cbCallEventUnkown, cb = cb, self._cbCallEventUnkown
        return cb

    # 设置呼叫事件回调函数 - 正在外呼
    def setCallEventCalling(self, cb):
        self._cbCallEventCalling, cb = cb, self._cbCallEventCalling
        return cb

    # 设置呼叫事件回调函数 - 正在呼入
    def setCallEventIncoming(self, cb):
        self._cbCallEventIncoming, cb = cb, self._cbCallEventIncoming
        return cb

    # 设置呼叫事件回调函数 - 正在处理
    def setCallEventProceeding(self, cb):
        self._cbCallEventProceeding, cb = cb, self._cbCallEventProceeding
        return cb

    # 设置呼叫事件回调函数 - 接听
    def setCallEventAccept(self, cb):
        self._cbCallEventAccept, cb = cb, self._cbCallEventAccept
        return cb

    # 设置呼叫事件回调函数 - 拒绝
    def setCallEventDecline(self, cb):
        self._cbCallEventDecline, cb = cb, self._cbCallEventDecline
        return cb

    # 设置呼叫事件回调函数 - 远端忙
    def setCallEventBusy(self, cb):
        self._cbCallEventBusy, cb = cb, self._cbCallEventBusy
        return cb

    # 设置呼叫事件回调函数 - 不可达
    def setCallEventUnreachable(self, cb):
        self._cbCallEventUnreachable, cb = cb, self._cbCallEventUnreachable
        return cb

    # 设置呼叫事件回调函数 - 离线
    def setCallEventOffline(self, cb):
        self._cbCallEventOffline, cb = cb, self._cbCallEventOffline
        return cb

    # 设置呼叫事件回调函数 - 对方挂断
    def setCallEventHangup(self, cb):
        self._cbCallEventHangup, cb = cb, self._cbCallEventHangup
        return cb

    # 设置呼叫事件回调函数 - 释放
    def setCallEventRelease(self, cb):
        self._cbCallEventRelease, cb = cb, self._cbCallEventRelease
        return cb

    # 设置呼叫事件回调函数 - 超时无人接听
    def setCallEventTimeout(self, cb):
        self._cbCallEventTimeout, cb = cb, self._cbCallEventTimeout
        return cb

    # 设置呼叫事件回调函数 - 某些错误
    def setCallEventSomeerror(self, cb):
        self._cbCallEventSomeerror, cb = cb, self._cbCallEventSomeerror
        return cb


################################################################################
# 测试程序

# TODO:
