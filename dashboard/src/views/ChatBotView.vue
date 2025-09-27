<template>
  <div class="chatbot-view-wrapper">
    <div class="overlay">
      <div class="overlay-content">
        <v-icon size="x-large" class="mb-4">mdi-dev-to</v-icon>
        <h2 class="text-h5">Chatbot 控制开发中</h2>
        <p class="text-body-1">后端 API 尚未实现</p>
      </div>
    </div>
    
    <!-- The entire AgentView content is duplicated here -->
    <v-card>
      <v-tabs v-model="tab" bg-color="primary" grow>
        <v-tab value="context">对话</v-tab>
        <v-tab value="memory">记忆</v-tab>
        <v-tab value="tools">工具</v-tab>
        <v-tab value="logs">日志</v-tab>
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
import { ref, defineAsyncComponent } from 'vue';

// Re-using the same components from the Agent page
const ContextTab = defineAsyncComponent(() => import('@/components/agent/ContextTab.vue'));
const MemoryTab = defineAsyncComponent(() => import('@/components/agent/MemoryTab.vue'));
const ToolsTab = defineAsyncComponent(() => import('@/components/agent/ToolsTab.vue'));
const LogsTab = defineAsyncComponent(() => import('@/components/agent/LogsTab.vue'));

const tab = ref('context');
</script>

<style scoped>
.chatbot-view-wrapper {
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
  border-radius: inherit; /* Inherit border-radius from parent card if any */
}

.overlay-content {
  text-align: center;
  padding: 20px;
  background-color: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
</style>
