#!/usr/bin/python
# -*- coding: utf8 -*-

from ctypes import *
import threading
import logging
import time
import sys
import json
import requests

__all__ = [
        'imxInit',
        'imxFini',
        'imxGetSDKVersion',
        'imxSetLog',
        'imxLogin',
        'imxLogout',
        'imxCall',
        'imxAccept',
        'imxDecline',
        'imxHangup'
        ]

logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(levelname)s- %(message)s')

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


# 局部变量
_imxCdll        = None
_imxCallId      = ''
_imxRemoteId    = ''
_imxServer      = None
_imxPort        = None
_imxDevId       = None
_imxCallIn      = False

_imxCallEvent   = None
_imxLoginEvent  = None

_cbSysEvent     = None
_cbNetState     = None
_cbLogin        = None
_cbCallEvent    = None


# 解析系统事件类型
def sysEventDescript(event):
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
def loginEventDescrpt(event):
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
def callEventDescrpt(event):
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
def cbSysEvent(event, descript, data):
    logging.debug('cbSysEvent() event: %d, descript: %s' %(event, sysEventDescript(event)))


# 网络传输状态处理回调函数
def cbNetState(state, data):
    logging.debug('cbNetState() state: nLoss - %d, nRTT - %d, nSendBitrate - %d' %(state.nLoss, state.nRTT, state.nSendBitrate))


# 登录/登出事件处理回调函数
def cbLogin(notify, data):
    global _imxLoginEvent

    logging.debug('cbLogin() status: %d, descript: %s' %(notify.event, loginEventDescrpt(notify.event)))
    if notify.event == le_login.value:
        _imxLoginEvent.set()
        logging.debug('========== user online ==========')
    else:
        _imxLoginEvent.clear()
        logging.debug('========== user offline ==========')


# 呼叫事件处理回调函数
def cbCallEvent(notify, data):
    global _imxCallIn, _imxCallEvent, _imxCallId, _imxRemoteId

    logging.debug('cbCallEvent(): event - %d, userId - %s, callId - %s, descript - %s' %(notify.eEvent, notify.szUserID, notify.szCallID, callEventDescrpt(notify.eEvent)))
    if notify.eEvent == ce_incoming.value:
        # 外部呼入
        logging.debug('>>>> incoming call .... caller: %s, callId: %s' %(notify.szUserID, notify.szUserID))
        logging.debug('Will you accept the incoming call ?')
        _imxCallIn = True
    elif notify.eEvent == ce_calling.value:
        # 正在外呼
        _imxCallIn = False
    elif notify.eEvent == ce_accept.value:
        # 连接成功
        _imxCallIn = False
        _imxCallEvent.set()
    else:
        # 未知事件 | 释放 | 拒接 | 远端忙 | 不可达 | 离线 | 远端挂断 | 释放 | 超时无人接听 | 某些错误
        _imxCallIn = False
        _imxCallEvent.clear()

    if notify.eEvent == ce_calling.value or notify.eEvent == ce_incoming.value:
        _imxCallId = ''
        _imxRemoteId = ''
        for ch in notify.szCallID:
            _imxCallId = _imxCallId + ch
        for ch in notify.szUserID:
            _imxRemoteId = _imxRemoteId + ch


# 获取视频模块版本信息
def imxGetSDKVersion():
    global _imxCdll

    if _imxCdll:
        majVer = c_int(0)
        subVer = c_int(0)
        extVer = c_int(0)
        build  = c_int(0)
        _imxCdll.ImxGetSDKVersion(pointer(majVer), pointer(subVer), pointer(extVer), pointer(build))
        version = str(majVer.value) + '.' + str(subVer.value) + '.' + str(extVer.value) + '.' + str(build.value)
        logging.debug('imxGetSDKVersion(): %s' %(version))
        return version
    return ''


# 设置视频模块日志开关
def imxSetLog(onOff):
    global _imxCdll

    logging.debug('imxSetLog(%s)' %('on' if onOff else 'off'))
    _imxCdll.ImxSetLog(c_bool(True if onOff else False))


# 初始化视频模块
def imxInit(server, port, devId):
    global _imxCdll, _imxServer, _imxPort, _imxDevId, _imxLoginEvent, _imxCallEvent
    global _cbSysEvent, _cbLogin, _cbCallEvent, _cbNetState

    _imxServer = server
    _imxPort = port
    _imxDevId = devId
    if not _imxLoginEvent:
        _imxLoginEvent = threading.Event()
    _imxLoginEvent.clear()
    if not _imxCallEvent:
        _imxCallEvent  = threading.Event()
    _imxCallEvent.clear()
    logging.debug('imxInit(server - %s, port - %d, devId - %s) start.' %(server, port, devId))
    try:
        ret = True
        if not _imxCdll:
            _imxCdll     = cdll.LoadLibrary(IMX_LIBRARY_PATH)
            logging.debug('load library: %s' %IMX_LIBRARY_PATH)
            _cbSysEvent  = sys_event_callback_t(cbSysEvent)
            _cbLogin     = login_callback_t(cbLogin)
            _cbCallEvent = call_event_callback_t(cbCallEvent)
            _cbNetState  = net_state_callback_t(cbNetState)
            imxSetLog(False)
            if _imxCdll.ImxInit(c_char_p(_imxServer),
                                c_ushort(_imxPort),
                                c_ushort(0),
                                c_char_p(_imxDevId),
                                vr_vga,
                                c_bool(False),
                                ll_error,
                                ll_error,
                                _cbSysEvent,
                                _cbLogin,
                                _cbCallEvent,
                                _cbNetState) != 0:
                ret = False
    except:
        ret = False
    finally:
        logging.debug('imxInit() %s.' %('success' if ret else 'failed'))
        return ret


