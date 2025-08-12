// dashboard_web/js/modules/connection.js

// 全局变量
let backendUrl = '';
let authToken = '';
let isConnected = false;
let adminWebSocket = null;
let healthCheckInterval = null; // 添加健康检查定时器
let disconnectNotified = false; // 添加断连通知标志，防止重复提示

// DOM 元素
const connectionForm = document.getElementById('connectionForm');
const disconnectBtn = document.getElementById('disconnectBtn');
const connectionStatus = document.getElementById('connectionStatus');
const statusDot = connectionStatus.querySelector('.status-dot');
const statusText = connectionStatus.querySelector('.status-text');

// 更新连接状态显示
function updateConnectionStatus(connected, message = '') {
    isConnected = connected;
    // 重置断连通知标志
    disconnectNotified = false;
    
    if (connected) {
        statusDot.className = 'status-dot connected';
        statusText.textContent = message || '已连接';
        disconnectBtn.disabled = false;
        
        // 显示控制、配置和日志标签页
        document.querySelector('[data-tab="control"]').style.display = 'block';
        document.querySelector('[data-tab="config"]').style.display = 'block';
        document.querySelector('[data-tab="agent"]').style.display = 'block';
    } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = message || '未连接';
        disconnectBtn.disabled = true;
        
        // 隐藏控制、配置和日志标签页
        document.querySelector('[data-tab="control"]').style.display = 'none';
        document.querySelector('[data-tab="config"]').style.display = 'none';
        document.querySelector('[data-tab="agent"]').style.display = 'none';
        
        // 关闭管理WebSocket连接
        if (adminWebSocket) {
            try {
                adminWebSocket.close(1000, 'Client disconnecting'); // 正常关闭代码
            } catch (e) {
                console.error('关闭WebSocket时出错:', e);
            }
            adminWebSocket = null;
        }
    }
}

