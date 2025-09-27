<template>
  <div>
    <v-expansion-panels variant="inset" class="my-4">
      <v-expansion-panel title="初始化记忆 (Init Memory)">
        <v-expansion-panel-text>
          <div class="d-flex mb-4">
            <v-btn @click="refreshInitMemory" class="mr-2">刷新</v-btn>
            <v-btn @click="openInitMemoryDialog()" color="primary">添加</v-btn>
          </div>
          <v-list lines="one" v-if="Object.keys(agentStore.initMemory).length > 0">
            <v-list-item
              v-for="(value, key) in agentStore.initMemory"
              :key="key"
              :title="key"
            >
              <v-list-item-subtitle class="value-display"><pre>{{ value }}</pre></v-list-item-subtitle>
              <template v-slot:append>
                <v-btn @click="openInitMemoryDialog(key, value)" icon="mdi-pencil" size="x-small" variant="text"></v-btn>
                <v-btn @click="deleteInitMemoryItem(key as string)" icon="mdi-delete" size="x-small" variant="text" color="error"></v-btn>
              </template>
            </v-list-item>
          </v-list>
          <p v-else>没有初始化记忆。</p>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel title="临时记忆 (Temp Memory)">
        <v-expansion-panel-text>
          <div class="d-flex mb-4">
            <v-btn @click="refreshTempMemory" class="mr-2">刷新</v-btn>
            <v-btn @click="isAddTempMemoryDialogVisible = true" color="primary" class="mr-2">添加</v-btn>
            <v-btn @click="clearTempMemory" color="error">清空</v-btn>
          </div>
          <v-list lines="one" v-if="agentStore.tempMemory.length > 0">
            <v-list-item
              v-for="item in agentStore.tempMemory"
              :key="item.id"
              :title="`[${item.role}] ${item.content || item.text}`"
              :subtitle="new Date(item.timestamp).toLocaleString()">
              <template v-slot:append>
                <v-btn @click="deleteTempMemoryItem(item.id)" icon="mdi-delete" size="x-small" variant="text" color="error"></v-btn>
              </template>
            </v-list-item>
          </v-list>
          <p v-else>没有临时记忆。</p>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel title="核心记忆 (Core Memory)">
        <v-expansion-panel-text>
          <div class="d-flex mb-4">
            <v-btn @click="refreshCoreMemory" class="mr-2">刷新</v-btn>
            <v-btn @click="openCoreMemoryDialog()" color="primary">添加记忆块</v-btn>
          </div>
          <div v-if="Object.keys(agentStore.coreMemory).length > 0">
            <v-card 
              v-for="block in agentStore.coreMemory" 
              :key="block.id" 
              class="mb-4"
              variant="outlined"
            >
              <v-card-title class="d-flex justify-space-between">
                <span>{{ block.title }}</span>
                <div>
                  <v-btn @click="openCoreMemoryDialog(block)" icon="mdi-pencil" size="x-small" variant="text"></v-btn>
                  <v-btn @click="deleteCoreMemoryBlock(block.id)" icon="mdi-delete" size="x-small" variant="text" color="error"></v-btn>
                </div>
              </v-card-title>
              <v-card-subtitle>{{ block.description }}</v-card-subtitle>
              <v-card-text>
                <ul>
                  <li v-for="(item, index) in block.content" :key="index">{{ item }}</li>
                </ul>
              </v-card-text>
            </v-card>
          </div>
          <p v-else>没有核心记忆。</p>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Add Temp Memory Dialog -->
    <v-dialog v-model="isAddTempMemoryDialogVisible" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">添加临时记忆</span>
        </v-card-title>
        <v-card-text>
          <v-select
            v-model="newTempMemory.role"
            :items="['system', 'user', 'assistant']"
            label="角色"
            required
          ></v-select>
          <v-textarea
            v-model="newTempMemory.content"
            label="内容"
            required
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue-darken-1" variant="text" @click="isAddTempMemoryDialogVisible = false">取消</v-btn>
          <v-btn color="blue-darken-1" variant="text" @click="addTempMemory">添加</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add/Edit Core Memory Dialog -->
    <v-dialog v-model="isCoreMemoryDialogVisible" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ editingCoreMemoryBlock.id ? '编辑' : '添加' }}核心记忆块</span>
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="editingCoreMemoryBlock.title"
            label="标题"
            required
          ></v-text-field>
          <v-textarea
            v-model="editingCoreMemoryBlock.description"
            label="描述"
          ></v-textarea>
          <v-textarea
            v-model="editingCoreMemoryBlock.contentStr"
            label="内容 (每行一条)"
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue-darken-1" variant="text" @click="isCoreMemoryDialogVisible = false">取消</v-btn>
          <v-btn color="blue-darken-1" variant="text" @click="saveCoreMemoryBlock">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add/Edit Init Memory Dialog -->
    <v-dialog v-model="isInitMemoryDialogVisible" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ editingInitMemoryItem.isEditing ? '编辑' : '添加' }}初始化记忆项</span>
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="editingInitMemoryItem.key"
            label="键"
            :disabled="editingInitMemoryItem.isEditing"
            required
          ></v-text-field>
          <v-textarea
            v-model="editingInitMemoryItem.valueStr"
            label="值 (可以是字符串, JSON, 或换行分隔的数组)"
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue-darken-1" variant="text" @click="isInitMemoryDialogVisible = false">取消</v-btn>
          <v-btn color="blue-darken-1" variant="text" @click="saveInitMemoryItem">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAgentStore } from '@/stores/agent';
