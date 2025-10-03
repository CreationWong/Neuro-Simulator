<template>
  <div class="mb-6">
    <!-- Provider ID (disabled) -->
    <v-text-field
      v-if="propKey === 'provider_id'"
      v-model="modelValue"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      persistent-hint
      variant="outlined"
      density="compact"
      disabled
    ></v-text-field>

    <!-- Number/Integer Fields -->
    <v-text-field
      v-else-if="isType('integer') || isType('number')"
      v-model.number="modelValue"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      type="number"
      persistent-hint
      variant="outlined"
      density="compact"
    ></v-text-field>

    <!-- Password Field -->
    <v-text-field
      v-else-if="isType('string') && propSchema.format === 'password'"
      v-model="modelValue"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      type="password"
      persistent-hint
      variant="outlined"
      density="compact"
    ></v-text-field>

    <!-- Text Area -->
    <v-textarea
      v-else-if="isType('string') && propSchema.format === 'text-area'"
      v-model="modelValue"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      persistent-hint
      variant="outlined"
    ></v-textarea>

    <!-- Regular Text Field -->
    <v-text-field
      v-else-if="isType('string') && !propSchema.enum && !isProviderId"
      v-model="modelValue"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      persistent-hint
      variant="outlined"
      density="compact"
    ></v-text-field>

    <!-- Boolean Switch -->
    <v-switch
      v-if="isType('boolean')"
      v-model="modelValue"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      persistent-hint
      color="primary"
      inset
    ></v-switch>

    <!-- Enum Select Dropdown -->
    <v-select
      v-if="propSchema.enum"
      v-model="modelValue"
      :items="propSchema.enum"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      persistent-hint
      variant="outlined"
      density="compact"
    ></v-select>

    <!-- Provider ID Select Dropdown -->
    <v-select
      v-if="isProviderId"
      v-model="modelValue"
      :items="providerItems"
      item-title="display_name"
      item-value="provider_id"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      persistent-hint
      variant="outlined"
      density="compact"
      clearable
    ></v-select>

    <!-- Array of Objects Renderer -->
    <div v-else-if="isObjectArray">
      <h3 class="text-h6 mb-2">{{ propSchema.title || propKey }}</h3>
      <p v-if="propSchema.description" class="text-caption mb-4">{{ propSchema.description }}</p>
      <v-card v-for="(item, index) in modelValue" :key="item.provider_id || index" class="mb-4" variant="outlined">
        <v-card-title class="d-flex justify-space-between align-center text-body-1">
          <span>{{ item.display_name || 'Item ' + (index + 1) }}</span>
          <div>
            <v-btn icon="mdi-pencil" size="small" variant="text" @click="openEditDialog(item, index)"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="text" @click="deleteItem(index)"></v-btn>
          </div>
        </v-card-title>
        <v-card-text v-if="item.provider_type || item.model_name">
          <p v-if="item.provider_type" class="text-body-2">Provider Type: {{ item.provider_type }}</p>
          <p v-if="item.model_name" class="text-body-2">Model: {{ item.model_name }}</p>
        </v-card-text>
      </v-card>
      <v-btn color="primary" @click="openAddDialog" block>Add {{ itemSchema.title || 'Item' }}</v-btn>

      <!-- Dialog for Add/Edit -->
      <v-dialog v-model="dialog" max-width="800px" persistent>
        <v-card :title="(isEditing ? 'Edit' : 'Add') + ' ' + (itemSchema.title || 'Item')">
          <v-card-text>
            <div v-for="key in Object.keys(itemSchema.properties || {})" :key="key">
              <FieldRenderer 
                :group-key="null" 
                :prop-key="key" 
                :prop-schema="itemSchema.properties[key]"
                :is-in-dialog="true"
                :dialog-data="editableItem"
              />
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn text @click="dialog = false">Cancel</v-btn>
            <v-btn color="primary" @click="saveItem">Save</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>

    <!-- Array Combobox for simple arrays -->
    <v-combobox
      v-else-if="isType('array')"
      v-model="modelValue"
      :label="propSchema.title || propKey"
      :hint="propSchema.description"
      persistent-hint
      chips
      multiple
      closable-chips
      variant="outlined"
      density="compact"
    ></v-combobox>

  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, defineAsyncComponent } from 'vue';
