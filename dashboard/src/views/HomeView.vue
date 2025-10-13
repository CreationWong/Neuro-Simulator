<template>
  <div class="home-view-wrapper">
    <div v-if="connectionStore.isIntegrated" class="overlay">
      <div class="overlay-content">
        <v-icon size="x-large" class="mb-4">mdi-server-network</v-icon>
        <h2 class="text-h5">{{ t('Automatically connected to the server') }}</h2>
        <p class="text-body-1">{{ t('No manual connection required for the built-in panel, please refresh if accidentally disconnected') }}</p>
      </div>
    </div>

    <v-card class="mx-auto" max-width="500" :disabled="connectionStore.isIntegrated">
      <v-card-title class="text-h6 font-weight-regular justify-space-between">
        <span>{{ t('Connection Settings') }}</span>
      </v-card-title>

      <v-window v-model="step">
        <v-window-item :value="1">
          <v-card-text>
            <v-text-field
              v-model="connectionStore.backendUrl"
              :label="t('Backend URL')"
              placeholder="http://localhost:8000"
              :disabled="connectionStore.isConnected"
            ></v-text-field>
            <v-text-field
              v-model="connectionStore.password"
              :label="t('Access Password (optional)')"
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
          {{ t('Connect') }}
        </v-btn>
        <v-btn
          v-else
          color="red"
          variant="flat"
          @click="handleDisconnect"
        >
          {{ t('Disconnect') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConnectionStore } from '@/stores/connection';

const { t } = useI18n();
const connectionStore = useConnectionStore();
const loading = ref(false);
const step = ref(1);

async function handleConnect() {
  if (!connectionStore.backendUrl) {
    console.error('Backend URL is required.');
    return;
  }
  loading.value = true;
  try {
    await connectionStore.connectToBackend();
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

<style scoped>
.home-view-wrapper {
  position: relative;
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.7);
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px; /* Match v-card's default border-radius */
}

.overlay-content {
  text-align: center;
  padding: 20px;
  background-color: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
</style>