import { useConnectionStore } from '@/stores/connection';
import { useUiStore } from '@/stores/ui';

const agentStore = useAgentStore();
const connectionStore = useConnectionStore();
const uiStore = useUiStore();

// State for the Add Temp Memory Dialog
const isAddTempMemoryDialogVisible = ref(false);
const newTempMemory = ref({ role: 'user', content: '' });

// State for the Add/Edit Core Memory Dialog
const isCoreMemoryDialogVisible = ref(false);
const editingCoreMemoryBlock = ref<any>({});

// State for the Add/Edit Init Memory Dialog
const isInitMemoryDialogVisible = ref(false);
const editingInitMemoryItem = ref<any>({});

function openCoreMemoryDialog(block: any = null) {
  if (block) {
    // Editing existing block
    editingCoreMemoryBlock.value = { ...block, contentStr: block.content.join('\n') };
  } else {
    // Adding new block
    editingCoreMemoryBlock.value = { title: '', description: '', contentStr: '' };
  }
  isCoreMemoryDialogVisible.value = true;
}

async function saveCoreMemoryBlock() {
  if (!connectionStore.isConnected) return;
  const blockToSave = editingCoreMemoryBlock.value;
  const payload = {
    title: blockToSave.title,
    description: blockToSave.description,
    content: blockToSave.contentStr.split('\n').filter((line: string) => line.trim() !== ''),
  };

  try {
    if (blockToSave.id) {
      // Update existing block
      await connectionStore.sendAdminWsMessage('update_core_memory_block', { block_id: blockToSave.id, ...payload });
    } else {
      // Create new block
      await connectionStore.sendAdminWsMessage('create_core_memory_block', payload);
    }
    isCoreMemoryDialogVisible.value = false;
  } catch (error) {
    console.error("Failed to save core memory block:", error);
  }
}

function openInitMemoryDialog(key: string | null = null, value: any = null) {
  if (key !== null) {
    // Editing existing item
    let valueStr = value;
    if (Array.isArray(value)) {
      valueStr = value.join('\n');
    } else if (typeof value === 'object') {
      valueStr = JSON.stringify(value, null, 2);
    }
    editingInitMemoryItem.value = { key, valueStr, isEditing: true };
  } else {
    // Adding new item
    editingInitMemoryItem.value = { key: '', valueStr: '', isEditing: false };
  }
  isInitMemoryDialogVisible.value = true;
}