import { useConfigStore } from '@/stores/config';
import { v4 as uuidv4 } from 'uuid';

// Using defineAsyncComponent to avoid circular reference
const FieldRenderer = defineAsyncComponent(() => import('@/components/config/FieldRenderer.vue'));

const props = defineProps<{ 
  groupKey: string | null, 
  propKey: string, 
  propSchema: any,
  isInDialog?: boolean,
  dialogData?: any
}>();

const configStore = useConfigStore();

// --- Type Checkers ---
function isType(type: string): boolean {
  if (props.propSchema.type === type) return true;
  if (Array.isArray(props.propSchema.anyOf)) {
    return props.propSchema.anyOf.some((t: any) => t.type === type);
  }
  return false;
}

const isObjectArray = computed(() => {
  if (!isType('array') || !props.propSchema.items) return false;
  // An array of objects can be defined inline or with a $ref
  return props.propSchema.items.type === 'object' || !!props.propSchema.items.$ref;
});

const itemSchema = computed(() => {
  if (!isObjectArray.value) return {};
  const items = props.propSchema.items;
  if (items.$ref) {
    const refName = items.$ref.split('/').pop();
    return configStore.schema.$defs?.[refName] || {};
  }
  return items;
});

const isProviderId = computed(() => {
  return props.propKey.endsWith('_provider_id');
});

// --- Provider ID Dropdown Logic ---
const providerItems = computed(() => {
  if (props.propKey === 'llm_provider_id') {
    return configStore.config.llm_providers || [];
  }
  if (props.propKey === 'tts_provider_id') {
    return configStore.config.tts_providers || [];
  }
  return [];
});

// --- Main Model Value ---
const modelValue = computed({
  get() {
    if (props.isInDialog) {
      return props.dialogData?.[props.propKey];
    }
    if (props.groupKey) {
      return configStore.config[props.groupKey]?.[props.propKey];
    }
    return configStore.config[props.propKey];
  },
  set(newValue) {
    if (props.isInDialog) {
      if (props.dialogData) {
        props.dialogData[props.propKey] = newValue;
      }
      return;
    }
    if (props.groupKey) {
      if (!configStore.config[props.groupKey]) {
        configStore.config[props.groupKey] = {};
      }
      configStore.config[props.groupKey][props.propKey] = newValue;
    } else {
      configStore.config[props.propKey] = newValue;
    }
  }
});

// --- Object Array CRUD Logic ---
const dialog = ref(false);
const isEditing = ref(false);
const editableItem = reactive<any>({});
const editingIndex = ref(-1);

function openAddDialog() {
  isEditing.value = false;
  Object.keys(editableItem).forEach(key => delete editableItem[key]); // Clear reactive object
  
  const properties = itemSchema.value.properties || {};
  for (const key in properties) {
    editableItem[key] = properties[key].default ?? null;
  }

  // Generate structured provider ID
  const providerType = editableItem.provider_type || itemSchema.value.properties?.provider_type?.enum?.[0] || 'unknown';
  const prefix = props.propKey === 'llm_providers' ? 'llm' : 'tts';
  editableItem.provider_id = `${prefix}-${providerType}-${uuidv4()}`;

  dialog.value = true;
}

function openEditDialog(item: any, index: number) {
  isEditing.value = true;
  editingIndex.value = index;
  Object.keys(editableItem).forEach(key => delete editableItem[key]);
  Object.assign(editableItem, JSON.parse(JSON.stringify(item))); // Deep copy
  dialog.value = true;
}

function saveItem() {
  const list = modelValue.value || [];
  if (isEditing.value) {
    list[editingIndex.value] = JSON.parse(JSON.stringify(editableItem));
  } else {
    list.push(JSON.parse(JSON.stringify(editableItem)));
  }
  modelValue.value = list;
  dialog.value = false;
}

function deleteItem(index: number) {
  const list = modelValue.value || [];
  list.splice(index, 1);
  modelValue.value = list;
}

</script>
