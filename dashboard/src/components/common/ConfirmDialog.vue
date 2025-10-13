<template>
  <v-dialog v-model="uiStore.isConfirmDialogVisible" persistent max-width="400">
    <v-card>
      <v-card-title class="text-h5">{{ t('Please confirm') }}</v-card-title>
      <v-card-text>{{ uiStore.confirmDialogMessage }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="grey-darken-1" variant="text" @click="uiStore.handleConfirm(false)">{{ t('Cancel') }}</v-btn>
        <v-btn color="primary" variant="flat" @click="uiStore.handleConfirm(true)">{{ t('Confirm') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useUiStore } from '@/stores/ui';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const uiStore = useUiStore();
</script>
