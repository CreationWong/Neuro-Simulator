// dashboard_web/js/modules/connection.js

// 全局变量
let backendUrl = '';
let authToken = '';
let isConnected = false;
let adminWebSocket = null;
let healthCheckInterval = null; // 保留健康检查定时器，但降低频率
let disconnectNotified = false; // 添加断连通知标志，防止重复提示
let connectionCheckWebSocket = null; // 专门用于连接检查的WebSocket

// 添加一个函数来获取当前连接状态的详细信息
function getConnectionStatusDetails() {
    return {
        isConnected: window.connectionModule.isConnected,  // 使用模块导出的isConnected
        backendUrl: window.connectionModule.backendUrl,
        authToken: window.connectionModule.authToken ? '***' : '', // 隐藏实际的token值
        adminWebSocketReadyState: window.connectionModule.adminWebSocket ? window.connectionModule.adminWebSocket.readyState : 'null',
        connectionCheckWebSocketReadyState: window.connectionModule.connectionCheckWebSocket ? window.connectionModule.connectionCheckWebSocket.readyState : 'null',
        healthCheckInterval: window.connectionModule.healthCheckInterval ? 'active' : 'null',
        disconnectNotified: window.connectionModule.disconnectNotified
    }
};

// 处理心跳消息
function handleHeartbeatMessage(data) {
    // 心跳消息不需要特殊处理，只是用于保持WebSocket连接活跃
}

// DOM 元素
const connectionForm = document.getElementById('connectionForm');
const disconnectBtn = document.getElementById('disconnectBtn');
const connectionStatus = document.getElementById('connectionStatus');
const statusDot = connectionStatus.querySelector('.status-dot');
const statusText = connectionStatus.querySelector('.status-text');

// 更新连接状态显示
function updateConnectionStatus(connected, message = '') {
    window.connectionModule.isConnected = connected;
    // 重置断连通知标志
    window.connectionModule.disconnectNotified = false;
    
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
        const agentTab = document.querySelector('[data-tab="agent"]');
        if (controlTab) controlTab.style.display = 'block';
        if (configTab) configTab.style.display = 'block';
        if (agentTab) agentTab.style.display = 'block';
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
        const agentTab = document.querySelector('[data-tab="agent"]');
        if (controlTab) controlTab.style.display = 'none';
        if (configTab) configTab.style.display = 'none';
        if (agentTab) agentTab.style.display = 'none';
        
        // 关闭管理WebSocket连接
        if (window.connectionModule.adminWebSocket) {
            try {
                window.connectionModule.adminWebSocket.close(1000, 'Client disconnecting'); // 正常关闭代码
            } catch (e) {
                console.error('关闭管理WebSocket时出错:', e);
            }
            window.connectionModule.adminWebSocket = null;
        }
        
        // 关闭连接检查WebSocket连接
        if (window.connectionModule.connectionCheckWebSocket) {
            try {
                window.connectionModule.connectionCheckWebSocket.close(1000, 'Client disconnecting'); // 正常关闭代码
            } catch (e) {
                console.error('关闭连接检查WebSocket时出错:', e);
            }
            window.connectionModule.connectionCheckWebSocket = null;
        }
    }
}

