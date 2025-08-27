// dashboard_web/js/modules/connection.js

// 全局变量
let backendUrl = '';
let authToken = '';
let isConnected = false;
let adminWebSocket = null;
let pendingRequests = new Map(); // 存储待处理的请求Promise回调 {request_id: {resolve, reject}}
let requestCounter = 0; // 用于生成唯一的request_id

// 添加一个函数来获取当前连接状态的详细信息
function getConnectionStatusDetails() {
    return {
        isConnected: window.connectionModule.isConnected,
        backendUrl: window.connectionModule.backendUrl,
        authToken: window.connectionModule.authToken ? '***' : '',
        adminWebSocketReadyState: window.connectionModule.adminWebSocket ? window.connectionModule.adminWebSocket.readyState : 'null',
    }
};

// DOM 元素
const connectionForm = document.getElementById('connectionForm');
const disconnectBtn = document.getElementById('disconnectBtn');
const connectionStatus = document.getElementById('connectionStatus');
const statusDot = connectionStatus.querySelector('.status-dot');
const statusText = connectionStatus.querySelector('.status-text');

// 更新连接状态显示
function updateConnectionStatus(connected, message = '') {
    window.connectionModule.isConnected = connected;
    
    const statusDot = document.getElementById('connectionStatus').querySelector('.status-dot');
    const statusText = document.getElementById('connectionStatus').querySelector('.status-text');
    
    if (connected) {
        statusDot.className = 'status-dot connected';
        statusText.textContent = message || '已连接';
        const disconnectBtn = document.getElementById('disconnectBtn');
        if (disconnectBtn) {
            disconnectBtn.disabled = false;
        }
        
        // 显示控制、配置和日志标签页
        const controlTab = document.querySelector('[data-tab="control"]');
        const configTab = document.querySelector('[data-tab="config"]');
        const logsTab = document.querySelector('[data-tab="logs"]');
        if (controlTab) controlTab.style.display = 'block';
        if (configTab) configTab.style.display = 'block';
        if (logsTab) logsTab.style.display = 'block';
        // agentManagementTab 和 chatbotManagementTab 的显示由配置决定，在获取配置后处理
    } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = message || '未连接';
        const disconnectBtn = document.getElementById('disconnectBtn');
        if (disconnectBtn) {
            disconnectBtn.disabled = true;
        }
        
        // 隐藏控制、配置和日志标签页
        const controlTab = document.querySelector('[data-tab="control"]');
        const configTab = document.querySelector('[data-tab="config"]');
        const logsTab = document.querySelector('[data-tab="logs"]');
        const agentManagementTab = document.querySelector('[data-tab="agent-management"]');
        const chatbotManagementTab = document.querySelector('[data-tab="chatbot-management"]');
        if (controlTab) controlTab.style.display = 'none';
        if (configTab) configTab.style.display = 'none';
        if (logsTab) logsTab.style.display = 'none';
        if (agentManagementTab) agentManagementTab.style.display = 'none';
        if (chatbotManagementTab) chatbotManagementTab.style.display = 'none';
        
        // 关闭管理WebSocket连接
        if (window.connectionModule.adminWebSocket) {
            try {
                window.connectionModule.adminWebSocket.close(1000, 'Client disconnecting');
            } catch (e) {
                console.error('关闭管理WebSocket时出错:', e);
            }
            window.connectionModule.adminWebSocket = null;
        }
        
        // 清除所有待处理的请求
        pendingRequests.forEach(({ reject }, id) => {
            reject(new Error('Connection lost'));
        });
        pendingRequests.clear();
    }
}