// 发送API请求的通用函数
async function apiRequest(endpoint, options = {}, skipConnectionCheck = false) {
    console.log('尝试发送API请求到:', endpoint); // 调试信息
    if (!isConnected && !skipConnectionCheck) {
        console.log('未连接到后端'); // 调试信息
        throw new Error('未连接到后端');
    }
    
    // 确保URL格式正确，避免双斜杠
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
    const url = backendUrl.endsWith('/') ? 
        `${backendUrl.slice(0, -1)}${cleanEndpoint}` : 
        `${backendUrl}${cleanEndpoint}`;
        
    console.log('完整URL:', url); // 调试信息
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // 只有当authToken存在且非空时才添加API Token头
    if (authToken && authToken.trim() !== '') {
        headers['X-API-Token'] = authToken;
        console.log('使用API Token:', authToken); // 调试信息
    }
    
    const config = {
        headers,
        ...options
    };
    
    console.log('请求配置:', config); // 调试信息
    try {
        const response = await fetch(url, config);
        console.log('响应:', response); // 调试信息
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('认证失败，请检查密码');
            }
            throw new Error(`请求失败: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API请求错误:', error);
        // 如果是网络错误且不是跳过连接检查的情况，认为连接已断开
        if ((error instanceof TypeError && error.message === 'Failed to fetch') && !skipConnectionCheck) {
            // 只有在还没有通知过断连的情况下才显示提示
            if (!disconnectNotified) {
                disconnectNotified = true;
                // 更新连接状态为断开
                updateConnectionStatus(false, '连接已断开');
                window.uiModule.showDisconnectDialog();
                // 切换到连接页面
                window.uiModule.switchTab('connection');
            }
        }
        throw error;
    }
}

// 连接到后端
async function connectToBackend(autoConnect = false) {
    console.log('开始连接到后端'); // 调试信息
    const url = document.getElementById('backendUrl').value.trim();
    const password = document.getElementById('password').value;
    
    console.log('后端URL:', url); // 调试信息
    console.log('密码:', password); // 调试信息
    
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
        statusDot.className = 'status-dot connecting';
        statusText.textContent = '连接中...';
        
        // 保存连接信息到localStorage
        backendUrl = url;
        authToken = password || ''; // 保存密码，即使是空字符串
        localStorage.setItem('backendUrl', backendUrl);
        if (authToken) {
            localStorage.setItem('authToken', authToken);
        }
        
        console.log('保存的后端URL:', backendUrl); // 调试信息
        console.log('保存的认证Token:', authToken); // 调试信息
        
        // 尝试获取后端状态以验证连接（跳过连接检查）
        const response = await apiRequest('/api/system/health', {}, true);
        
        console.log('健康检查响应:', response); // 调试信息
        
        if (response.status === 'healthy') {
            updateConnectionStatus(true, '已连接');
            if (!autoConnect) {
                window.uiModule.showToast('连接成功！', 'success');
            }
            // 更新直播状态
            window.streamModule.updateStreamStatus();
            // 连接管理WebSocket
            connectAdminWebSocket();
            // 默认切换到控制页面
            window.uiModule.switchTab('control');
            // 启动健康检查定时器（如果还没有）
            if (!healthCheckInterval) {
                healthCheckInterval = setInterval(async () => {
                    if (isConnected) {
                        try {
                            // 发送一个简单的健康检查请求
                            await apiRequest('/api/system/health', {}, true);
                        } catch (error) {
                            // 如果是网络错误，认为连接已断开
                            if (error instanceof TypeError && error.message === 'Failed to fetch') {
                                // 只有在还没有通知过断连的情况下才显示提示
                                if (!disconnectNotified) {
                                    disconnectNotified = true;
                                    updateConnectionStatus(false, '连接已断开');
                                    window.uiModule.showDisconnectDialog();
                                    // 切换到连接页面
                                    window.uiModule.switchTab('connection');
                                }
                            }
                        }
                    }
                }, 10000); // 每10秒检查一次连接健康状态
            }
        } else {
            throw new Error('后端服务不健康');
        }
    } catch (error) {
        console.error('连接失败:', error);
        updateConnectionStatus(false, '连接失败');
        if (!autoConnect) {
            window.uiModule.showToast(`连接失败: ${error.message}`, 'error');
        }
        // 清除健康检查定时器
        if (healthCheckInterval) {
            clearInterval(healthCheckInterval);
            healthCheckInterval = null;
        }
        // 切换到连接页面
        window.uiModule.switchTab('connection');
    }
}

// 断开连接
function disconnectFromBackend() {
    backendUrl = '';
    authToken = '';
    updateConnectionStatus(false, '已断开连接');
    window.uiModule.showToast('已断开连接', 'info');
    // 切换回连接页面
    window.uiModule.switchTab('connection');
    // 清除健康检查定时器
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
        healthCheckInterval = null;
    }
    // 重置断连通知标志
    disconnectNotified = false;
}

// 连接管理WebSocket
function connectAdminWebSocket() {
    if (adminWebSocket) {
        adminWebSocket.close();
    }
    
    try {
        const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws/admin';
        adminWebSocket = new WebSocket(wsUrl);
        
        adminWebSocket.onopen = () => {
            console.log('管理WebSocket连接已建立');
            // 不再需要调用fetchInitialContext()，因为WebSocket管理员端点会在连接时发送初始上下文
        };
        
        adminWebSocket.onmessage = (event) => {
            // 添加一个明显的调试信息
            console.log('WebSocket消息接收:', event.data.substring(0, 100) + (event.data.length > 100 ? '...' : ''));
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
                        // 处理Agent上下文 - 像日志一样逐条追加
                        const contextOutput = document.getElementById('contextOutput');
                        if (contextOutput && Array.isArray(data.messages)) {
                            // 清空现有内容
                            contextOutput.innerHTML = '';
                            
                            // 逐条添加消息
                            data.messages.forEach(msg => {
                                const itemDiv = document.createElement('div');
                                itemDiv.className = 'memory-item';
                                
                                // 从消息内容中提取角色和文本
                                let role = msg.role || 'system';
                                let content = msg.content || msg.text || '';
                                let timestamp = msg.timestamp || new Date().toISOString();
                                
                                // 如果是处理详情消息，需要特殊处理
                                if (msg.processing_details) {
                                    const details = typeof msg.processing_details === 'string' ? 
                                        JSON.parse(msg.processing_details) : msg.processing_details;
                                    content = details.final_response || content;
                                    role = 'assistant';
                                }
                                
                                const timestampDisplay = new Date(timestamp).toLocaleString();
                                const roleDisplay = role === 'user' ? '用户' : role === 'assistant' ? '助手' : role;
                                
                                itemDiv.innerHTML = `
                                    <div class="memory-content">
                                        <div><strong>[${roleDisplay}]</strong> ${content}</div>
                                        <div class="memory-time">${timestampDisplay}</div>
                                    </div>
                                `;
                                
                                contextOutput.appendChild(itemDiv);
                            });
                            
                            // 滚动到底部以显示最新内容
                            contextOutput.scrollTop = contextOutput.scrollHeight;
                        }
                        break;
                        
                    default:
                        console.warn('未知的WebSocket消息类型:', data.type);
                        console.log('完整消息内容:', data);
                }
            } catch (error) {
                console.error('解析WebSocket消息失败:', error);
            }
        };
        
        adminWebSocket.onerror = (error) => {
            console.error('管理WebSocket错误:', error);
            // 只有在还没有通知过断连的情况下才显示提示
            if (!disconnectNotified) {
                disconnectNotified = true;
                // 如果WebSocket出错，认为连接可能已断开
                updateConnectionStatus(false, '连接已断开');
                window.uiModule.showDisconnectDialog();
                // 切换到连接页面
                window.uiModule.switchTab('connection');
            }
        };
        
        adminWebSocket.onclose = () => {
            console.log('管理WebSocket连接已关闭');
            // 检查是否是异常关闭，如果是则更新连接状态
            if (isConnected && !disconnectNotified) {
                disconnectNotified = true;
                updateConnectionStatus(false, '连接已断开');
                window.uiModule.showDisconnectDialog();
                // 切换到连接页面
                window.uiModule.switchTab('connection');
            }
        };
    } catch (error) {
        console.error('连接管理WebSocket失败:', error);
        // 只有在还没有通知过断连的情况下才显示提示
        if (!disconnectNotified) {
            disconnectNotified = true;
            // 更新连接状态为断开
            updateConnectionStatus(false, '连接已断开');
            window.uiModule.showDisconnectDialog();
            // 切换到连接页面
            window.uiModule.switchTab('connection');
        }
    }
}

// 显示断连对话框
function showDisconnectDialog() {
    // 使用确认对话框显示断连信息，但只显示确定按钮
    showConfirmDialog('与后端的连接已断开，请重新连接。').then(() => {
        // 用户点击确定后，对话框会自动关闭
    });
    
    // 为了只显示确定按钮，我们需要修改对话框的HTML
    setTimeout(() => {
        if (confirmDialog) {
            const cancelButton = confirmDialog.querySelector('.confirm-cancel');
            const okButton = confirmDialog.querySelector('.confirm-ok');
            
            // 隐藏取消按钮
            if (cancelButton) {
                cancelButton.style.display = 'none';
            }
            
            // 修改确定按钮文本
            if (okButton) {
                okButton.textContent = '确定';
            }
            
            // 修改消息显示
            const messageEl = confirmDialog.querySelector('.confirm-message');
            if (messageEl) {
                messageEl.textContent = '与后端的连接已断开，请重新连接。';
            }
        }
    }, 10);
}

// 导出函数和变量供其他模块使用
window.connectionModule = {
    updateConnectionStatus,
    apiRequest,
    connectToBackend,
    disconnectFromBackend,
    connectAdminWebSocket,
    showDisconnectDialog,
    isConnected,
    backendUrl,
    authToken
};