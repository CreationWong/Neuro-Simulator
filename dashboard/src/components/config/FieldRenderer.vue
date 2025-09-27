<template>
  <div class="mb-6">
    <!-- Number/Integer Fields -->
    <v-text-field
      v-if="isType('integer') || isType('number')"
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
      v-else-if="isType('string') && !propSchema.enum"
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

    <!-- Array Combobox -->
    <v-combobox
      v-if="isType('array')"
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
import { computed } from 'vue';
import { useConfigStore } from '@/stores/config';

const props = defineProps<{ 
  groupKey: string | null, 
  propKey: string, 
  propSchema: any 
}>();

const configStore = useConfigStore();

function isType(type: string): boolean {
  if (props.propSchema.type === type) {
    return true;
  }
  if (Array.isArray(props.propSchema.anyOf)) {
    return props.propSchema.anyOf.some((t: any) => t.type === type);
  }
  return false;
}

const modelValue = computed({
  get() {
    if (props.groupKey) {
      return configStore.config[props.groupKey]?.[props.propKey];
    } else {
      return configStore.config[props.propKey];
    }
  },
  set(newValue) {
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
</script>