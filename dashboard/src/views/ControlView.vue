<template>
  <v-card>
    <v-card-title>直播控制</v-card-title>
    <v-card-text>
      <div class="stream-status">
        <p>当前状态: 
          <v-chip :color="streamStore.isRunning ? 'green' : 'red'" dark>
            {{ streamStore.isRunning ? '运行中' : '已停止' }}
          </v-chip>
        </p>
      </div>
      <div class="control-buttons">
        <v-btn color="primary" @click="startStream" :loading="loading.start">开始直播</v-btn>
        <v-btn color="error" @click="stopStream" :loading="loading.stop">停止直播</v-btn>
        <v-btn color="warning" @click="restartStream" :loading="loading.restart">重启直播</v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useStreamStore } from '@/stores/stream';
import { useConnectionStore } from '@/stores/connection';

const streamStore = useStreamStore();
const connectionStore = useConnectionStore();

const loading = reactive({
  start: false,
  stop: false,
  restart: false,
});

async function startStream() {
  loading.start = true;
  try {
    await connectionStore.sendAdminWsMessage('start_stream');
  } catch (e) {
    console.error(e);
    // Show toast/snackbar with error
  } finally {
    loading.start = false;
  }
}

async function stopStream() {
  loading.stop = true;
  try {
    await connectionStore.sendAdminWsMessage('stop_stream');
  } catch (e) {
    console.error(e);
  } finally {
    loading.stop = false;
  }
}

async function restartStream() {
  loading.restart = true;
  try {
    await connectionStore.sendAdminWsMessage('restart_stream');
  } catch (e) {
    console.error(e);
  } finally {
    loading.restart = false;
  }
}
</script>

<style scoped>
.stream-status {
  margin-bottom: 20px;
}
.control-buttons {
  display: flex;
  gap: 16px;
}
</style>