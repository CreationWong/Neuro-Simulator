
<template>
  <div>
    <!-- Loading Indicator -->
    <div v-if="isLoading" class="text-center pa-10">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
      <p class="mt-4">{{ t('Loading configuration...') }}</p>
    </div>

    <!-- Main Content -->
    <div v-else>
      <v-tabs v-model="tab" bg-color="primary" class="mb-4 config-tabs" grow>
        <v-tab v-for="group in renderedSchema" :key="group.key" :value="group.key">
          {{ t(group.title) }}
        </v-tab>
      </v-tabs>

      <v-card-actions class="justify-end pa-4">
        <v-btn @click="saveConfig" color="primary" variant="flat" :loading="isSaving">{{ t('Save Configuration') }}</v-btn>
      </v-card-actions>

      <v-window v-model="tab" eager>
        <v-window-item v-for="group in renderedSchema" :key="group.key" :value="group.key">
          <v-card flat class="pa-4">
            <h1 class="text-h4 mb-6">{{ t(group.title) }}</h1>
            <div v-for="prop in group.properties" :key="prop.key">
              <FieldRenderer :group-key="group.isGroup ? group.key : null" :prop-key="prop.key" :prop-schema="prop.schema" />
            </div>

            <!-- Danger Zone for Server Settings -->
            <div v-if="group.key === 'server'" class="mt-10">
              <v-card border color="error" variant="outlined">
                <v-card-title class="text-h5">{{ t('Danger Zone') }}</v-card-title>
                <v-card-text>
                  <p class="mb-4">{{ t('These actions are destructive and cannot be undone.') }}</p>
                  <div class="d-flex flex-wrap ga-4">
                    <v-btn @click="resetConfig" color="error" variant="flat">{{ t('Reset Settings to Default') }}</v-btn>
                    <v-btn @click="resetData" color="error" variant="flat">{{ t('Reset Data to Initial State') }}</v-btn>
                  </div>
                </v-card-text>
              </v-card>
            </div>
          </v-card>
        </v-window-item>
      </v-window>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, defineAsyncComponent } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConfigStore } from '@/stores/config';
import { useConnectionStore } from '@/stores/connection';

const { t } = useI18n();
const FieldRenderer = defineAsyncComponent(() => import('@/components/config/FieldRenderer.vue'));

const configStore = useConfigStore();
const connectionStore = useConnectionStore();

const isLoading = ref(true);
const tab = ref(null);
const isSaving = ref(false);

const renderedSchema = computed(() => {
  const schema = configStore.schema;
  if (!schema || !schema.properties) return [];

  const priorityOrder = ['llm_providers', 'tts_providers', 'neuro', 'chatbot', 'stream', 'server'];
  const schemaKeys = Object.keys(schema.properties);

  schemaKeys.sort((a, b) => {
      const indexA = priorityOrder.indexOf(a);
      const indexB = priorityOrder.indexOf(b);

      if (indexA !== -1 && indexB !== -1) return indexA - indexB;
      if (indexA !== -1) return -1;
      if (indexB !== -1) return 1;
      return a.localeCompare(b);
  });

  return schemaKeys.map(key => {
    const groupSchema = schema.properties[key];
    
    if (groupSchema.$ref) {
      const defName = groupSchema.$ref.split('/').pop() || '';
      const def = schema.$defs?.[defName] || {};
      const props = def.properties || {};
      return {
        key: key,
        title: groupSchema.title || def.title || key.charAt(0).toUpperCase() + key.slice(1),
        isGroup: true,
        properties: Object.keys(props).map(propKey => ({
          key: propKey,
          schema: props[propKey]
        }))
      };
    }
    
    return {
      key: key,
      title: groupSchema.title || key.charAt(0).toUpperCase() + key.slice(1),
      isGroup: false,
      properties: [{ key: key, schema: groupSchema }]
    };
  });
});

async function saveConfig() {
  if (!connectionStore.isConnected) return;
  isSaving.value = true;
  try {
    await connectionStore.sendAdminWsMessage('update_configs', configStore.config);
    console.log('Config saved successfully!');
  } catch (error) {
    console.error("Failed to save config:", error);
  } finally {
    isSaving.value = false;
  }
}

async function resetConfig() {
  if (confirm(t('Are you sure you want to reset all settings to their default values? This cannot be undone.'))) {
    try {
      await connectionStore.sendAdminWsMessage('reset_config_to_defaults', {});
      // Optionally, show a success message to the user
      alert(t('Configuration has been reset. The new settings are now active.'));
    } catch (error) {
      console.error("Failed to reset config:", error);
      alert(t('Failed to reset configuration.'));
    }
  }
}

async function resetData() {
  if (confirm(t('Are you sure you want to reset all data (prompts, memory, etc.) to the initial state? This cannot be undone.'))) {
    try {
      await connectionStore.sendAdminWsMessage('reset_data_directories', {});
      alert(t('Data has been reset. The application is re-initializing with the new data.'));
    } catch (error) {
      console.error("Failed to reset data:", error);
      alert(t('Failed to reset data.'));
    }
  }
}

onMounted(async () => {
  isLoading.value = true;
  try {
    await configStore.fetchSchema();
    await configStore.fetchConfig();
  } finally {
    isLoading.value = false;
  }
});
</script>

<style>
.config-tabs .v-tab {
  text-transform: none !important;
}
</style>
