#!/usr/bin/python
# -*- coding: utf8 -*-

import json
import requests
import logging
import traceback

if __name__ == '__main__':
    import sys
    sys.path.append('..')

import data_access.settings
from utility import setLogging

__all__ = [
        'init',
        'login',
        'heatbeat',
        'getConfig',
        'getMp3List',
        'getPersonList',
        'getDoctorList'
        ]

LOGIN_URL_POSTFIX       = '/medical/auth/robot/login'       # 机器人登录地址后缀
GET_TOKEN_URL_POSTFIX   = '/medical/auth/api/getLoginToken' # 机器人获取登录令牌后缀
CONFIG_URL_POSTFIX      = '/medical/robot/findMyConfig'     # 机器人配置信息地址后缀
HEATBEAT_URL_POSTFIX    = '/medical/robot/heartbeat'        # 机器人心跳地址后缀
MP3_LIST_URL_POSTFIX    = '/medical/robot/listMp3'          # 音频列表地址后缀
DOCTOR_LIST_URL_POSTFIX = '/medical/robot/listOnlineDoctor' # 在线医生列表地址


# 局部变量
_hostName       = None
_portNumber     = None
_robotId        = None

_token          = None
_rbtId          = None
_gps            = None

_personList     = []


# 初始化服务器模块
def init(hostName, portNumber, robotId):
    global _hostName, _portNumber, _robotId, _gps

    _hostName = hostName
    _portNumber = portNumber
    _robotId = robotId
    _, settings = data_access.settings.get_settings()
    _gps = settings['gpsCoord']

    requests.packages.urllib3.disable_warnings()

