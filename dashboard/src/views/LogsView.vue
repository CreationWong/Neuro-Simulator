<template>
  <v-card>
    <v-card-title>Server 日志</v-card-title>
    <v-card-text>
      <div ref="logsContainer" class="logs-output">
        <div v-for="(log, index) in logStore.serverLogs" :key="`server-${index}`" class="log-entry">
          {{ log }}
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { useLogStore } from '@/stores/logs';

const logStore = useLogStore();
const logsContainer = ref<HTMLElement | null>(null);

// Watch for new logs and scroll to the bottom
watch(
  () => logStore.serverLogs.length,
  async () => {
    await nextTick(); // Wait for the DOM to update
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
    }
  },
  { deep: true } // Use deep watch just in case
);
</script>

<style scoped>
.logs-output {
  background-color: #1E1E1E;
  color: #D4D4D4;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9rem;
  white-space: pre-wrap;
  height: 75vh; /* Set a good height */
  overflow-y: auto;
  padding: 16px;
  border-radius: 4px;
}

.log-entry {
  margin-bottom: 4px;
}
</style>