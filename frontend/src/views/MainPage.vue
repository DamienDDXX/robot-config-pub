<template>
  <div class="main-page">
    <navigation class="top-bar"></navigation>
    <main class="main">
      <div class="row device-info">
        <span class="sn">设备序列号： {{seriesNumber}}</span>
        <el-button type="danger" class="restart" icon="el-icon-refresh-left" @click="onRestartBtnClick" :loading="isRestarting">系统重启</el-button>
        <el-button type="danger" class="shutdown" @click="onShutdownBtnClick" :loading="isShutingDown">关闭系统</el-button>
        <el-button type="primary" class="debug" @click="onMimicDebugBtnClick" :loading="isDebuging">模拟调试</el-button>
      </div>
      <div class="row sections">
        <div class="section" v-for="(section, index) in sections" :key="index">
          <div class="row title-container">
            <eva-icon :name="section.icon" fill="#00e"></eva-icon>
            <router-link class="title link" :to="{name: section.routeName}">{{section.title}}</router-link>
          </div>          
          <div class="desc">
            {{section.desc}}
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import Navigation from '@/components/Navigation';
import deviceQuery from '@/rest/deviceQuery';

export default {
  data() {
    return {
      isRestarting: false,
      isShutingDown: false,
      isDebuging: false,
      seriesNumber: '',
      sections: [
        {
          title: '系统服务器',
          desc: '配置、查看和修改服务器地址……',
          icon: 'grid',
          routeName: 'server-page'
        },
        {
          title: '无线网络',
          desc: '扫描、查看和修改无线网络连接……',
          icon: 'wifi',
          routeName: 'wifi-page'
        },
        {
          title: '蓝牙手环',
          desc: '扫描、连接和管理蓝牙手环……',
          icon: 'bluetooth',
          routeName: 'bracelet-page'
        },
        {
          title: '其它设置',
          desc: '设置摄像头分辨率、位置坐标……',
          icon: 'settings-2',
          routeName: 'settings-page'
        },
        {
          title: '功能测试',
          desc: '测试扬声器、麦克风、液晶屏、摄像头和按键……',
          icon: 'smartphone',
          routeName: 'test-page'
        }
      ]
    };
  },
  methods: {
    async onRestartBtnClick() {
      try {
        this.isRestarting = true;
        await deviceQuery.restartServer();
        this.isRestarting = false;
        this.$message({
          message: '重启成功',
          type: 'success'
        });
      } catch {
        this.isRestarting = false;
        this.$message({
          message: '重启失败',
          type: 'error'
        });
      }
    },
    async onShutdownBtnClick() {
      try {
        this.isShutingDown = true;
        await deviceQuery.shutdownServer();
        this.isShutingDown = false;
        this.$message({
          message: '关闭系统成功',
          type: 'success'
        });
      } catch {
        this.isShutingDown = false;
        this.$message({
          message: '关闭系统失败',
          type: 'error'
        });
      }
    }, 
    async onMimicDebugBtnClick() {
      try {
        this.isDebuging = true;
        await deviceQuery.shutdownServer();
        this.isDebuging = false;
        this.$message({
          message: '模拟调试成功',
          type: 'success'
        });
      } catch {
        this.isDebuging = false;
        this.$message({
          message: '模拟调试失败',
          type: 'error'
        });
      }
    }
  },
  async created() {
    try {
      const deviceInfo = await deviceQuery.getDeviceInfo();
      this.seriesNumber = deviceInfo.seriesNumber;
    } catch {
      this.$message({
        message: '获取设备序列号失败',
        type: 'error'
      });
    }
  },
  components: {
    Navigation
  }
};
</script>

<style lang="scss" scoped>
.main-page {
  width: 100%;
  height: 100%;
  .top-bar {
    width: 100%;
    height: 64px;
  }
  .main {
    overflow: auto;
    width: 100%;
    height: calc(100% - 64px);
    padding: 24px;
    margin:0 auto;
    .device-info {
      flex-wrap: wrap;
      align-items: center;
      margin-top:48px;
      margin-left: 24px;
      font-size: 28px;
      font-weight: bold;
      .sn {
        margin-right:24px;
        margin-bottom: 16px;
      }
      .restart, .shutdown, .debug {
        margin-bottom: 16px;
      }
    }
    .sections {
      flex-wrap: wrap;  
      margin-top: 48px;    
      .section {
        width: 300px;
        padding: 24px;
        border-radius: 4px;
        .title-container {
          font-size: 18px;
          color: #00e;
          .title {
            margin-left: 12px;
          }
          .link {
            color: #00e;
            text-decoration: none;
            &:hover {
              color: #0055ff;
            }
          }
        }
        .desc {
          margin-top: 14px;
          font-size: 14px;
          height: 60px;
          color: #666;
          line-height: 20px;
        }
      }
      
    }
  }
}
</style>
