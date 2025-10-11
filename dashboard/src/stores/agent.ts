import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAgentStore = defineStore('agent', () => {
  const coreMemory = ref<any>({});
  const tempMemory = ref<any[]>([]);
  const initMemory = ref<any>({});
  const agentHistory = ref<any[]>([]);
  const agentPrompt = ref<string>('');

  function handleCoreMemoryUpdate(payload: any) {
    coreMemory.value = payload;
  }

  function handleTempMemoryUpdate(payload: any) {
    tempMemory.value = payload;
  }

  function handleInitMemoryUpdate(payload: any) {
    initMemory.value = payload;
  }

  function handleAgentHistoryUpdate(payload: any[]) {
    agentHistory.value = payload;
  }

  function setAgentPrompt(prompt: string) {
    agentPrompt.value = prompt;
  }

  return {
    coreMemory,
    tempMemory,
    initMemory,
    agentHistory,
    agentPrompt,
    handleCoreMemoryUpdate,
    handleTempMemoryUpdate,
    handleInitMemoryUpdate,
    handleAgentHistoryUpdate,
    setAgentPrompt,
  };
});