// 发送API请求的通用函数 (用于初始认证)
async function apiRequest(endpoint, options = {}, skipConnectionCheck = false) {
    // 简化版的apiRequest，主要用于连接时的认证检查
    if (!window.connectionModule.backendUrl && !skipConnectionCheck) {
        throw new Error('未配置后端地址');
    }
    
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
    const url = window.connectionModule.backendUrl.endsWith('/') ? 
        `${window.connectionModule.backendUrl.slice(0, -1)}${cleanEndpoint}` : 
        `${window.connectionModule.backendUrl}${cleanEndpoint}`;
        
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (window.connectionModule.authToken && window.connectionModule.authToken.trim() !== '') {
        headers['X-API-Token'] = window.connectionModule.authToken;
    }
    
    const config = {
        headers,
        ...options
    };
    
    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('认证失败，请检查密码');
            }
            throw new Error(`请求失败: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        // 网络错误处理
        if (error instanceof TypeError && error.message === 'Failed to fetch') {
            window.uiModule.showToast('无法连接到后端，请检查地址和网络', 'error');
        }
        throw error;
    }
}

// 连接到后端 (包括HTTP认证和WebSocket连接)
async function connectToBackend(autoConnect = false) {
    const url = document.getElementById('backendUrl').value.trim();
    const password = document.getElementById('password').value;
    
    if (!url && !autoConnect) {
        window.uiModule.showToast('请输入后端地址', 'warning');
        return;
    }
    
    if (!url && autoConnect) {
        return;
    }
    
    // 在尝试新连接之前，先断开任何现有的连接
    if (window.connectionModule.adminWebSocket) {
        console.log('Closing existing WebSocket connection before connecting...');
        window.connectionModule.adminWebSocket.close(1000, 'Client initiating new connection');
        window.connectionModule.adminWebSocket = null;
    }
    
     // 重置待处理的请求
     pendingRequests.forEach(({ reject }, id) => {
        reject(new Error('Connection interrupted by new connection attempt'));
    });
    pendingRequests.clear();
    
    try {
        // 更新状态为连接中
        const statusDot = document.getElementById('connectionStatus').querySelector('.status-dot');
        const statusText = document.getElementById('connectionStatus').querySelector('.status-text');
        statusDot.className = 'status-dot connecting';
        statusText.textContent = '连接中...';
        
        // 保存连接信息到localStorage
        window.connectionModule.backendUrl = url;
        window.connectionModule.authToken = password || '';
        localStorage.setItem('backendUrl', window.connectionModule.backendUrl);
        if (window.connectionModule.authToken) {
            localStorage.setItem('authToken', window.connectionModule.authToken);
        }
        
        // 1. 通过HTTP API进行认证
        const healthResponse = await window.connectionModule.apiRequest('/api/system/health', {}, true);
        
        if (healthResponse.status !== 'healthy') {
            throw new Error('后端服务不健康');
        }
        
        // 2. 认证成功后，连接到管理WebSocket
        await window.connectionModule.connectAdminWebSocket();
        
        // 3. 更新UI状态
        window.connectionModule.updateConnectionStatus(true, '已连接');
        if (!autoConnect) {
            window.uiModule.showToast('连接成功！', 'success');
        }
        
        // 4. 默认切换到控制页面
        window.uiModule.switchTab('control');
        
        // 5. 获取初始配置
        if (window.configModule && window.configModule.getConfig) {
            // 延迟一小段时间确保WebSocket完全建立并能接收初始事件
            setTimeout(() => {
                window.configModule.getConfig().catch(error => {
                    console.error('获取配置失败:', error);
                    window.uiModule.showToast(`获取配置失败: ${error.message}`, 'error');
                });
            }, 100);
        }
        
    } catch (error) {
        console.error('连接失败:', error);
        // 确保在失败时也关闭可能已打开的WebSocket
        if (window.connectionModule.adminWebSocket) {
            window.connectionModule.adminWebSocket.close(1000, 'Connection failed');
            window.connectionModule.adminWebSocket = null;
        }
        window.connectionModule.updateConnectionStatus(false, '连接失败');
        if (!autoConnect) {
            window.uiModule.showToast(`连接失败: ${error.message}`, 'error');
        }
        // 切换到连接页面
        window.uiModule.switchTab('connection');
    }
}

// 断开连接
function disconnectFromBackend() {
    // 关闭WebSocket连接
    if (window.connectionModule.adminWebSocket) {
        try {
            window.connectionModule.adminWebSocket.close(1000, 'Client disconnecting');
        } catch (e) {
            console.error('Error closing WebSocket:', e);
        }
        window.connectionModule.adminWebSocket = null;
    }
    
    // 清除所有待处理的请求
    pendingRequests.forEach(({ reject }, id) => {
        reject(new Error('Connection disconnected'));
    });
    pendingRequests.clear();
    
    window.connectionModule.backendUrl = '';
    window.connectionModule.authToken = '';
    window.connectionModule.updateConnectionStatus(false, '已断开连接');
    window.uiModule.showToast('已断开连接', 'info');
    // 切换回连接页面
    window.uiModule.switchTab('connection');
}

// 连接管理WebSocket
function connectAdminWebSocket() {
    return new Promise((resolve, reject) => {
        if (window.connectionModule.adminWebSocket) {
            window.connectionModule.adminWebSocket.close();
        }
        
        try {
            const wsUrl = window.connectionModule.backendUrl.replace(/^http/, 'ws') + '/ws/admin';
            window.connectionModule.adminWebSocket = new WebSocket(wsUrl);
            
            window.connectionModule.adminWebSocket.onopen = () => {
                console.log('管理WebSocket连接已建立');
                // 如果设置了密码，发送认证消息
                if (window.connectionModule.authToken && window.connectionModule.authToken.trim() !== '') {
                    const authMessage = {
                        action: "authenticate",
                        payload: {
                            password: window.connectionModule.authToken
                        }
                    };
                    window.connectionModule.adminWebSocket.send(JSON.stringify(authMessage));
                }
                resolve();
            };
            
            window.connectionModule.adminWebSocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // 检查是否是请求响应
                    if (data.type === 'response' && data.request_id) {
                        const pendingRequest = pendingRequests.get(data.request_id);
                        if (pendingRequest) {
                            pendingRequests.delete(data.request_id);
                            if (data.payload && data.payload.status === 'error') {
                                pendingRequest.reject(new Error(data.payload.message || 'Unknown error'));
                            } else {
                                pendingRequest.resolve(data.payload);
                            }
                        }
                    }
                    // 处理服务器推送的事件
                    // 将事件类型分发给对应的模块处理
                    else if (data.type === 'core_memory_updated') {
                        if (window.agentModule && window.agentModule.displayCoreMemory) {
                            window.agentModule.displayCoreMemory(data.payload);
                        }
                    }
                    else if (data.type === 'temp_memory_updated') {
                        if (window.agentModule && window.agentModule.displayTempMemory) {
                            window.agentModule.displayTempMemory(data.payload);
                        }
                    }
                    else if (data.type === 'init_memory_updated') {
                        if (window.agentModule && window.agentModule.displayInitMemory) {
                            window.agentModule.displayInitMemory(data.payload);
                        }
                    }
                    else if (data.type === 'agent_context') {
                        // 处理Agent上下文 (流式更新)
                        if (window.agentModule && window.agentModule.displayAgentContext) {
                            // 传递新的消息数组
                            window.agentModule.displayAgentContext(data.messages);
                        }
                    }
                    else if (data.type === 'server_log') {
                        // 处理服务器日志
                        const serverLogsOutput = document.getElementById('serverLogsOutput');
                        if (serverLogsOutput) {
                            const logDiv = document.createElement('div');
                            logDiv.className = 'log-entry log-server';
                            
                            const content = data.data || data.content || data.message || 'Unknown server log message';
                            
                            if (content.includes('ERROR') || content.includes('Error')) {
                                logDiv.classList.add('log-error');
                            } else if (content.includes('WARNING') || content.includes('Warning')) {
                                logDiv.classList.add('log-warning');
                            } else if (content.includes('DEBUG') || content.includes('Debug')) {
                                logDiv.classList.add('log-debug');
                            } else {
                                logDiv.classList.add('log-info');
                            }
                            
                            logDiv.textContent = content;
                            serverLogsOutput.appendChild(logDiv);
                            
                            const logEntries = serverLogsOutput.querySelectorAll('.log-entry');
                            if (logEntries.length > 1000) {
                                for (let i = 0; i < logEntries.length - 1000; i++) {
                                    logEntries[i].remove();
                                }
                            }
                            
                            serverLogsOutput.scrollTop = serverLogsOutput.scrollHeight;
                        }
                    }
                    else if (data.type === 'agent_log') {
                        // 处理Agent日志 (流式更新)
                        if (window.agentModule && window.agentModule.displayAgentLogs) {
                            // 传递单条日志记录
                            window.agentModule.displayAgentLogs(data.data || data.content || data.message || 'Unknown agent log message');
                        }
                    }
                    else if (data.type === 'config_updated') {
                        // 更新配置显示
                        if (window.configModule && window.configModule.configToForm) {
                            window.configModule.configToForm(data.payload);
                        }
                        // 更新Agent管理标签页可见性
                        if (window.configModule && window.configModule.updateAgentManagementVisibility) {
                            window.configModule.updateAgentManagementVisibility(data.payload);
                        }
                    }
                    else if (data.type === 'stream_status') {
                        // 更新直播状态显示
                        const streamStatus = document.getElementById('streamStatus');
                        if (streamStatus) {
                            streamStatus.textContent = data.payload.is_running ? '运行中' : '已停止';
                            streamStatus.style.color = data.payload.is_running ? '#4CAF50' : '#F44336';
                        }
                    }
                    else if (data.type === 'available_tools_updated') {
                        if (window.toolsModule && window.toolsModule.handleAvailableToolsUpdate) {
                            window.toolsModule.handleAvailableToolsUpdate(data.payload.tools);
                        }
                    }
                    else if (data.type === 'agent_tool_allocations_updated') {
                        if (window.toolsModule && window.toolsModule.handleAllocationsUpdate) {
                            window.toolsModule.handleAllocationsUpdate(data.payload.allocations);
                        }
                    }
                    else {
                        console.log('Received WebSocket message:', data);
                    }
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error);
                }
            };
            
            window.connectionModule.adminWebSocket.onerror = (error) => {
                console.error('管理WebSocket错误:', error);
                reject(new Error('WebSocket连接错误'));
            };
            
            window.connectionModule.adminWebSocket.onclose = (event) => {
                console.log('管理WebSocket连接已关闭，代码:', event.code, '原因:', event.reason);
                // 如果不是主动断开，显示错误信息
                if (event.code !== 1000) {
                    window.uiModule.showToast('与后端的WebSocket连接已断开', 'error');
                }
                window.connectionModule.updateConnectionStatus(false, '连接已断开');
                if (window.uiModule && window.uiModule.showDisconnectDialog) {
                    window.uiModule.showDisconnectDialog();
                }
                window.uiModule.switchTab('connection');
                reject(new Error('WebSocket连接已关闭'));
            };
        } catch (error) {
            console.error('连接管理WebSocket失败:', error);
            reject(new Error('无法建立WebSocket连接'));
        }
    });
}

// 通过WebSocket发送管理消息并等待响应
function sendAdminWsMessage(action, payload = {}) {
    return new Promise((resolve, reject) => {
        if (!window.connectionModule.adminWebSocket || window.connectionModule.adminWebSocket.readyState !== WebSocket.OPEN) {
            reject(new Error('WebSocket未连接'));
            return;
        }
        
        const requestId = `req-${Date.now()}-${requestCounter++}`;
        const message = {
            action: action,
            payload: payload,
            request_id: requestId
        };
        
        pendingRequests.set(requestId, { resolve, reject });
        
        try {
            window.connectionModule.adminWebSocket.send(JSON.stringify(message));
        } catch (error) {
            pendingRequests.delete(requestId);
            reject(new Error('发送消息失败'));
        }
        
        // 设置超时
        setTimeout(() => {
            if (pendingRequests.has(requestId)) {
                pendingRequests.delete(requestId);
                reject(new Error('请求超时'));
            }
        }, 10000); // 10秒超时
    });
}

// 导出函数和变量供其他模块使用
window.connectionModule = {
    updateConnectionStatus,
    apiRequest,
    connectToBackend,
    disconnectFromBackend,
    connectAdminWebSocket,
    sendAdminWsMessage,
    isConnected: false,
    backendUrl: '',
    authToken: '',
    adminWebSocket: null,
    getConnectionStatusDetails
};