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
if platform.system().lower() == 'windows':
    import manager.buttonSIM as button
elif platform.system().lower() == 'linux':
    import manager.buttonAPI as button
else:
    raise NotImplementedError

__all__ = [
        'init',
        'fini',
        'version',
        'setLog',
        'login',
        'logout',
        'call',
        'accept',
        'decline',
        'hangup'
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


# 局部变量
_cdll           = None
_callId         = ''
_remoteId       = ''
_server         = None
_port           = None
_personId       = None
_callIn         = False

_callEvent      = None
_loginEvent     = None

_cbSysEvent     = None
_cbNetState     = None
_cbLogin        = None
_cbCallEvent    = None

_debugEvent     = None


# 解析系统事件类型
def descriptSysEvent(event):
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
def descriptLoginEvent(event):
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
def callEventDescript(event):
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
    logging.debug('imxAPI.cbSysEvent() event: %d, descript: %s' %(event, descriptSysEvent(event)))


# 网络传输状态处理回调函数
def cbNetState(state, data):
    logging.debug('imxAPI.cbNetState() state: nLoss - %d, nRTT - %d, nSendBitrate - %d' %(state.nLoss, state.nRTT, state.nSendBitrate))


# 登录/登出事件处理回调函数
def cbLogin(notify, data):
    global _loginEvent
    logging.debug('imxAPI.cbLogin() status: %d, descript: %s' %(notify.event, descriptLoginEvent(notify.event)))
    if notify.event == le_login.value:
        _loginEvent.set()
        logging.debug('========== user online ==========')
    else:
        _loginEvent.clear()
        logging.debug('========== user offline ==========')


# 呼叫事件处理回调函数
def cbCallEvent(notify, data):
    global _callIn, _callEvent, _callId, _remoteId
    logging.debug('imxAPI.cbCallEvent(): event - %d, userId - %s, callId - %s, descript - %s' %(notify.eEvent, notify.szUserID, notify.szCallID, callEventDescript(notify.eEvent)))
    if notify.eEvent == ce_incoming.value:
        # 外部呼入
        logging.debug('incoming call:  caller - %s, callId - %s' %(notify.szUserID, notify.szUserID))
        _callIn = True
    elif notify.eEvent == ce_calling.value:
        # 正在外呼
        _callIn = False
    elif notify.eEvent == ce_accept.value:
        # 连接成功
        _callIn = False
        _callEvent.set()
    else:
        # 未知事件 | 释放 | 拒接 | 远端忙 | 不可达 | 离线 | 远端挂断 | 释放 | 超时无人接听 | 某些错误
        _callIn = False
        _callEvent.clear()

    if notify.eEvent == ce_calling.value or notify.eEvent == ce_incoming.value:
        _callId = ''
        _remoteId = ''
        for ch in notify.szCallID:
            _callId = _callId + ch
        for ch in notify.szUserID:
            _remoteId = _remoteId + ch


# 获取视频模块版本信息
def version():
    global _cdll
    logging.debug('imxAPI.version().')
    version = ''
    if _cdll:
        majVer = c_int(0)
        subVer = c_int(0)
        extVer = c_int(0)
        build  = c_int(0)
        _cdll.ImxGetSDKVersion(pointer(majVer), pointer(subVer), pointer(extVer), pointer(build))
        version = str(majVer.value) + '.' + str(subVer.value) + '.' + str(extVer.value) + '.' + str(build.value)
    logging.debug('imxAPI.version(): %s' %(version))
    return version


# 设置视频模块日志开关
def setLog(onOff):
    global _cdll
    logging.debug('imxAPI.setLog(%s)' %('on' if onOff else 'off'))
    _cdll.ImxSetLog(c_bool(True if onOff else False))


# 初始化视频模块
def init(server, port, personId):
    global _cdll, _server, _port, _personId, _loginEvent, _callEvent
    global _cbSysEvent, _cbLogin, _cbCallEvent, _cbNetState
    _server, _port, _personId = server, port, personId
    if not _loginEvent:
        _loginEvent = threading.Event()
    _loginEvent.clear()
    if not _callEvent:
        _callEvent  = threading.Event()
    _callEvent.clear()
    logging.debug('imxAPI.init(server - %s, port - %d, personId - %s).' %(server, port, personId))
    ret = False
    try:
        if not _cdll:
            logging.debug('load library: %s' %IMX_LIBRARY_PATH)
            _cdll        = cdll.LoadLibrary(IMX_LIBRARY_PATH)
            _cbSysEvent  = sys_event_callback_t(cbSysEvent)
            _cbLogin     = login_callback_t(cbLogin)
            _cbCallEvent = call_event_callback_t(cbCallEvent)
            _cbNetState  = net_state_callback_t(cbNetState)
            if _cdll.ImxInit(c_char_p(_server),
                             c_ushort(_port),
                             c_ushort(0),
                             c_char_p(_personId),
                             vr_vga,
                             c_bool(False),
                             ll_error,
                             ll_error,
                             _cbSysEvent,
                             _cbLogin,
                             _cbCallEvent,
                             _cbNetState) == 0:
                ret = True
                setLog(False)
            else:
                ret = False
    except:
        pass
    finally:
        logging.debug('imxAPI.init() %s.' %('success' if ret else 'failed'))
        return ret


# 终止视频模块
def fini():
    global _cdll
    logging.debug('imxAPI.fini().')
    if _cdll:
        _cdll.ImxFini()
        _cdll = None


# 登录视频模块
def login():
    global _cdll, _personId
    logging.debug('imxAPI.login().')
    ret = False
    if _cdll and _personId:
        if _cdll.ImxLogin(c_char_p(_personId)) == 0:
            _loginEvent.wait(30)
            if _loginEvent.isSet():
                ret = True
    logging.debug('imxAPI.login(%s) %s.' %(_personId, 'success' if ret else 'failed'))
    return ret


# 登出视频模块
def logout():
    global _cdll
    logging.debug('imxAPI.logout().')
    ret = False
    if _cdll:
        if _cdll.ImxLogout() == 0:
            ret = True
    logging.debug('imxAPI.logout() %s.' %('success' if ret else 'failed'))
    return ret


# 发起视频呼叫
def call(destUserId):
    global _cdll
    logging.debug('imxAPI.call(%s).' %destUserId)
    error = 0
    if _cdll:
        error = _cdll.ImxCall(c_char_p(destUserId))
        if error == 0:
            logging.debug('imxAPI.call(%s) success.' %destUserId)
            return True
    logging.debug('imxAPI.call(%s) failed. error code: %d' %(destUserId, error))
    return False


# 接听视频呼叫
def accept():
    global _cdll, _callId
    logging.debug('imxAPI.accept(%s).' %_callId)
    error = 0
    if _cdll:
        error = _cdll.ImxAccept(c_char_p(_callId))
        if error == 0:
            logging.debug('imxAPI.accept(%s) success.' %_callId)
            return True
    logging.debug('imxAPI.accept(%s) failed. error code: %d' %(_callId, error))
    return False


# 拒接视频呼叫
def decline():
    global _cdll, _callId
    logging.debug('imxAPI.decline(%s).' %_callId)
    error = 0
    if _cdll:
        error = _cdll.ImxDecline(c_char_p(_callId))
        if error == 0:
            logging.debug('imxAPI.decline(%s) success.' %_callId)
            return True
    logging.debug('imxAPI.decline(%s) failed. error code: %d' %(_callId, error))
    return False


# 挂断视频呼叫
def hangup():
    global _cdll, _callId
    logging.debug('imxAPI.hangup(%s).' %_callId)
    error = 0
    if _cdll:
        error = _cdll.ImxHangup(c_char_p(_callId))
        if error == 0:
            logging.debug('imxAPI.hangup(%s) success.' %_callId)
            return True
    logging.debug('imxAPI.hangup(%s) failed. error code: %d' %(_callId, error))
    return False


################################################################################
# 测试程序
_buttonCall = False

# 呼叫按键动作
def actBtnCall():
    global _buttonCall
    _buttonCall = True

# 调试对外呼出
def debugCallOut(destId):
    global _callIn, _callEvent, _callId, _remoteId, _buttonCall

    call(destId)    # 发起对外呼叫

    # 等待对方接听或按键挂断
    _buttonCall = False
    for wait in range(0, 30):
        time.sleep(1)
        if _callEvent.isSet() or _buttonCall:
            break;

    if _callEvent.isSet():
        # 对方接听
        _buttonCall = False
        logging.debug('imxAPI.debugCallOut: %s answere the call.' %_remoteId)
        while True:
            if not _callEvent.isSet():
                # 挂断电话
                logging.debug('imxAPI.debugCallOut: %s hang up.' %(_remoteId if not _buttonCall else _callId))
                break;
            elif _buttonCall:
                hangup()
            time.sleep(0.5)
    elif _buttonCall:
        # 按键挂断处理
        logging.debug('imxAPI.debugCallOut: %s hang up.' %_callId)
        hangup()
    else:
        # 无人接听
        logging.debug('imxAPI.debugCallOut: %s no answered.' %_remoteId)
    _buttonCall = False
    hangup()


# 调试外部呼入
def debugCallIn(autoAccept):
    global _callIn, _callEvent, _callId, _remoteId, _buttonCall

    if autoAccept:
        # 自动接入
        logging.debug('imxAPI.debugCallIn: accept automatically.')
    else:
        # 非自动接入，等待用户按键确认接入
        logging.debug('imxAPI.debugCallIn: accept manually.')
        while True:
            if _buttonCall:
                autoAccept = True
                logging.debug('imxAPI.debugCallIn: %s accepted.' %_callId)
                break;
            elif not _callIn:
                logging.debug('imxAPI.debugCallIn: %s hang up.' %_remoteId)
                break
            time.sleep(0.5)

    if autoAccept:
        accept()
        for wait in range(0, 30):
            # 等待接入成功
            time.sleep(1)
            if _callEvent.isSet():
                break

    if _callEvent.isSet():
        # 接入成功
        _buttonCall = False
        while True:
            if not _callEvent.isSet():
                # 挂断电话
                logging.debug('imxAPI.debugCallIn: %s hang up.' %(_remoteId if not _buttonCall else _callId))
                break;
            elif _buttonCall:
                hangup()
            time.sleep(0.5)
    else:
        # 未接听
        logging.debug('imxAPI.debugCallIn: %s not accepted.' %_callId)
    _buttonCall = False
    hangup()

# 调试视频通话模块
def debugImx(server, port, personId, destId):
    global _buttonCall, _callIn

    # 初始化按键
    button.init()
    cbButton = button.setCallCallback(actBtnCall)

    # 初始化视频通话模块
    init(server, port, personId)
    version()
    try:
        if login():
            # 登录成功
            autoAccept = True
            while True:
                if _buttonCall:
                    # 向外呼出
                    debugCallOut(destId)
                elif _callIn:
                    # 外部呼入
                    debugCallIn(autoAccept)
                    autoAccept = not autoAccept
                time.sleep(1)
    except KeyboardInterrupt:
        logging.debug('Quit by user...')
    finally:
        logout()
        fini()
        button.setCallCallback(cbButton)
        sys.exit()

# 测试程序
if __name__ == '__main__':
    debugImx('47.104.157.108', 0, 'joyee', 'jove')

