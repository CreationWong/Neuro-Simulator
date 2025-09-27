import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useToolsStore = defineStore('tools', () => {
  const availableTools = ref<any[]>([]);
  const allocations = ref<any>({});

  function handleAvailableToolsUpdate(tools: any[]) {
    availableTools.value = tools;
  }

  function handleAllocationsUpdate(newAllocations: any) {
    console.log('DEBUG: handleAllocationsUpdate received:', newAllocations);
    allocations.value = newAllocations;
  }

  return {
    availableTools,
    allocations,
    handleAvailableToolsUpdate,
    handleAllocationsUpdate,
  };
});