# 终止视频模块
def imxFini():
    global _imxCdll

    logging.debug('imxFini() start.')
    if _imxCdll:
        _imxCdll.ImxFini()
        _imxCall = None


# 登录视频模块
def imxLogin():
    global _imxCdll, _imxDevId

    ret = False
    if _imxCdll and _imxDevId:
        logging.debug('imxLogin(%s) start.' %_imxDevId)
        if _imxCdll.ImxLogin(c_char_p(_imxDevId)) == 0:
            ret = True
        logging.debug('imxLogin(%s) %s.' %(_imxDevId, 'success' if ret else 'failed'))
    return ret


# 登出视频模块
def imxLogout():
    global _imxCdll

    logging.debug('imxLogout() start.')
    ret = False
    if _imxCdll:
        if _imxCdll.ImxLogout() == 0:
            ret = True
    logging.debug('imxLogout() %s.' %('success' if ret else 'failed'))
    return ret


# 发起视频呼叫
def imxCall(destUserId):
    global _imxCdll

    error = 0
    logging.debug('imxCall(%s) start.' %destUserId)
    if _imxCdll:
        error = _imxCdll.ImxCall(c_char_p(destUserId))
        if error == 0:
            logging.debug('imxCall(%s) success.' %destUserId)
            return True
    logging.debug('imxCall(%s) failed. error code: %d' %(destUserId, error))
    return False


# 接听视频呼叫
def imxAccept():
    global _imxCdll, _imxCallId

    error = 0
    logging.debug('imxAccept(%s) start.' %_imxCallId)
    if _imxCdll:
        error = _imxCdll.ImxAccept(c_char_p(_imxCallId))
        if error == 0:
            logging.debug('imxAccept(%s) success.' %_imxCallId)
            return True
    logging.debug('imxAccept(%s) failed. error code: %d' %(_imxCallId, error))
    return False


# 拒接视频呼叫
def imxDecline():
    global _imxCdll, _imxCallId

    error = 0
    logging.debug('imxDecline(%s) start.' %_imxCallId)
    if _imxCdll:
        error = _imxCdll.ImxDecline(c_char_p(_imxCallId))
        if error == 0:
            logging.debug('imxDecline(%s) success.' %_imxCallId)
            return True
    logging.debug('imxDecline(%s) failed. error code: %d' %(_imxCallId, error))
    return False


# 挂断视频呼叫
def imxHangup():
    global _imxCdll, _imxCallId

    error = 0
    logging.debug('imxHangup(%s) start.' %_imxCallId)
    if _imxCdll:
        error = _imxCdll.ImxHangup(c_char_p(_imxCallId))
        if error == 0:
            logging.debug('imxHangup(%s) success.' %_imxCallId)
            return True
    logging.debug('imxHangup(%s) failed. error code: %d' %(_imxCallId, error))
    return False


# 视频呼出调试程序
def debugCallOut():
    global _imxLoginEvent, _imxCallEvent, _imxCallIn

    server = '47.104.157.108'
    port = 0
    devId = 'joyee'
    imxInit(server, port, devId)
    imxGetSDKVersion()
    try:
        while True:
            imxLogin()  # 登录
            _imxLoginEvent.wait(30)
            while _imxLoginEvent.isSet():
                # 登录成功
                time.sleep(1)
                imxCall('jove')
                _imxCallEvent.wait(30)      # 等待连接成功
                if _imxCallEvent.isSet() and not _imxCallIn:
                    # 处理呼叫事件
                    time.sleep(10)
                    imxHangup()
                    while _imxCallEvent.isSet():
                        time.sleep(1)
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
    finally:
        imxLogout()
        imxFini()
        sys.exit(0)


# 视频呼入调试程序
def debugCallIn():
    global _imxLoginEvent, _imxCallEvent

    server = '47.104.157.108'
    port = 0
    devId  = 'joyee'
    imxInit(server, port, devId)
    imxGetSDKVersion()
    try:
        while True:
            imxLogin()      # 登录
            _imxLoginEvent.wait(30)
            while _imxLoginEvent.isSet():
                # 登录成功
                while not _imxCallIn:
                    time.sleep(1)   # 等待外部呼入
                imxAccept()
                _imxCallEvent.wait(30)      # 等待连接成功
                if _imxCallEvent.isSet():
                    # 处理呼入事件
                    timeout = 0
                    while _imxCallEvent.isSet():
                        time.sleep(1)
                        timeout = timeout + 1
                        if timeout == 15:   # 15 秒后自动挂断
                            imxHangup()
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
    finally:
        imxLogout()
        imxFini()
        sys.exit(0)


if __name__ == '__main__':
    debugCallOut()

