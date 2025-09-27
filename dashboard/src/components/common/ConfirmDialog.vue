<template>
  <v-dialog v-model="uiStore.isConfirmDialogVisible" persistent max-width="400">
    <v-card>
      <v-card-title class="text-h5">请确认</v-card-title>
      <v-card-text>{{ uiStore.confirmDialogMessage }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="grey-darken-1" variant="text" @click="uiStore.handleConfirm(false)">取消</v-btn>
        <v-btn color="primary" variant="flat" @click="uiStore.handleConfirm(true)">确定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useUiStore } from '@/stores/ui';

const uiStore = useUiStore();
</script>
