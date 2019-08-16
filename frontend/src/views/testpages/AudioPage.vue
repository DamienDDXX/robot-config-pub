<template>
  <div class="audio-page">
    <h1>测试麦克风</h1>
    <div class="operations">
      <el-button type="primary" @click="onTestBtnClick" icon="el-icon-microphone" :loading="isRecording">录制</el-button>
      <el-button v-if="false" type="danger" @click="onStopBtnClick">停止</el-button>
      <el-button type="success" @click="onPlayBtnClick" icon="el-icon-video-play" :loading="isPlaying">播放</el-button>
    </div>
  </div>
</template>

<script>
import testQuery from '@/rest/testQuery';

export default {
  data() {
    return {
      isRecording: false,
      isPlaying: false
    };
  },
  methods: {
    async onStopBtnClick() {
      try {
        await testQuery.stopRecordingAudio();
        this.$message({
          message: '已停止录制',
          type: 'success'
        });
      } catch {
        this.$message({
          message: '停止失败',
          type: 'error'
        });
      }
    },
    async onTestBtnClick() {
      try {
        this.isRecording = true;
        await testQuery.startRecordingAudio();
        this.isRecording = false;
        this.$message({
          message: '录制成功',
          type: 'success'
        });
      } catch {
        this.isRecording = false;
        this.$message({
          message: '录制失败',
          type: 'error'
        });
      }
    },
    async onPlayBtnClick() {
      try {
        this.isPlaying = true;
        await testQuery.playRecordedAudio();
        this.isPlaying = false;
        this.$message({
          message: '播放成功',
          type: 'success'
        });
      } catch {
        this.isPlaying = false;
        this.$message({
          message: '播放失败',
          type: 'error'
        });
      }
    }
  },
  created() {
    testQuery.enterTestEnv('audio');
  },
  beforeDestroy() {
    testQuery.exitTestEnv('audio');
  }
};
</script>

<style lang="scss" scoped>
.audio-page {
  .operations {
    margin-top: 48px;
  }
}
</style>
