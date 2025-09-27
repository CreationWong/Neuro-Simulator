import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useStreamStore = defineStore('stream', () => {
  const isRunning = ref(false);

  function handleStreamStatusUpdate(payload: { is_running: boolean }) {
    isRunning.value = payload.is_running;
  }

  return {
    isRunning,
    handleStreamStatusUpdate,
  };
});