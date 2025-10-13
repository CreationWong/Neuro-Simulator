<template>
  <v-card>
    <v-card-title>{{ t('Stream Control') }}</v-card-title>
    <v-card-text>
      <div class="stream-status">
        <p>{{ t('Current Status') }}: 
          <v-chip :color="streamStore.isRunning ? 'green' : 'red'" dark>
            {{ streamStore.isRunning ? t('Running') : t('Stopped') }}
          </v-chip>
        </p>
      </div>
      <div class="control-buttons">
        <v-btn color="primary" @click="startStream" :loading="loading.start">{{ t('Start Stream') }}</v-btn>
        <v-btn color="error" @click="stopStream" :loading="loading.stop">{{ t('Stop Stream') }}</v-btn>
        <v-btn color="warning" @click="restartStream" :loading="loading.restart">{{ t('Restart Stream') }}</v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useStreamStore } from '@/stores/stream';
import { useConnectionStore } from '@/stores/connection';

const { t } = useI18n();
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