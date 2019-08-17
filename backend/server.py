#!/usr/bin/python
# -*- coding: utf8 -*-

from flask import Flask, request, jsonify, render_template
from data_access import device, server, wifi, bracelet, settings, test_func
import os
import datetime
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity

basedir = os.path.dirname(os.path.abspath(__file__))
print(basedir)
app = Flask(__name__,static_url_path='', static_folder=os.path.join(basedir, 'static'), template_folder=os.path.join(basedir, 'static'))
app.config['JWT_SECRET_KEY'] = 'random_sect_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)

jwt = JWTManager(app)

builtinUser = {
    'username': 'admin',
    'password': 'onlyforrobot'
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/login', methods=['post'])
def login():
    login_model = request.json
    # check for fields validation
    if not('username' in login_model and 'password' in login_model):
        return 'username or password is missing', 400
    username = login_model['username']
    password = login_model['password']

    if username == builtinUser['username'] and password == builtinUser['password']:
        access_token = create_access_token(identity=login_model)
        res = {
            'token': access_token
        }
        return jsonify(res)
    return 'Not Authorized', 401


@app.route('/api/device')
@jwt_required
def get_device_info():
    status, result = device.get_device_info()
    if status:
        return jsonify(result), 200
    else:
        return result, 400


@app.route('/api/restart', methods=['post'])
@jwt_required
def restart_server():
    status, result = device.restart_server()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/server')
@jwt_required
def get_server_info():
    status, result = server.get_server_info()
    if status:
        return jsonify(result)
    else:
        return result, 400


@app.route('/api/server', methods=['post'])
@jwt_required
def update_server_info():
    server_info = request.json
    status, result = server.update_server_info(server_info)
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/wifi')
@jwt_required
def get_wifi_info():
    status, result = wifi.get_wifi_info()
    if status:
        return jsonify(result), 200
    else:
        return result, 400


@app.route('/api/wifi_list')
@jwt_required
def get_available_wifi_list():
    status, result = wifi.get_available_wifi_list()
    if status:
        return jsonify(result), 200
    else:
        return result, 400


@app.route('/api/wifi', methods=['post'])
@jwt_required
def update_wifi_info():
    wifi_info = request.json
    status, result = wifi.update_wifi_info(wifi_info)
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/bracelet_list')
@jwt_required
def get_configured_bracelet_list():
    status, bracelet_list = bracelet.get_configured_bracelet_list()
    if status:
        return jsonify(bracelet_list)
    else:
        return


@app.route('/api/bracelet/<int:bracelet_id>')
@jwt_required
def get_bracelet_info(bracelet_id):
    status, result = bracelet.get_bracelet_info(bracelet_id)
    if status:
        return jsonify(result), 200
    else:
        return result, 400


@app.route('/api/bracelet/<int:bracelet_id>', methods=['put'])
@jwt_required
def update_bracelet_info(bracelet_id):
    bracelet_info = request.json
    if not('mac' in bracelet_info):
        return 'mac field is missing', 400
    status, result = bracelet.update_bracelet_info(bracelet_id, bracelet_info['mac'])
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/bracelet', methods=['post'])
@jwt_required
def add_bracelet():
    bracelet_info = request.json
    if not ('mac' in bracelet_info):
        return 'mac field is missing', 400
    status, result = bracelet.add_bracelet(bracelet_info['mac'])
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/bracelet/<int:bracelet_id>', methods=['delete'])
@jwt_required
def delete_bracelet(bracelet_id):
    status, result = bracelet.delete_bracelet(bracelet_id)
    if status:
        return result, 200
    else:
        return result, 404


@app.route('/api/scan_bracelet_list')
@jwt_required
def get_scanned_bracelet_list():
    status, result = bracelet.get_scanned_bracelet_list()
    if status:
        return jsonify(result), 200
    else:
        return result, 400


@app.route('/api/settings')
@jwt_required
def get_settings():
    status, result = settings.get_settings()
    if status:
        return jsonify(result), 200
    else:
        return result, 400


@app.route('/api/settings', methods=['put'])
@jwt_required
def update_settings():
    s = request.json
    status, result = settings.update_settings(s)
    if status:
        return result, 200
    else:
        return result, 400


# test functionalities
@app.route('/api/enter_radio_test_env', methods=['post'])
@jwt_required
def enter_radio_test_env():
    status, result = test_func.enter_radio_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/exit_radio_test_env', methods=['post'])
@jwt_required
def exit_radio_test_env():
    status, result = test_func.exit_radio_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/start_test_radio', methods=['post'])
@jwt_required
def start_test_radio():
    status, result = test_func.start_test_radio()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/stop_test_radio', methods=['post'])
@jwt_required
def stop_test_radio():
    status, result = test_func.stop_test_radio()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/enter_audio_test_env', methods=['post'])
@jwt_required
def enter_audio_test_env():
    status, result = test_func.enter_audio_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/exit_audio_test_env', methods=['post'])
@jwt_required
def exit_audio_test_env():
    status, result = test_func.exit_audio_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/start_recording_audio', methods=['post'])
@jwt_required
def start_recording_audio():
    status, result = test_func.start_recording_audio()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/stop_recording_audio', methods=['post'])
@jwt_required
def stop_recording_audio():
    status, result = test_func.stop_recording_audio()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/play_recorded_audio', methods=['post'])
@jwt_required
def play_recorded_audio():
    status, result = test_func.play_recorded_audio()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/enter_monitor_test_env', methods=['post'])
@jwt_required
def enter_monitor_test_env():
    status, result = test_func.enter_monitor_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/exit_monitor_test_env', methods=['post'])
@jwt_required
def exit_monitor_test_env():
    status, result = test_func.exit_monitor_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/start_test_monitor', methods=['post'])
@jwt_required
def start_test_monitor():
    status, result = test_func.start_test_monitor()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/stop_test_monitor', methods=['post'])
@jwt_required
def stop_test_monitor():
    status, result = test_func.stop_test_monitor()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/enter_camera_test_env', methods=['post'])
@jwt_required
def enter_camera_test_env():
    status, result = test_func.enter_camera_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/exit_camera_test_env', methods=['post'])
@jwt_required
def exit_camera_test_env():
    status, result = test_func.exit_camera_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/capture_camera', methods=['post'])
@jwt_required
def capture_camera():
    status, result = test_func.capture_camera()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/enter_keypad_test_env', methods=['post'])
@jwt_required
def enter_keypad_test_env():
    status, result = test_func.enter_keypad_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/exit_keypad_test_env', methods=['post'])
@jwt_required
def exit_keypad_test_env():
    status, result = test_func.exit_keypad_test_env()
    if status:
        return result, 200
    else:
        return result, 400


@app.route('/api/keypad')
@jwt_required
def get_keypad_strings():
    status, result = test_func.get_keypad_strings()
    if status:
        return jsonify(result), 200
    else:
        return result, 400


if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 9999)