// 发送API请求的通用函数
async function apiRequest(endpoint, options = {}, skipConnectionCheck = false) {
    if (!window.connectionModule.isConnected && !skipConnectionCheck) {
        throw new Error('未连接到后端');
    }
    
    // 确保URL格式正确，避免双斜杠
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
    const url = window.connectionModule.backendUrl.endsWith('/') ? 
        `${window.connectionModule.backendUrl.slice(0, -1)}${cleanEndpoint}` : 
        `${window.connectionModule.backendUrl}${cleanEndpoint}`;
        
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // 只有当authToken存在且非空时才添加API Token头
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
            // 特别处理401错误
            if (response.status === 401) {
                throw new Error('认证失败，请检查密码');
            }
            // 对于其他错误状态码，我们不一定会断开连接，除非是网络问题
            throw new Error(`请求失败: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        // 如果是网络错误且不是跳过连接检查的情况，认为连接已断开
        if ((error instanceof TypeError && error.message === 'Failed to fetch') && !skipConnectionCheck) {
            // 断开连接
            window.connectionModule.disconnectNotified = true;
            // 更新连接状态为断开
            window.connectionModule.updateConnectionStatus(false, '连接已断开');
            // 显示断连对话框
            if (window.uiModule && window.uiModule.showDisconnectDialog) {
                window.uiModule.showDisconnectDialog();
            }
            // 切换到连接页面
            if (window.uiModule && window.uiModule.switchTab) {
                window.uiModule.switchTab('connection');
            }
        }
        // 对于其他错误，我们不改变连接状态
        throw error;
    }
}

// 连接到后端
async function connectToBackend(autoConnect = false) {
    const url = document.getElementById('backendUrl').value.trim();
    const password = document.getElementById('password').value;
    
    if (!url && !autoConnect) {
        window.uiModule.showToast('请输入后端地址', 'warning');
        return;
    }
    
    if (!url && autoConnect) {
        // 自动连接时如果没有URL则不执行连接
        return;
    }
    
    try {
        // 更新状态为连接中
        const statusDot = document.getElementById('connectionStatus').querySelector('.status-dot');
        const statusText = document.getElementById('connectionStatus').querySelector('.status-text');
        statusDot.className = 'status-dot connecting';
        statusText.textContent = '连接中...';
        
        // 保存连接信息到localStorage
        window.connectionModule.backendUrl = url;
        window.connectionModule.authToken = password || ''; // 保存密码，即使是空字符串
        localStorage.setItem('backendUrl', window.connectionModule.backendUrl);
        if (window.connectionModule.authToken) {
            localStorage.setItem('authToken', window.connectionModule.authToken);
        }
        
        // 尝试获取后端状态以验证连接（跳过连接检查）
        const response = await window.connectionModule.apiRequest('/api/system/health', {}, true);
        
        if (response.status === 'healthy') {
            window.connectionModule.updateConnectionStatus(true, '已连接');
            if (!autoConnect) {
                window.uiModule.showToast('连接成功！', 'success');
            }
            // 更新直播状态
            window.streamModule.updateStreamStatus();
            // 连接管理WebSocket
            window.connectionModule.connectAdminWebSocket();
            // 默认切换到控制页面
            window.uiModule.switchTab('control');
            // 启动健康检查定时器（如果还没有），但降低频率到每30秒一次
            if (!window.connectionModule.healthCheckInterval) {
                window.connectionModule.healthCheckInterval = setInterval(async () => {
                    if (window.connectionModule.isConnected) {
                        try {
                            // 发送一个简单的健康检查请求
                            await window.connectionModule.apiRequest('/api/system/health', {}, true);
                        } catch (error) {
                            // 如果是网络错误，认为连接已断开
                            if (error instanceof TypeError && error.message === 'Failed to fetch') {
                                // 断开连接
                                window.connectionModule.disconnectNotified = true;
                                // 更新连接状态为断开
                                window.connectionModule.updateConnectionStatus(false, '连接已断开');
                                // 显示断连对话框
                                if (window.uiModule && window.uiModule.showDisconnectDialog) {
                                    window.uiModule.showDisconnectDialog();
                                }
                                // 切换到连接页面
                                if (window.uiModule && window.uiModule.switchTab) {
                                    window.uiModule.switchTab('connection');
                                }
                            }
                        }
                    }
                }, 30000); // 每30秒检查一次连接健康状态，降低频率
            }
            
            // 连接检查WebSocket
            window.connectionModule.connectConnectionCheckWebSocket();
        } else {
            throw new Error('后端服务不健康');
        }
    } catch (error) {
        console.error('连接失败:', error);
        window.connectionModule.updateConnectionStatus(false, '连接失败');
        if (!autoConnect) {
            window.uiModule.showToast(`连接失败: ${error.message}`, 'error');
        }
        // 清除健康检查定时器
        if (window.connectionModule.healthCheckInterval) {
            clearInterval(window.connectionModule.healthCheckInterval);
            window.connectionModule.healthCheckInterval = null;
        }
        // 切换到连接页面
        window.uiModule.switchTab('connection');
    }
}

// 断开连接
function disconnectFromBackend() {
    window.connectionModule.backendUrl = '';
    window.connectionModule.authToken = '';
    window.connectionModule.updateConnectionStatus(false, '已断开连接');
    window.uiModule.showToast('已断开连接', 'info');
    // 切换回连接页面
    window.uiModule.switchTab('connection');
    // 清除健康检查定时器
    if (window.connectionModule.healthCheckInterval) {
        clearInterval(window.connectionModule.healthCheckInterval);
        window.connectionModule.healthCheckInterval = null;
    }
    // 重置断连通知标志
    window.connectionModule.disconnectNotified = false;
}

// 连接管理WebSocket
function connectAdminWebSocket() {
    if (window.connectionModule.adminWebSocket) {
        window.connectionModule.adminWebSocket.close();
    }
    
    try {
        const wsUrl = window.connectionModule.backendUrl.replace(/^http/, 'ws') + '/ws/admin';
        window.connectionModule.adminWebSocket = new WebSocket(wsUrl);
        
        window.connectionModule.adminWebSocket.onopen = () => {
            console.log('管理WebSocket连接已建立');
            // 不再需要调用fetchInitialContext()，因为WebSocket管理员端点会在连接时发送初始上下文
        };
        
        window.connectionModule.adminWebSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                // 处理不同类型的数据
                switch (data.type) {
                    case 'server_log':
                        // 处理服务器日志
                        const serverLogsOutput = document.getElementById('serverLogsOutput');
                        if (serverLogsOutput) {
                            const logDiv = document.createElement('div');
                            logDiv.className = 'log-entry log-server';
                            
                            // 确保data.data存在
                            const content = data.data || data.content || data.message || 'Unknown server log message';
                            
                            // 根据日志级别设置样式
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
                            
                            // 保持只显示最新的1000行日志
                            const logEntries = serverLogsOutput.querySelectorAll('.log-entry');
                            if (logEntries.length > 1000) {
                                // 删除多余的日志条目
                                for (let i = 0; i < logEntries.length - 1000; i++) {
                                    logEntries[i].remove();
                                }
                            }
                            
                            // 滚动到底部以显示最新日志
                            serverLogsOutput.scrollTop = serverLogsOutput.scrollHeight;
                        }
                        break;
                        
                    case 'agent_log':
                        // 处理Agent日志
                        const agentLogsOutput = document.getElementById('agentLogsOutput');
                        if (agentLogsOutput) {
                            const logDiv = document.createElement('div');
                            logDiv.className = 'log-entry log-agent';
                            
                            // 确保data.data存在
                            const content = data.data || data.content || data.message || 'Unknown agent log message';
                            
                            // 根据日志级别设置样式
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
                            agentLogsOutput.appendChild(logDiv);
                            
                            // 保持只显示最新的1000行日志
                            const logEntries = agentLogsOutput.querySelectorAll('.log-entry');
                            if (logEntries.length > 1000) {
                                // 删除多余的日志条目
                                for (let i = 0; i < logEntries.length - 1000; i++) {
                                    logEntries[i].remove();
                                }
                            }
                            
                            // 滚动到底部以显示最新日志
                            agentLogsOutput.scrollTop = agentLogsOutput.scrollHeight;
                        }
                        break;
                        
                    case 'agent_context':
                        // 处理Agent上下文 - 实时更新显示
                        displayAgentContext(data.messages);
                        break;
                        
                    case 'heartbeat':
                        // 心跳消息，不需要特殊处理
                        handleHeartbeatMessage(data);
                        break;
                        
                    default:
                        console.warn('未知的WebSocket消息类型:', data.type);
                }
            } catch (error) {
                console.error('解析WebSocket消息失败:', error);
            }
        };
        
        window.connectionModule.adminWebSocket.onerror = (error) => {
            console.error('管理WebSocket错误:', error);
            // WebSocket错误不应该影响API连接状态
            // 只需要记录错误并尝试重新连接
            console.log('WebSocket错误，但API连接状态保持不变');
        };
        
        window.connectionModule.adminWebSocket.onclose = () => {
            console.log('管理WebSocket连接已关闭');
            // WebSocket关闭不应该影响API连接状态
            // 只需要记录并尝试重新连接
            console.log('WebSocket关闭，但API连接状态保持不变');
        };
    } catch (error) {
        console.error('连接管理WebSocket失败:', error);
        // WebSocket连接失败不应该影响API连接状态
        // 只需要记录错误
        console.log('WebSocket连接失败，但API连接状态保持不变');
    }
}

// 连接检查WebSocket（用于检测连接状态）
function connectConnectionCheckWebSocket() {
    // 如果已存在连接检查WebSocket，先关闭它
    if (window.connectionModule.connectionCheckWebSocket) {
        window.connectionModule.connectionCheckWebSocket.close();
    }
    
    try {
        const wsUrl = window.connectionModule.backendUrl.replace(/^http/, 'ws') + '/ws/admin';
        window.connectionModule.connectionCheckWebSocket = new WebSocket(wsUrl);
        
        window.connectionModule.connectionCheckWebSocket.onopen = () => {
            console.log('连接检查WebSocket连接已建立');
        };
        
        window.connectionModule.connectionCheckWebSocket.onmessage = (event) => {
            // 连接检查WebSocket只用于检测连接状态，不处理消息
            // 但我们需要监听消息以保持连接活跃
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'heartbeat') {
                    // 心跳消息，不需要特殊处理
                }
            } catch (error) {
                console.error('解析连接检查WebSocket消息失败:', error);
            }
        };
        
        window.connectionModule.connectionCheckWebSocket.onerror = (error) => {
            console.error('连接检查WebSocket错误:', error);
            // WebSocket错误时，立即断开连接
            handleWebSocketDisconnect();
        };
        
        window.connectionModule.connectionCheckWebSocket.onclose = (event) => {
            console.log('连接检查WebSocket连接已关闭，代码:', event.code, '原因:', event.reason);
            // WebSocket关闭时，立即断开连接
            handleWebSocketDisconnect();
        };
    } catch (error) {
        console.error('连接检查WebSocket失败:', error);
        // WebSocket连接失败时，立即断开连接
        handleWebSocketDisconnect();
    }
}

// 处理WebSocket断开连接
function handleWebSocketDisconnect() {
    // 检查是否已经通知过断连，防止重复通知
    if (!window.connectionModule.disconnectNotified) {
        window.connectionModule.disconnectNotified = true;
        // 更新连接状态为断开
        window.connectionModule.updateConnectionStatus(false, '连接已断开');
        // 显示断连对话框
        if (window.uiModule && window.uiModule.showDisconnectDialog) {
            window.uiModule.showDisconnectDialog();
        }
        // 切换到连接页面
        if (window.uiModule && window.uiModule.switchTab) {
            window.uiModule.switchTab('connection');
        }
    }
}

// 导出函数和变量供其他模块使用
window.connectionModule = {
    updateConnectionStatus,
    apiRequest,
    connectToBackend,
    disconnectFromBackend,
    connectAdminWebSocket,
    connectConnectionCheckWebSocket,
    handleHeartbeatMessage,
    isConnected: false,
    backendUrl: '',
    authToken: '',
    adminWebSocket: null,
    connectionCheckWebSocket: null,
    healthCheckInterval: null,
    disconnectNotified: false,
    getConnectionStatusDetails
};