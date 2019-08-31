import axios from 'axios';

export default class DeviceQuery {
  static getDeviceInfo() {
    return axios.get('/api/device').then(res => res.data);
  }

  static restartServer() {
    return axios.post('/api/restart').then(res => res.data);
  }

  static shutdownServer() {
    return axios.post('/api/shutdown').then(res => res.data);
  }

  static mimicDebug() {
    return axios.post('/api/mimic_debug').then(res => res.data);
  }
}
