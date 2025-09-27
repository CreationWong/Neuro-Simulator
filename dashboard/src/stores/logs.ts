import { defineStore } from 'pinia';
import { ref } from 'vue';

const MAX_LOGS = 1000;

export const useLogStore = defineStore('logs', () => {
  const serverLogs = ref<string[]>([]);
  const agentLogs = ref<string[]>([]);

  function addServerLog(log: string) {
    serverLogs.value.push(log);
    if (serverLogs.value.length > MAX_LOGS) {
      serverLogs.value.shift();
    }
  }

  function addAgentLog(log: string) {
    agentLogs.value.push(log);
    if (agentLogs.value.length > MAX_LOGS) {
      agentLogs.value.shift();
    }
  }

  return {
    serverLogs,
    agentLogs,
    addServerLog,
    addAgentLog,
  };
});