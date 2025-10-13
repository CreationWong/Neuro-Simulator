<template>
  <div class="agent-view-wrapper">
    <!-- Overlay for external agents -->
    <div v-if="isExternalAgent" class="overlay">
      <div class="overlay-content">
        <v-icon size="x-large" class="mb-4">mdi-link-variant</v-icon>
        <h2 class="text-h5">{{ t('Currently using an external Agent') }}</h2>
        <p class="text-body-1">{{ t('Please go to the corresponding platform for control') }}</p>
      </div>
    </div>

    <!-- Main content (same as before) -->
    <v-card :disabled="isExternalAgent">
      <v-tabs v-model="tab" bg-color="primary" grow>
        <v-tab value="context">{{ t('Conversation') }}</v-tab>
        <v-tab value="memory">{{ t('Memory') }}</v-tab>
        <v-tab value="tools">{{ t('Tools') }}</v-tab>
        <v-tab value="logs">{{ t('Logs') }}</v-tab>
      </v-tabs>

      <v-card-text>
        <v-window v-model="tab">
          <v-window-item value="context">
            <ContextTab />
          </v-window-item>

          <v-window-item value="memory">
            <MemoryTab />
          </v-window-item>

          <v-window-item value="tools">
            <ToolsTab />
          </v-window-item>

          <v-window-item value="logs">
            <LogsTab />
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConfigStore } from '@/stores/config';

// Async components
const ContextTab = defineAsyncComponent(() => import('@/components/agent/ContextTab.vue'));
const MemoryTab = defineAsyncComponent(() => import('@/components/agent/MemoryTab.vue'));
const ToolsTab = defineAsyncComponent(() => import('@/components/agent/ToolsTab.vue'));
const LogsTab = defineAsyncComponent(() => import('@/components/agent/LogsTab.vue'));

const { t } = useI18n();
const configStore = useConfigStore();
const tab = ref('context');

const isExternalAgent = computed(() => {
  return configStore.config?.agent_type && configStore.config.agent_type !== 'builtin';
});
</script>

<style scoped>
.agent-view-wrapper {
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