import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';
import router from '@/router';
import { useStreamStore } from './stream';
import { useLogStore } from './logs';
import { useAgentStore } from './agent';
import { useConfigStore } from './config';
import { useToolsStore } from './tools';

interface PendingRequest {
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}

export const useConnectionStore = defineStore('connection', () => {
  const isConnected = ref(false);
  const isIntegrated = ref(false);
  const statusText = ref('未连接');
  const backendUrl = ref(localStorage.getItem('backendUrl') || '');
  const password = ref(localStorage.getItem('password') || '');
  const wasUnexpectedlyDisconnected = ref(false);
  const ws = shallowRef<WebSocket | null>(null);
  const pendingRequests = new Map<string, PendingRequest>();
  let requestCounter = 0;

  async function connectToBackend(): Promise<boolean> {
    if (isConnected.value || ws.value) {
      await disconnectFromBackend();
    }
    statusText.value = '连接中...';
    try {
      const url = backendUrl.value || window.location.origin;
      const healthUrl = new URL('/api/system/health', url).toString();
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (password.value) {
        headers['X-API-Token'] = password.value;
      }
      const response = await fetch(healthUrl, { headers });
      if (!response.ok) {
        if (response.status === 401) throw new Error('认证失败，请检查密码');
        throw new Error(`后端服务不健康: ${response.statusText}`);
      }
      const healthData = await response.json();
      if (healthData.status !== 'healthy') {
        throw new Error('后端服务不健康');
      }
      await connectWebSocket();
      isConnected.value = true;
      statusText.value = '已连接';
      if (backendUrl.value) {
        localStorage.setItem('backendUrl', backendUrl.value);
        localStorage.setItem('password', password.value);
      }
      console.log('连接成功！');
      const configStore = useConfigStore();
      await configStore.fetchConfig();
      await router.push('/control');
      return true;
    } catch (error: any) {
      console.error('连接失败:', error);
      statusText.value = `连接失败: ${error.message}`;
      isConnected.value = false;
      if (ws.value) {
        ws.value.close();
        ws.value = null;
      }
      return false;
    }
  }

  function connectWebSocket() {
    return new Promise<void>((resolve, reject) => {
      const url = backendUrl.value || window.location.origin;
      const wsUrl = new URL('/ws/admin', url).toString().replace(/^http/, 'ws');
      const webSocket = new WebSocket(wsUrl);
      webSocket.onopen = () => {
        console.log('管理WebSocket连接已建立');
        ws.value = webSocket;
        if (password.value) {
          ws.value.send(JSON.stringify({ action: "authenticate", payload: { password: password.value } }));
        }
        resolve();
      };
      webSocket.onmessage = (event) => handleWsMessage(event.data);
      webSocket.onerror = (error) => {
        console.error('管理WebSocket错误:', error);
        reject(new Error('WebSocket连接错误'));
      };
      webSocket.onclose = (event) => {
        console.log('管理WebSocket连接已关闭，代码:', event.code, '原因:', event.reason);
        if (isConnected.value && event.code !== 1000) {
          wasUnexpectedlyDisconnected.value = true;
        }
        isConnected.value = false;
        statusText.value = '连接已断开';
        ws.value = null;
        pendingRequests.forEach((p) => p.reject(new Error('连接已断开')));
        pendingRequests.clear();
      };
    });
  }

  async function disconnectFromBackend() {
    if (ws.value) {
      ws.value.close(1000, 'Client disconnecting');
      ws.value = null;
    }
    isConnected.value = false;
    statusText.value = '已断开连接';
    console.log('已断开连接');
  }

  function sendAdminWsMessage<T = any>(action: string, payload: any = {}): Promise<T> {
    return new Promise((resolve, reject) => {
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        return reject(new Error('WebSocket未连接'));
      }
      const requestId = `req-${Date.now()}-${requestCounter++}`;
      const message = { action, payload, request_id: requestId };
      pendingRequests.set(requestId, { resolve, reject });
      try {
        ws.value.send(JSON.stringify(message));
      } catch (error) {
        pendingRequests.delete(requestId);
        reject(new Error('发送消息失败'));
      }
      setTimeout(() => {
        if (pendingRequests.has(requestId)) {
          pendingRequests.delete(requestId);
          reject(new Error('请求超时'));
        }
      }, 15000);
    });
  }

  function handleWsMessage(data: any) {
    try {
      const message = JSON.parse(data);
      if (message.type === 'response' && message.request_id) {
        const pending = pendingRequests.get(message.request_id);
        if (pending) {
          pendingRequests.delete(message.request_id);
          if (message.payload?.status === 'error') {
            pending.reject(new Error(message.payload.message || 'Unknown backend error'));
          } else {
            pending.resolve(message.payload);
          }
        }
      } else if (message.type) {
        const streamStore = useStreamStore();
        const logStore = useLogStore();
        const agentStore = useAgentStore();
        const configStore = useConfigStore();
        const toolsStore = useToolsStore();
        switch (message.type) {
          case 'stream_status': streamStore.handleStreamStatusUpdate(message.payload); break;
          case 'server_log': logStore.addServerLog(message.data || message.content || 'Unknown server log'); break;
          case 'agent_log': logStore.addAgentLog(message.data || message.content || 'Unknown agent log'); break;
          case 'core_memory_updated': agentStore.handleCoreMemoryUpdate(message.payload); break;
          case 'temp_memory_updated': agentStore.handleTempMemoryUpdate(message.payload); break;
          case 'init_memory_updated': agentStore.handleInitMemoryUpdate(message.payload); break;
          case 'agent_context': agentStore.handleAgentContextUpdate(message.messages); break;
          case 'config_updated': configStore.handleConfigUpdate(message.payload); break;
          case 'available_tools_updated': toolsStore.handleAvailableToolsUpdate(message.payload.tools); break;
          case 'agent_tool_allocations_updated': toolsStore.handleAllocationsUpdate(message.payload.allocations); break;
          default: console.log(`Received unhandled server event: ${message.type}`, message.payload);
        }
      }
    } catch (error) {
      console.error('解析WebSocket消息失败:', error);
    }
  }

  async function initializeConnection() {
    try {
      const response = await fetch('/api/system/health');
      if (response.ok) {
        console.log('Integrated mode detected. Auto-connecting...');
        isIntegrated.value = true;
        statusText.value = '检测到集成模式，正在连接...';
        backendUrl.value = '';
        password.value = '';
        localStorage.removeItem('backendUrl');
        localStorage.removeItem('password');
        await connectToBackend();
        return;
      }
    } catch (e) {
      console.log('Probe for integrated mode failed, assuming standalone mode.');
    }

    if (backendUrl.value) {
      console.log('Standalone mode: attempting to connect to stored URL.');
      await connectToBackend();
    }
  }

  initializeConnection();

  return {
    isConnected,
    isIntegrated,
    statusText,
    backendUrl,
    password,
    wasUnexpectedlyDisconnected,
    connectToBackend,
    disconnectFromBackend,
    sendAdminWsMessage,
  };
});