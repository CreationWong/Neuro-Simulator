<template>
  <v-container>
    <v-card class="mx-auto" max-width="500">
      <v-card-title class="text-h6 font-weight-regular justify-space-between">
        <span>连接设置</span>
      </v-card-title>

      <v-window v-model="step">
        <v-window-item :value="1">
          <v-card-text>
            <v-text-field
              v-model="connectionStore.backendUrl"
              label="后端地址"
              placeholder="http://localhost:8000"
              :disabled="connectionStore.isConnected"
            ></v-text-field>
            <v-text-field
              v-model="connectionStore.password"
              label="访问密码 (可选)"
              type="password"
              :disabled="connectionStore.isConnected"
            ></v-text-field>
            <span class="text-caption text-grey-darken-1">
              {{ connectionStore.statusText }}
            </span>
          </v-card-text>
        </v-window-item>
      </v-window>

      <v-divider></v-divider>

      <v-card-actions>
        <v-btn
          v-if="!connectionStore.isConnected"
          color="primary"
          variant="flat"
          @click="handleConnect"
          :loading="loading"
        >
          连接
        </v-btn>
        <v-btn
          v-else
          color="red"
          variant="flat"
          @click="handleDisconnect"
        >
          断开连接
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useConnectionStore } from '@/stores/connection';
import { useRouter } from 'vue-router';

const connectionStore = useConnectionStore();
const router = useRouter();
const loading = ref(false);
const step = ref(1); // For the v-window, can be used for multi-step forms later

async function handleConnect() {
  if (!connectionStore.backendUrl) {
    console.error('Backend URL is required.');
    return;
  }
  loading.value = true;
  try {
    const success = await connectionStore.connectToBackend();
    if (success) {
      router.push('/control');
    }
  } catch (error) {
    console.error('Failed to connect:', error);
  } finally {
    loading.value = false;
  }
}

async function handleDisconnect() {
  await connectionStore.disconnectFromBackend();
}

</script>
