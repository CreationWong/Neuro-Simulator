<template>
  <v-app>
    <v-app-bar app>
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title class="title-text">vedal987 🐢 Simulator</v-toolbar-title>

      <v-spacer></v-spacer>

      <v-chip
        :color="statusColor"
        text-color="white"
        variant="flat"
        size="small"
        class="mr-4"
      >
        {{ connectionStore.statusText }}
      </v-chip>
    </v-app-bar>

    <v-navigation-drawer app v-model="drawer">
      <v-list dense>
        <v-list-item v-for="item in visibleNavItems" :key="item.title" :to="item.to" link>
          <template v-slot:prepend>
            <v-icon>{{ item.icon }}</v-icon>
          </template>
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item>
      </v-list>

      <template v-slot:append>
        <div class="pa-2 footer-text">
          *Evil sold out
        </div>
      </template>

    </v-navigation-drawer>

    <v-main>
      <v-container fluid>
        <router-view></router-view>
      </v-container>
    </v-main>
  </v-app>

  <!-- Disconnection Dialog -->
  <v-dialog v-model="connectionStore.wasUnexpectedlyDisconnected" persistent max-width="400">
    <v-card>
      <v-card-title class="text-h5">连接已断开</v-card-title>
      <v-card-text>与后端的连接已意外断开，请重新连接。</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="flat" @click="handleReconnectRedirect">返回连接页面</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog />

</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useConnectionStore } from '@/stores/connection';
import { useConfigStore } from '@/stores/config';
import { useRouter } from 'vue-router';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';

const drawer = ref(true); // Sidebar is open by default

const allNavItems = [
  { title: '连接', icon: 'mdi-connection', to: '/' },
  { title: '控制', icon: 'mdi-gamepad-variant', to: '/control' },
  { title: '配置', icon: 'mdi-cog', to: '/config' },
  { title: '日志', icon: 'mdi-file-document-outline', to: '/logs' },
  { title: 'Agent', icon: 'mdi-robot', to: '/agent', name: 'agent' },
  { title: 'ChatBot', icon: 'mdi-forum', to: '/chatbot' },
];

const connectionStore = useConnectionStore();
const configStore = useConfigStore();
const router = useRouter();

const visibleNavItems = computed(() => {
  // If not connected, only show the connection tab
  if (!connectionStore.isConnected) {
    return allNavItems.filter(item => item.to === '/');
  }
  return allNavItems;
});

const statusColor = computed(() => {
  const status = connectionStore.statusText;
  if (status === '已连接') return 'success';
  if (status === '连接中...') return 'warning';
  return 'error';
});

function handleReconnectRedirect() {
  connectionStore.wasUnexpectedlyDisconnected = false; // Reset the flag
  router.push({ name: 'connection' });
}

onMounted(async () => {
  // Try to auto-connect if a URL is saved
  if (connectionStore.backendUrl) {
    const success = await connectionStore.connectToBackend();
    if (success) {
      router.push('/control');
    }
  }
});
</script>

<style scoped>
.title-text {
  font-family: 'First Coffee', sans-serif;
  font-weight: 600;
}

.footer-text {
  font-family: 'First Coffee', sans-serif;
  font-weight: 600;
  color: #8A8A8A; /* A light grey color */
  text-align: center;
}
</style>