#!/usr/bin/python
# -*- coding: utf8 -*-


import json
import ssl
import requests
import threading
import logging
import time
import traceback


# from mp3Manager import *
# from buttonManager import *


__all__ = [
        'robotInit',
        'robotLogin',
        'robotHeartbeat',
        'robotGetConfig',
        'robotGetPersonList',
        'robotGetMp3List',
        'robotUpdateMp3List',
        'robotGetDoctorList',
        'robotUpdateDoctorList',
        ]


ROBOT_LOGIN_URL_POSTFIX     = '/medical/auth/robot/login'       # 机器人登录地址后缀
ROBOT_GET_TOKEN_URL_POSTFIX = '/medical/auth/api/getLoginToken' # 机器人获取登录令牌后缀
ROBOT_CONFIG_URL_POSTFIX    = '/medical/robot/findMyConfig'     # 机器人配置信息地址后缀
ROBOT_MP3_LIST_URL_POSTFIX  = '/medical/robot/listMp3'          # 机器人音频列表地址后缀
ROBOT_MP3_FILE_URL_POSTFIX  = '/medical/basic/file/download'    # 机器人音频文件地址后缀
ROBOT_HEATBEAT_URL_POSTFIX  = '/medical/robot/heartbeat'        # 机器人心跳地址后缀
DOCTOR_LIST_URL_POSTFIX     = '/medical/robot/listOnlineDoctor' # 在线医生列表地址


logging.basicConfig(level = logging.DEBUG,
                    format = ' %(asctime)s - %(levelname)s- %(message)s')


# 局部变量
_hostName       = None
_portNumber     = None
_robotId        = None

_loginToken     = None
_token          = None
_rbtId          = None
_gps            = None

_vsvrIp         = None
_vsvrPort       = None

_playVersion    = 0
_playUpdate     = False
_confVersion    = 0
_confUpdate     = False

_mp3List        = []
_personList     = []
_doctorList     = []


# 机器人初始化
#
#   hostName    - 系统服务器地址
#   portNumber  - 访问端口号
#   robotId     - 机器识别码
def robotInit(hostName, portNumber, robotId):
    global _hostName, _portNumber, _robotId, _loginToken, _token, _rbtId, _gps, _vsvrIp, _vsvrPort, _playVersion, _playUpdate, _confVersion, _confUpdate, _mp3List, _personList, _doctorList

    _hostName       = hostName
    _portNumber     = portNumber
    _robotId        = robotId

    _loginToken     = None
    _token          = None
    _rbtId          = None
    _gps            = None

    _vsvrIp         = None
    _vsvrPort       = None

    _playVersion    = 0
    _playUpdate     = False
    _confVersion    = 0
    _confUpdate     = False

    _mp3List        = []
    _personList     = []
    _doctorList     = []
    requests.packages.urllib3.disable_warnings()


