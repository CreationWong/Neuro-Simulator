<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-switch
        v-model="isPromptMode"
        label="上下文模式"
        color="primary"
        hide-details
      ></v-switch>
    </div>

    <div v-if="isPromptMode" class="context-prompt-view">
      <pre>{{ agentStore.agentContext }}</pre>
    </div>

    <div v-else class="context-conversation-view">
       <div v-for="(msg, index) in agentStore.agentContext" :key="index" class="message-item">
         <!-- Detailed message rendering will go here -->
         <p><strong>{{ msg.role }}:</strong> {{ msg.content }}</p>
       </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useAgentStore } from '@/stores/agent';
import { useConnectionStore } from '@/stores/connection';

const isPromptMode = ref(false);
const agentStore = useAgentStore();
const connectionStore = useConnectionStore();

async function refreshContext() {
  if (!connectionStore.isConnected) return;

  if (isPromptMode.value) {
    try {
      const response = await connectionStore.sendAdminWsMessage('get_last_prompt');
      // The store will be updated by the websocket message handler, 
      // but we can also update it directly here for immediate feedback.
      agentStore.agentContext = response.prompt;
    } catch (error) {
      console.error('获取最新Prompt失败:', error);
      agentStore.agentContext = `获取提示词失败: ${error}`;
    }
  } else {
    try {
      const contextMessages = await connectionStore.sendAdminWsMessage('get_agent_context');
      agentStore.agentContext = contextMessages;
    } catch (error) {
      console.error('获取上下文失败:', error);
    }
  }
}

// When the switch is toggled, refresh the context
watch(isPromptMode, refreshContext);

// Initial load
refreshContext();

</script>

<style scoped>
.context-prompt-view pre {
  background-color: #1E1E1E;
  color: #D4D4D4;
  font-family: 'Courier New', Courier, monospace;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 70vh;
  overflow-y: auto;
}

.message-item {
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;
}
</style>
