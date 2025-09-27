import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAgentStore = defineStore('agent', () => {
  const coreMemory = ref<any>({});
  const tempMemory = ref<any[]>([]);
  const initMemory = ref<any>({});
  const agentContext = ref<any>([]); // Can be an array of messages or a string for the prompt

  function handleCoreMemoryUpdate(payload: any) {
    coreMemory.value = payload;
  }

  function handleTempMemoryUpdate(payload: any) {
    tempMemory.value = payload;
  }

  function handleInitMemoryUpdate(payload: any) {
    initMemory.value = payload;
  }

  function handleAgentContextUpdate(payload: any) {
    // The payload can be the array of messages from get_agent_context
    // or the response from get_last_prompt
    if (typeof payload === 'string') {
      agentContext.value = payload;
    } else if (Array.isArray(payload)) {
      agentContext.value = payload;
    } else if (payload.prompt) { // Handling the direct response from get_last_prompt
        agentContext.value = payload.prompt;
    } else if (payload.messages) { // Handling the direct response from get_agent_context
        agentContext.value = payload.messages;
    }
  }

  return {
    coreMemory,
    tempMemory,
    initMemory,
    agentContext,
    handleCoreMemoryUpdate,
    handleTempMemoryUpdate,
    handleInitMemoryUpdate,
    handleAgentContextUpdate,
  };
});