# 机器人获取登录令牌
def robotGetLoginToken():
    global _token, _loginToken
    logging.debug('robotGetLoginToken() start ...')
    try:
        tokenUrl = _hostName + ':' + _portNumber + ROBOT_GET_TOKEN_URL_POSTFIX
        rsp = requests.get(tokenUrl, verify = False)
        logging.debug('robot get login token: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                _loginToken = js['data']['loginToken']
                logging.debug('robot get token success.')
            return True
    except:
        logging.debug('robot get token failed.')
        traceback.print_exc()
        return False


# 机器人登录
def robotLogin():
    global _hostName, _portNumber, _robotId, _token, _loginToken
    logging.debug('robotLogin() start ...')
    try:
        loginUrl = _hostName + ':' + _portNumber + ROBOT_LOGIN_URL_POSTFIX
        headers = {
                'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
                'access_token': _loginToken
                }
        payload = { 'robotId': _robotId }
        rsp = requests.post(loginUrl, headers = headers, data = payload, verify = False)
        logging.debug('robot login: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                _token = js['data']['token']
                logging.debug('robot login success.')
                return True
        logging.debug('robot login failed.')
        return False
    except:
        logging.debug('robot login failed.')
        traceback.print_exc()
        return False


# 获取机器人配置信息
def robotGetConfig():
    global _hostName, _portNumber, _token, _rbtId, _vsvrIp, _vsvrPort, _personList

    logging.debug('robotGetConfig() start ...')
    try:
        configUrl = _hostName + ':' + _portNumber + ROBOT_CONFIG_URL_POSTFIX
        logging.debug('robot get config: url - %s, token - %s' %(configUrl, _token))
        headers = { 'access_token': _token }
        rsp = requests.get(configUrl, headers = headers, verify = False)
        logging.debug('robot get config: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                if 'data' in js:
                    # 获取机器人编码配置
                    if 'rbtId' in js['data']:
                        _rbtId      = js['data']['rbtId']
                        logging.debug('robot get config: rbtId - %s' %_rbtId)

                    # 获取视频服务器配置
                    if 'videoServer' in js['data']:
                        vsvrIp     = js['data']['videoServer']['vsvrIp']
                        vsvrPort   = js['data']['videoServer']['vsvrPort']
                        logging.debug('robot get config: vsvrIp - %s, vsvrPort: %s' %(vsvrIp, vsvrPort))
                        if vsvrIp != _vsvrIp or vsvrPort != _vsvrPort:
                            # 视频服务器地址发生变化，重新登录
                            _vsvrIp   = vsvrIp
                            _vsvrPort = vsvrPort
                            """
                            重新登录视频服务器
                            to be done
                            """

                    # 获取居民配置信息
                    if 'person' in js['data']:
                        _personList.clear()
                        for index in range(len(js['data']['person'])):
                            person = {
                                    'id':           js['data']['person'][index]['id'],
                                    'rbtId':        js['data']['person'][index]['rbtId'],
                                    'sensorId':     js['data']['person'][index]['sensorId'],
                                    'personId':     js['data']['person'][index]['personId'],
                                    'monitorInv':   js['data']['person'][index]['monitorInv'],
                                    'systolicPre':  0,
                                    'diastolicPre': 0,
                                    'heartRate':    0
                                    }
                            _personList.append(person)
                            logging.debug('Person %d - id = %s, rbtId = %s, sensorId = %s, personId = %s, monitorInv = %d' %(index + 1, person['id'], person['rbtId'], person['sensorId'], person['personId'], person['monitorInv']))

                    logging.debug('robot get config success.')
                    return True
            return False
    except:
        logging.warning('robot get config failed.')
        traceback.print_exc()
        return False


# 获取居民信息
def robotGetPersonList():
    global _personList
    return _personList


# 设置居民健康参数
def robotSetPersonHvx(sensorId, systolicPre, diastolicPre, heartRate):
    global _personList
    for index in range(len(_personList)):
        if sensorId == _personList[index]['sensorId']:
            _personList[index]['systolicPre']   = systolicPre
            _personList[index]['diastolicPre']  = diastolicPre
            _personList[index]['heartRate']     = heartRate
            return True
    return False


# 获取音频播放列表
def robotGetMp3List():
    global _mp3List
    return _mp3List


# 机器人更新音频播放列表
def robotUpdateMp3List():
    global _hostName, _portNumber, _token, _mp3List
    logging.debug('robotUpdateMp3List() start ...')
    try:
        mp3ListUrl = _hostName + ':' + _portNumber + ROBOT_MP3_LIST_URL_POSTFIX
        headers = { 'access_token': _token }
        rsp = requests.get(mp3ListUrl, headers = headers, verify = False)
        logging.debug('robot update mp3 list: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            _mp3List.clear()
            for index in range(len(js['data'])):
                if js['data'][index]['fileId']:
                    mp3 = {
                            'fileId':   js['data'][index]['fileId'],
                            'fileName': js['data'][index]['fileName'],
                            'pri':      js['data'][index]['pri']
                            }
                    _mp3List.append(mp3)
                    logging.debug('mp3 %d - fileId = %s, fileName = %s, pri = %s' %(index + 1, mp3['fileId'], mp3['fileName'], mp3['pri']))

            logging.debug('robot update mp3 list success.')
            return True
        logging.debug('robot update mp3 list failed.')
        return False
    except:
        logging.debug('robot update mp3 list failed.')
        traceback.print_exc()
        return False


# 机器人获取在线医生列表
def robotGetDoctorList():
    global _doctorList
    return _doctorList


# 机器人更新在线医生列表
def robotUpdateDoctorList():
    global _hostName, _portNumber, _token, _personList, _doctorList
    logging.debug('robotUpdateDoctorList() start ...')
    if len(_personList) > 0:
        try:
            doctorListUrl = hostName + ':' + portNumber + DOCTOR_LIST_URL_POSTFIX
            headers = {
                    'Content-Type': 'application/json;charset=UTF-8',
                    'access_token': _token
                    }
            payload = { 'personId': _personList[0]['personId'] }
            rsp = requests.post(doctorListUrl, headers = headers, data = json.dumps(payload), verify = False)
            logging.debug('robot update doctor list: rsp.status_code - %d', rsp.status_code)
            if rsp.status_code == 200:
                js = rsp.json()
                logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
                if 'code' in js and js['code'] == 0:
                    _doctorList.clear()
                    for index in range(len(js['data'])):
                        doctor = {
                                'id':           js['data'][index]['id'],
                                'name':         js['data'][index]['name'],
                                'role':         js['data'][index]['role'],
                                'onlineSts':    js['data'][index]['onlineSts']
                                }
                        _doctorList.append(doctor)
                    logging.debug('robot update doctor list success.')
                    return True
            logging.debug('robot update doctor list failed.')
            return False
        except:
            logging.debug('robot update doctor list failed.')
            traceback.print_exc()
            return False
    logging.debug('robot update doctor list failed: no person.')
    return False


# 机器人心跳同步
def robotHeartbeat():
    global _hostName, _portNumber, _rbtId, _token, _personList, _gps, _playVersion, _playUpdate, _confVersion, _confUpdate
    logging.debug('robotHeartbeat() start ...')
    heatbeatUrl = _hostName + ':' + _portNumber + ROBOT_HEATBEAT_URL_POSTFIX
    try:
        logging.debug('robot heartbeat: url - %s, rbtId - %s, token - %s' %(heatbeatUrl, _rbtId, _token))
        headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'access_token': _token
                }
        payload = { 'rbtId': _rbtId,
                    'data': [] }
        for person in _personList:
            data = {}
            data['personId']     = person['personId']
            data['systolicPre']  = person['systolicPre']
            data['diastolicPre'] = person['diastolicPre']
            data['heartRate']    = person['heartRate']
            data['gps']          = _gps
            payload['data'].append(data)

        if _playUpdate:
            payload['playVer'] = _playVersion
            _playUpdate = False
        if _confUpdate:
            payload['confVer'] = _confVersion
            _confUpdate = False

        logging.debug('headers: - %s' %(json.dumps(headers, indent = 4, ensure_ascii = False)))
        logging.debug('message: - %s' %(json.dumps(payload, indent = 4, ensure_ascii = False)))

        rsp = requests.post(heatbeatUrl, headers = headers, data = json.dumps(payload), verify = False)
        logging.debug('robot heatbeat: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                _playUpdate = False
                _confUpdate = False

                # 检查配置信息是否有更新
                if 'confVer' in js['data']:
                    logging.debug('robot heatbeat: update config version - %d.', js['data']['confVer'])
                    if robotGetConfig():
                        _confVersion = js['data']['confVer']
                        _confUpdate  = True

                # 检查音频列表是否有更新
                if 'playVer' in js['data']:
                    logging.debug('robot heatbeat: update play version - %d.', js['data']['playVer'])
                    if robotUpdateMp3List():
                        _playVersion = js['data']['playVer']
                        _playUpdate  = True
                        """
                        启动后台下载音频列表
                        to be done
                        """

            logging.debug('robot heartbeat success.')
            return True

        logging.debug('robot heartbeat failed.')
        return False
    except:
        logging.debug('robot heartbeat failed.')
        traceback.print_exc()
        return False


# 调试程序
if __name__ == '__main__':
    hostName    = 'https://ttyoa.com'
    portNumber  = '8098'
    robotId     = 'b827eb319c88'
    try:
        robotInit(hostName, portNumber, robotId)
        robotGetLoginToken()
        if robotLogin():
            robotGetConfig()
            # if robotUpdateMp3List():
            #     mp3FileUrl = hostName + ':' + portNumber + ROBOT_MP3_FILE_URL_POSTFIX
            #     mp3ListInit()
            #     mp3ListUpdateStart(mp3FileUrl, robotGetMp3List(), _token)
            # print(robotGetMp3List())
            # robotHeartbeat()
            # robotUpdateDoctorList()
            # print(robotGetDoctorList())
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        mp3ListUpdateStop()