async function saveInitMemoryItem() {
  if (!connectionStore.isConnected || !editingInitMemoryItem.value.key.trim()) return;
  
  const { key, valueStr } = editingInitMemoryItem.value;
  let parsedValue: any = valueStr;

  try {
    // Attempt to parse the value as JSON if it looks like it
    const trimmedValue = valueStr.trim();
    if ((trimmedValue.startsWith('{') && trimmedValue.endsWith('}')) || (trimmedValue.startsWith('[') && trimmedValue.endsWith(']'))) {
        parsedValue = JSON.parse(trimmedValue);
    } else if (trimmedValue.includes('\n')) {
        // Parse as an array if it contains newlines
        parsedValue = trimmedValue.split('\n').filter((line: string) => line.trim() !== '');
    }
  } catch (e) {
    // If parsing fails, just treat it as a plain string
    console.warn("Could not parse value as JSON or array, saving as string.", e);
  }

  try {
    await connectionStore.sendAdminWsMessage('update_init_memory_item', { key, value: parsedValue });
    isInitMemoryDialogVisible.value = false;
  } catch (error) {
    console.error(`Failed to save init memory item ${key}:`, error);
  }
}

async function addTempMemory() {
  if (!connectionStore.isConnected || !newTempMemory.value.content.trim()) return;
  try {
    await connectionStore.sendAdminWsMessage('add_temp_memory', newTempMemory.value);
    isAddTempMemoryDialogVisible.value = false;
    newTempMemory.value.content = ''; // Reset content
  } catch (error) {
    console.error("Failed to add temp memory:", error);
  }
}

async function deleteCoreMemoryBlock(blockId: string) {
  if (!connectionStore.isConnected) return;
  if (confirm('确定要删除这个记忆块吗？')) {
    try {
      await connectionStore.sendAdminWsMessage('delete_core_memory_block', { block_id: blockId });
    } catch (error) {
      console.error(`Failed to delete core memory block ${blockId}:`, error);
    }
  }
}

async function deleteInitMemoryItem(key: string) {
  if (!connectionStore.isConnected) return;
  if (confirm(`确定要删除键 "${key}" 吗？`)) {
    try {
      await connectionStore.sendAdminWsMessage('delete_init_memory_key', { key });
    } catch (error) {
      console.error(`Failed to delete init memory item ${key}:`, error);
    }
  }
}

async function deleteTempMemoryItem(itemId: string) {
  if (!connectionStore.isConnected) return;
  // Optional: add a confirmation dialog
  try {
    await connectionStore.sendAdminWsMessage('delete_temp_memory_item', { item_id: itemId });
  } catch (error) {
    console.error(`Failed to delete temp memory item ${itemId}:`, error);
  }
}

async function clearTempMemory() {
  if (!connectionStore.isConnected) return;
  // Optional: add a confirmation dialog
  if (confirm('确定要清空所有临时记忆吗？')) {
    try {
      await connectionStore.sendAdminWsMessage('clear_temp_memory');
    } catch (error) {
      console.error("Failed to clear temp memory:", error);
    }
  }
}

async function refreshInitMemory() {
  if (!connectionStore.isConnected) return;
  try {
    const data = await connectionStore.sendAdminWsMessage('get_init_memory');
    agentStore.handleInitMemoryUpdate(data);
  } catch (error) {
    console.error("Failed to refresh init memory:", error);
  }
}

async function refreshTempMemory() {
  if (!connectionStore.isConnected) return;
  try {
    const data = await connectionStore.sendAdminWsMessage('get_temp_memory');
    agentStore.handleTempMemoryUpdate(data);
  } catch (error) {
    console.error("Failed to refresh temp memory:", error);
  }
}

async function refreshCoreMemory() {
  if (!connectionStore.isConnected) return;
  try {
    const data = await connectionStore.sendAdminWsMessage('get_core_memory_blocks');
    agentStore.handleCoreMemoryUpdate(data);
  } catch (error) {
    console.error("Failed to refresh core memory:", error);
  }
}

async function refreshAllMemories() {
  if (!connectionStore.isConnected) return;
  // Now we call the individual refresh functions
  await Promise.all([
    refreshInitMemory(),
    refreshTempMemory(),
    refreshCoreMemory(),
  ]);
}

onMounted(() => {
  refreshAllMemories();
});
</script>

<style scoped>
.value-display pre {
  white-space: pre-wrap;       /* CSS3 */
  white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
  white-space: -pre-wrap;      /* Opera 4-6 */
  white-space: -o-pre-wrap;    /* Opera 7 */
  word-wrap: break-word;       /* Internet Explorer 5.5+ */
}
</style>