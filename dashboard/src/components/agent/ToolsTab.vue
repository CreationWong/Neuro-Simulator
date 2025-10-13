<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <div class="d-flex mb-4">
          <v-btn @click="reloadTools" class="mr-2">{{ t('Reload Tools') }}</v-btn>
          <v-btn @click="handleSaveAllocations" color="primary">{{ t('Save Allocations') }}</v-btn>
        </div>
        <p class="text-caption">{{ t('Here you can assign available tool tags to Agents. The Neuro Agent is responsible for interacting with the audience, while the Memory Agent is responsible for organizing memories in the background.') }}</p>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card variant="outlined">
          <v-card-title>{{ t('All Available Tools') }}</v-card-title>
          <v-card-text>
            <v-table density="compact">
              <thead>
                <tr>
                  <th class="text-left">{{ t('Tool Name') }}</th>
                  <th class="text-left">{{ t('Description') }}</th>
                  <th class="text-center">{{ t('Neuro Agent') }}</th>
                  <th class="text-center">{{ t('Memory Agent') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tool in toolsStore.availableTools" :key="tool.name">
                  <td>{{ tool.name }}</td>
                  <td>{{ tool.description }}</td>
                  <td class="text-center">
                    <v-checkbox-btn v-model="editableAllocations.neuro_agent" :value="tool.name" hide-details></v-checkbox-btn>
                  </td>
                  <td class="text-center">
                    <v-checkbox-btn v-model="editableAllocations.memory_manager" :value="tool.name" hide-details></v-checkbox-btn>
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col md="6" cols="12">
        <v-card variant="outlined">
          <v-card-title>{{ t('Neuro Agent Toolset') }}</v-card-title>
          <v-card-text>
             <v-chip-group column>
              <v-chip
                v-for="toolName in toolsStore.allocations.neuro_agent"
                :key="toolName"
              >
                {{ toolName }}
              </v-chip>
            </v-chip-group>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col md="6" cols="12">
        <v-card variant="outlined">
          <v-card-title>{{ t('Memory Agent Toolset') }}</v-card-title>
          <v-card-text>
            <v-chip-group column>
              <v-chip
                v-for="toolName in toolsStore.allocations.memory_manager"
                :key="toolName"
              >
                {{ toolName }}
              </v-chip>
            </v-chip-group>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

  </v-container>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToolsStore } from '@/stores/tools';
import { useConnectionStore } from '@/stores/connection';

const { t } = useI18n();
const toolsStore = useToolsStore();
const connectionStore = useConnectionStore();

// Local state for editing allocations
const editableAllocations = ref<{ neuro_agent: string[], memory_manager: string[] }>({ neuro_agent: [], memory_manager: [] });

// Watch for changes from the store and update the local editable state
watch(() => toolsStore.allocations, (newAllocations) => {
  // Deep copy to prevent direct mutation of the store's state
  editableAllocations.value = JSON.parse(JSON.stringify(newAllocations || { neuro_agent: [], memory_manager: [] }));
}, { deep: true, immediate: true });

async function handleSaveAllocations() {
  if (!connectionStore.isConnected) return;
  try {
    await connectionStore.sendAdminWsMessage('set_agent_tool_allocations', { allocations: editableAllocations.value });
    // Optionally, show a success toast/snackbar
    console.log('Tool allocations saved successfully!');
  } catch (error) {
    console.error("Failed to save allocations:", error);
    // Optionally, show an error toast/snackbar
  }
}

async function reloadTools() {
  if (!connectionStore.isConnected) return;
  try {
    // This will trigger the backend to send updated tool information
    await connectionStore.sendAdminWsMessage('reload_tools');
  } catch (error) {
    console.error("Failed to reload tools:", error);
  }
}

async function fetchInitialData() {
  if (!connectionStore.isConnected) return;
  try {
    const [toolsResponse, allocationsResponse] = await Promise.all([
      connectionStore.sendAdminWsMessage('get_all_tools'),
      connectionStore.sendAdminWsMessage('get_agent_tool_allocations'),
    ]);
    console.log('DEBUG: toolsResponse:', toolsResponse);
    console.log('DEBUG: allocationsResponse:', allocationsResponse);
    toolsStore.handleAvailableToolsUpdate(toolsResponse.tools);
    toolsStore.handleAllocationsUpdate(allocationsResponse.allocations);
  } catch (error) {
    console.error("Failed to fetch tools initial data:", error);
  }
}

onMounted(() => {
  fetchInitialData();
});
</script>
