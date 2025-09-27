import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useConnectionStore } from './connection';

export const useConfigStore = defineStore('config', () => {
  const config = ref<any>({});
  const schema = ref<any>({}); // To hold the settings schema

  function handleConfigUpdate(payload: any) {
    config.value = payload;
  }

  async function fetchConfig() {
    const connectionStore = useConnectionStore();
    if (!connectionStore.isConnected) return;
    try {
      const latestConfig = await connectionStore.sendAdminWsMessage('get_configs');
      config.value = latestConfig;
    } catch (error) {
      console.error("Failed to fetch config:", error);
    }
  }

  async function fetchSchema() {
    const connectionStore = useConnectionStore();
    if (!connectionStore.isConnected) return;
    try {
      const settingsSchema = await connectionStore.sendAdminWsMessage('get_settings_schema');
      schema.value = settingsSchema;
    } catch (error) {
      console.error("Failed to fetch schema:", error);
    }
  }

  return {
    config,
    schema,
    handleConfigUpdate,
    fetchConfig,
    fetchSchema,
  };
});
