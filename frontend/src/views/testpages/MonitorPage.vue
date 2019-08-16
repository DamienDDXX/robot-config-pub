<template>
  <div class="monitor-page">
    <h1>测试液晶屏</h1>
    <div class="operations">
      <el-button type="primary" @click="onTestBtnClick" icon="el-icon-monitor" :loading="isTesting">测试</el-button>
      <el-button v-if="false" type="danger" @click="onStopBtnClick">停止</el-button>
    </div>
  </div>
</template>

<script>
import testQuery from '@/rest/testQuery';

export default {
  data() {
    return {
      isTesting: false
    };
  },
  methods: {
    async onStopBtnClick() {
      try {
        await testQuery.stopTestMonitor();
        this.$message({
          message: '测试液晶屏已停止',
          type: 'success'
        });
      } catch {
        this.$message({
          message: '测试液晶屏停止失败',
          type: 'error'
        });
      }
    },
    async onTestBtnClick() {
      try {
        this.isTesting = true;
        await testQuery.startTestMonitor();
        this.isTesting = false;
        this.$message({
          message: '测试液晶屏成功',
          type: 'success'
        });
      } catch {
        this.isTesting = false;
        this.$message({
          message: '测试液晶屏失败',
          type: 'error'
        });
      }
    }
  },
  created() {
    testQuery.enterTestEnv('monitor');
  },
  beforeDestroy() {
    testQuery.exitTestEnv('monitor');
  }
};
</script>

<style lang="scss" scoped>
.monitor-page {
  .operations {
    margin-top: 48px;
  }
}
</style>
