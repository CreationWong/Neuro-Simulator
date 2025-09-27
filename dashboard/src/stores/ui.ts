import { defineStore } from 'pinia';
import { ref } from 'vue';

interface DialogPromise {
  resolve: (value: boolean) => void;
}

export const useUiStore = defineStore('ui', () => {
  const isConfirmDialogVisible = ref(false);
  const confirmDialogMessage = ref('');
  let dialogPromise = ref<DialogPromise | null>(null);

  function showConfirm(message: string): Promise<boolean> {
    confirmDialogMessage.value = message;
    isConfirmDialogVisible.value = true;
    return new Promise((resolve) => {
      dialogPromise.value = { resolve };
    });
  }

  function handleConfirm(result: boolean) {
    if (dialogPromise.value) {
      dialogPromise.value.resolve(result);
    }
    isConfirmDialogVisible.value = false;
  }

  return {
    isConfirmDialogVisible,
    confirmDialogMessage,
    showConfirm,
    handleConfirm,
  };
});