# 获取登录令牌
def getLoginToken():
    global _token

    ret = False
    loginToken = None
    logging.debug('serverAPI.getLoginToken() start.')
    try:
        tokenUrl = _hostName + ':' + _portNumber + GET_TOKEN_URL_POSTFIX
        logging.debug('get login token: url - %s' %tokenUrl)
        rsp = requests.get(tokenUrl, verify = False)
        logging.debug('get login token: rsp.status_code - %d' %rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                loginToken = js['data']['loginToken']
                ret = True
    except:
        traceback.print_exc()
    finally:
        logging.debug('serverAPI.getLoginToken %s.' %('success' if ret else 'failed'))
        return ret, loginToken


# 登录
def login():
    global _hostName, _portNumber, _robotId, _token

    ret = False
    logging.debug('serverAPI.login() start.')
    ret, loginToken = getLoginToken()
    if ret:
        try:
            loginUrl = _hostName + ':' + _portNumber + LOGIN_URL_POSTFIX
            logging.debug('login: url - %s, loginToken - %s' %(loginUrl, loginToken))
            headers = {
                    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
                    'access_token': loginToken
                    }
            payload = { 'robotId': _robotId }
            rsp = requests.post(loginUrl, headers = headers, data = payload, verify = False)
            logging.debug('login: rsp.status_code - %d', rsp.status_code)
            if rsp.status_code == 200:
                js = rsp.json()
                logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
                if 'code' in js and js['code'] == 0:
                    _token = js['data']['token']
                    ret = True
        except:
            traceback.print_exc()
    logging.debug('serverAPI.login() %s' %('success' if ret else 'failed'))
    return ret, _token


# 获取配置信息
def getConfig():
    global _hostName, _portNumber, _token, _rbtId

    ret = False
    vsvrIp = ''
    vsvrPort = 0
    logging.debug('serverAPI.getConfig() start.')
    try:
        configUrl = _hostName + ':' + _portNumber + CONFIG_URL_POSTFIX
        logging.debug('get config: url - %s, token - %s' %(configUrl, _token))
        headers = { 'access_token': _token }
        rsp = requests.get(configUrl, headers = headers, verify = False)
        logging.debug('get config: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                if 'data' in js:
                    # 获取机器人编码配置
                    if 'rbtId' in js['data']:
                        _rbtId = js['data']['rbtId']
                        logging.debug('get config: rbtId - %s' %_rbtId)

                    # 获取视频服务器配置
                    if 'videoServer' in js['data']:
                        vsvrIp = js['data']['videoServer']['vsvrIp']
                        vsvrPort = js['data']['videoServer']['vsvrPort']
                        logging.debug('get config: vsvrIp - %s, vsvrPort: %s' %(vsvrIp, vsvrPort))

                    # 获取居民配置信息
                    if 'person' in js['data']:
                        del _personList[:]
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
                            logging.debug('get config: person %d - id = %s, rbtId = %s, sensorId = %s, personId = %s, monitorInv = %d' %(index + 1, person['id'], person['rbtId'], person['sensorId'], person['personId'], person['monitorInv']))
                    ret = True
    except:
        traceback.print_exc()
    finally:
        logging.debug('serverAPI.getConfig() %s.' %('success' if ret else 'failed'))
        return ret, vsvrIp, vsvrPort, _personList


# 获取音频列表
def getMp3List():
    global _hostName, _portNumber, _token

    ret = False
    mp3List = []
    logging.debug('serverAPI.getMp3List() start.')
    try:
        mp3ListUrl = _hostName + ':' + _portNumber + MP3_LIST_URL_POSTFIX
        logging.debug('get mp3 list: url - %s, token - %s' %(mp3ListUrl, _token))
        headers = { 'access_token': _token }
        rsp = requests.get(mp3ListUrl, headers = headers, verify = False)
        logging.debug('get mp3 list: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            for index in range(len(js['data'])):
                if js['data'][index]['fileId']:
                    mp3 = {
                            'fileId':   js['data'][index]['fileId'],
                            'fileName': js['data'][index]['fileName'],
                            'pri':      js['data'][index]['pri']
                            }
                    mp3List.append(mp3)
                    logging.debug('get mp3 list: mp3 %d - fileId = %s, fileName = %s, pri = %s' %(index + 1, mp3['fileId'], mp3['fileName'], mp3['pri']))
            ret = True
    except:
        traceback.print_exc()
    finally:
        logging.debug('serverAPI.getMp3List() %s.' %('success' if ret else 'failed'))
        return ret, mp3List


# 获取居民列表
def getPersonList():
    global _personList
    return _personList


# 获取在线医生列表
def getDoctorList(personId):
    global _hostName, _portNumber, _token

    ret = False
    doctorList = []
    logging.debug('serverAPI.getDoctorList() start.')
    try:
        doctorListUrl = hostName + ':' + portNumber + DOCTOR_LIST_URL_POSTFIX
        logging.debug('get doctor list: url - %s, token - %s' %(doctorListUrl, _token))
        headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'access_token': _token
                }
        payload = { 'personId': personId }
        rsp = requests.post(doctorListUrl, headers = headers, data = json.dumps(payload), verify = False)
        logging.debug('get doctor list: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                for index in range(len(js['data'])):
                    doctor = {
                            'id':           js['data'][index]['id'],
                            'name':         js['data'][index]['name'],
                            'role':         js['data'][index]['role'],
                            'onlineSts':    js['data'][index]['onlineSts']
                            }
                    doctorList.append(doctor)
                ret = True
    except:
        traceback.print_exc()
    finally:
        logging.debug('serverAPI.getDoctorList() %s.' %('success' if ret else 'failed'))
        return ret, doctorList


# 心跳同步
def heatbeat(playVer = None, cbUpdatePlay = None, confVer = None, cbUpdateConf = None):
    global _hostName, _portNumber, _token, _rbtId, _personList

    ret, playUpdate, confUpdate = False, None, None
    logging.debug('serverAPI.heartbeat() start ...')
    try:
        heatbeatUrl = _hostName + ':' + _portNumber + HEATBEAT_URL_POSTFIX
        logging.debug('heartbeat: url - %s, token - %s' %(heatbeatUrl, _token))
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
        if playVer:
            payload['playVer'] = playVer
        if confVer:
            payload['confVer'] = confVer

        logging.debug('headers: - %s' %(json.dumps(headers, indent = 4, ensure_ascii = False)))
        logging.debug('message: - %s' %(json.dumps(payload, indent = 4, ensure_ascii = False)))

        rsp = requests.post(heatbeatUrl, headers = headers, data = json.dumps(payload), verify = False)
        logging.debug('heatbeat: rsp.status_code - %d', rsp.status_code)
        if rsp.status_code == 200:
            js = rsp.json()
            logging.debug(json.dumps(js, indent = 4, ensure_ascii = False))
            if 'code' in js and js['code'] == 0:
                # 检查配置信息是否有更新
                if 'confVer' in js['data']:
                    logging.debug('heatbeat: conf version updated - %d.', js['data']['confVer'])
                    confUpdate = js['data']['confVer']
                    # 调用配置更新回调函数
                    if cbUpdateConf:
                        cbUpdateConf(confUpdate)

                # 检查音频列表是否有更新
                if 'playVer' in js['data']:
                    logging.debug('heatbeat: play version updated - %d.', js['data']['playVer'])
                    playUpdate = js['data']['playVer']
                    # 调用音频更新回调函数
                    if cbUpdatePlay:
                        cbUpdatePlay(playUpdate)
            ret = True
    except:
        traceback.print_exc()
    finally:
        logging.debug('serverAPI.heartbeat() %s.' %('success' if ret else 'failed'))
        return ret, playUpdate, confUpdate


################################################################################
# 测试程序
if __name__ == '__main__':
    hostName, portNumber, robotId = 'https://ttyoa.com', '8098', 'b827eb319c88'
    init(hostName, portNumber, robotId)

    # 测试登录
    ret, _ = login()
    if ret:
        # 测试获取配置
        ret, vsvrIp, vsvrPort, personList = getConfig()
        if ret:
            print(vsvrIp, vsvrPort, personList)
            # 测试获取医生列表
            ret, doctorList = getDoctorList(personList[0]['personId'])
            if ret:
                print(doctorList)

        # 测试获取音频列表
        ret, mp3List = getMp3List()
        if ret:
            print(mp3List)

        # 测试心跳同步
        ret, playUpdate, confUpdate = heatbeat()
        if ret:
            print(playUpdate, confUpdate)

