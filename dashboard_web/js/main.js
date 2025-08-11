// dashboard_web/js/main.js

// 全局变量
let backendUrl = '';
let authToken = '';
let isConnected = false;
let logWebSocket = null;
let currentConfig = {}; // 存储当前配置
let toastContainer = null; // 横幅提示容器
let confirmDialog = null; // 确认对话框元素
let confirmResolver = null; // 确认对话框的Promise resolver
let healthCheckInterval = null; // 添加健康检查定时器
let disconnectNotified = false; // 添加断连通知标志，防止重复提示
let modalDialog = null; // 模态对话框元素

// DOM 元素
const connectionForm = document.getElementById('connectionForm');
const disconnectBtn = document.getElementById('disconnectBtn');
const connectionStatus = document.getElementById('connectionStatus');
const statusDot = connectionStatus.querySelector('.status-dot');
const statusText = connectionStatus.querySelector('.status-text');

// 直播控制相关元素
const streamStatus = document.getElementById('streamStatus');
const startStreamBtn = document.getElementById('startStreamBtn');
const stopStreamBtn = document.getElementById('stopStreamBtn');
const restartStreamBtn = document.getElementById('restartStreamBtn');

// 配置管理相关元素
const configForm = document.getElementById('configForm');
const resetConfigBtn = document.getElementById('resetConfigBtn');

// 日志显示相关元素
const logsOutput = document.getElementById('logsOutput');
const logLines = document.getElementById('logLines');
const refreshLogsBtn = document.getElementById('refreshLogsBtn');

// Agent 控制相关元素
const refreshAgentLogsBtn = document.getElementById('refreshAgentLogsBtn');
const clearAgentLogsBtn = document.getElementById('clearAgentLogsBtn');
const agentLogsOutput = document.getElementById('agentLogsOutput');
const refreshTempMemoryBtn = document.getElementById('refreshTempMemoryBtn');
const clearTempMemoryBtn = document.getElementById('clearTempMemoryBtn');
const tempMemoryOutput = document.getElementById('tempMemoryOutput');
const refreshCoreMemoryBtn = document.getElementById('refreshCoreMemoryBtn');
const addCoreMemoryBlockBtn = document.getElementById('addCoreMemoryBlockBtn');
const coreMemoryOutput = document.getElementById('coreMemoryOutput');
const refreshToolsBtn = document.getElementById('refreshToolsBtn');
const toolsOutput = document.getElementById('toolsOutput');
const toolName = document.getElementById('toolName');
const aiToolName = document.getElementById('aiToolName');
const connectToolBtn = document.getElementById('connectToolBtn');

// Agent 标签页相关元素
const agentTabBtns = document.querySelectorAll('.agent-tab-btn');
const agentTabContents = document.querySelectorAll('.agent-tab-content');

// 模态对话框相关元素
const addMemoryBlockDialog = document.getElementById('addMemoryBlockDialog');
const addMemoryBlockForm = document.getElementById('addMemoryBlockForm');
const cancelAddMemoryBtn = document.getElementById('cancelAddMemoryBtn');
const closeDialogBtns = document.querySelectorAll('.close-btn');

// 标签页相关元素
const navTabs = document.querySelectorAll('.nav-tab');
const tabContents = document.querySelectorAll('.tab-content');

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
        document.querySelector('[data-tab="logs"]').style.display = 'block';
    } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = message || '未连接';
        disconnectBtn.disabled = true;
        
        // 隐藏控制、配置和日志标签页
        document.querySelector('[data-tab="control"]').style.display = 'none';
        document.querySelector('[data-tab="config"]').style.display = 'none';
        document.querySelector('[data-tab="agent"]').style.display = 'none';
        document.querySelector('[data-tab="logs"]').style.display = 'none';
        
        // 关闭日志WebSocket连接
        if (logWebSocket) {
            try {
                logWebSocket.close(1000, 'Client disconnecting'); // 正常关闭代码
            } catch (e) {
                console.error('关闭WebSocket时出错:', e);
            }
            logWebSocket = null;
        }
    }
}

// 切换标签页
function switchTab(tabName) {
    // 更新标签页激活状态
    navTabs.forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // 显示对应的内容区域
    tabContents.forEach(content => {
        if (content.id === `${tabName}-tab`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
}

// 切换Agent标签页
function switchAgentTab(tabName) {
    // 更新标签页激活状态
    agentTabBtns.forEach(tab => {
        if (tab.dataset.agentTab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // 显示对应的内容区域
    agentTabContents.forEach(content => {
        if (content.id === `${tabName}-agent-tab`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
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
                showDisconnectDialog();
                // 切换到连接页面
                switchTab('connection');
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
        showToast('请输入后端地址', 'warning');
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
                showToast('连接成功！', 'success');
            }
            // 更新直播状态
            updateStreamStatus();
            // 连接日志WebSocket
            connectLogWebSocket();
            // 默认切换到控制页面
            switchTab('control');
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
                                    showDisconnectDialog();
                                    // 切换到连接页面
                                    switchTab('connection');
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
            showToast(`连接失败: ${error.message}`, 'error');
        }
        // 清除健康检查定时器
        if (healthCheckInterval) {
            clearInterval(healthCheckInterval);
            healthCheckInterval = null;
        }
        // 切换到连接页面
        switchTab('connection');
    }
}

// 断开连接
function disconnectFromBackend() {
    backendUrl = '';
    authToken = '';
    updateConnectionStatus(false, '已断开连接');
    showToast('已断开连接', 'info');
    // 切换回连接页面
    switchTab('connection');
    // 清除健康检查定时器
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
        healthCheckInterval = null;
    }
    // 重置断连通知标志
    disconnectNotified = false;
}

// 更新直播状态
async function updateStreamStatus() {
    try {
        const status = await apiRequest('/api/stream/status');
        streamStatus.textContent = status.is_running ? '运行中' : '已停止';
        streamStatus.style.color = status.is_running ? '#4CAF50' : '#F44336';
    } catch (error) {
        streamStatus.textContent = '无法获取状态';
        streamStatus.style.color = '#F44336';
        console.error('获取直播状态失败:', error);
        
        // 检查是否是连接问题，如果是则更新连接状态
        if (error.message.includes('Failed to fetch') || error.message.includes('未连接到后端')) {
            // 只有在还没有通知过断连的情况下才显示提示
            if (!disconnectNotified) {
                disconnectNotified = true;
                // 显示断连提示对话框
                showDisconnectDialog();
            }
            // 更新连接状态为断开
            updateConnectionStatus(false, '连接已断开');
            // 切换到连接页面
            switchTab('connection');
        }
    }
}

// 开始直播
async function startStream() {
    const confirmed = await showConfirmDialog('确定要开始直播吗？');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await apiRequest('/api/stream/start', { method: 'POST' });
        showToast(response.message, 'success');
        updateStreamStatus();
    } catch (error) {
        showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 停止直播
async function stopStream() {
    const confirmed = await showConfirmDialog('确定要停止直播吗？');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await apiRequest('/api/stream/stop', { method: 'POST' });
        showToast(response.message, 'success');
        updateStreamStatus();
    } catch (error) {
        showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 重启直播
async function restartStream() {
    const confirmed = await showConfirmDialog('确定要重启直播吗？这将停止并重新启动直播进程。');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await apiRequest('/api/stream/restart', { method: 'POST' });
        showToast(response.message, 'success');
        updateStreamStatus();
    } catch (error) {
        showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 重置Agent记忆
async function resetAgentMemory() {
    const confirmed = await showConfirmDialog('确定要重置Agent的记忆吗？这将清除所有临时记忆和对话历史。');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await apiRequest('/api/agent/reset_memory', { method: 'POST' });
        showToast(response.message, 'success');
        // 刷新记忆显示
        refreshTempMemory();
        refreshCoreMemory();
    } catch (error) {
        showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 将配置对象转换为表单值
function configToForm(config) {
    // 遍历表单中的每个输入元素
    const formElements = configForm.querySelectorAll('input, select, textarea');
    
    formElements.forEach(element => {
        const name = element.name;
        if (!name) return;
        
        // 解析嵌套属性路径 (例如: stream_metadata.stream_title)
        const keys = name.split('.');
        let value = config;
        
        // 通过路径获取配置值
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                value = undefined;
                break;
            }
        }
        
        // 根据元素类型设置值
        if (value !== undefined) {
            if (element.type === 'checkbox') {
                element.checked = value;
            } else if (Array.isArray(value)) {
                // 对于数组类型，将其转换为逗号分隔的字符串
                element.value = value.join(', ');
            } else {
                element.value = value;
            }
        }
    });
}

// 将表单值转换为配置对象
function formToConfig() {
    const config = {};
    
    // 遍历表单中的每个输入元素
    const formElements = configForm.querySelectorAll('input, select, textarea');
    
    formElements.forEach(element => {
        const name = element.name;
        if (!name) return;
        
        // 解析嵌套属性路径 (例如: stream_metadata.stream_title)
        const keys = name.split('.');
        let obj = config;
        
        // 创建嵌套对象结构
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!(key in obj)) {
                obj[key] = {};
            }
            obj = obj[key];
        }
        
        // 设置最终值
        const lastKey = keys[keys.length - 1];
        if (element.type === 'checkbox') {
            obj[lastKey] = element.checked;
        } else if (element.type === 'number') {
            const numValue = parseFloat(element.value);
            obj[lastKey] = isNaN(numValue) ? element.value : numValue;
        } else if (element.type === 'text' && 
                  (element.name.endsWith('.stream_tags') || 
                   element.name.endsWith('.username_blocklist') ||
                   element.name.endsWith('.username_pool'))) {
            // 处理数组类型字段
            obj[lastKey] = element.value.split(',').map(item => item.trim()).filter(item => item);
        } else {
            obj[lastKey] = element.value;
        }
    });
    
    return config;
}

// 获取配置
async function getConfig() {
    try {
        const config = await apiRequest('/api/configs');
        currentConfig = config; // 保存当前配置
        configToForm(config); // 填充表单
        
        // 检查是否有未显示的配置项
        checkForMissingConfigItems(config);
    } catch (error) {
        console.error('获取配置失败:', error);
        showToast(`获取配置失败: ${error.message}\n\n请检查后端日志以获取更多信息。`, 'error');
    }
}

// 检查是否有未在面板中显示的配置项
function checkForMissingConfigItems(config) {
    // 定义应该在面板中显示的配置项路径
    const expectedPaths = [
        'stream_metadata.stream_title',
        'stream_metadata.stream_category',
        'stream_metadata.stream_tags',
        'neuro_behavior.input_chat_sample_size',
        'neuro_behavior.post_speech_cooldown_sec',
        'neuro_behavior.initial_greeting',
        'audience_simulation.llm_provider',
        'audience_simulation.gemini_model',
        'audience_simulation.openai_model',
        'audience_simulation.llm_temperature',
        'audience_simulation.chat_generation_interval_sec',
        'audience_simulation.chats_per_batch',
        'audience_simulation.max_output_tokens',
        'audience_simulation.username_blocklist',
        'audience_simulation.username_pool',
        'agent.agent_provider',
        'agent.agent_model',
        'performance.neuro_input_queue_max_size',
        'performance.audience_chat_buffer_max_size',
        'performance.initial_chat_backlog_limit'
    ];
    
    // 收集实际配置中的所有路径
    const actualPaths = [];
    
    function collectPaths(obj, prefix = '') {
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const fullPath = prefix ? `${prefix}.${key}` : key;
                if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                    collectPaths(obj[key], fullPath);
                } else {
                    actualPaths.push(fullPath);
                }
            }
        }
    }
    
    collectPaths(config);
    
    // 检查是否有未显示的配置项
    const missingPaths = actualPaths.filter(path => 
        !expectedPaths.includes(path) && 
        !path.startsWith('api_keys') && 
        !path.startsWith('tts') && 
        !path.startsWith('server') &&
        path !== 'stream_metadata.streamer_nickname'
    );
    
    if (missingPaths.length > 0) {
        console.warn('发现未在面板中显示的配置项:', missingPaths);
        // 可以在这里添加更多用户提示逻辑
    }
}

// 重置配置表单
function resetConfigForm() {
    configToForm(currentConfig); // 使用保存的配置重置表单
}

// 保存配置
async function saveConfig(e) {
    e.preventDefault(); // 阻止表单默认提交行为
    
    try {
        const config = formToConfig(); // 从表单获取配置
        await apiRequest('/api/configs', {
            method: 'PATCH',
            body: JSON.stringify(config)
        });
        showToast('配置保存成功', 'success');
        // 更新当前配置
        currentConfig = {...currentConfig, ...config};
    } catch (error) {
        console.error('保存配置失败:', error);
        showToast(`保存配置失败: ${error.message}\n\n请检查后端日志以获取更多信息。`, 'error');
    }
}

// 获取日志
async function getLogs() {
    try {
        const lines = logLines.value;
        const response = await apiRequest(`/api/logs?lines=${lines}`);
        logsOutput.textContent = response.logs.join('\n');
        // 滚动到底部
        logsOutput.scrollTop = logsOutput.scrollHeight;
    } catch (error) {
        logsOutput.textContent = `获取日志失败: ${error.message}`;
    }
}

// 连接日志WebSocket
function connectLogWebSocket() {
    if (logWebSocket) {
        logWebSocket.close();
    }
    
    try {
        const wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws/logs';
        logWebSocket = new WebSocket(wsUrl);
        
        logWebSocket.onopen = () => {
            console.log('日志WebSocket连接已建立');
        };
        
        logWebSocket.onmessage = (event) => {
            const logEntry = event.data;
            // 添加新日志到输出区域
            logsOutput.textContent += logEntry + '\n';
            // 保持滚动到底部（如果已经在底部）
            if (logsOutput.scrollTop + logsOutput.clientHeight >= logsOutput.scrollHeight - 10) {
                logsOutput.scrollTop = logsOutput.scrollHeight;
            }
            // 限制日志行数以防止内存问题
            const lines = logsOutput.textContent.split('\n');
            if (lines.length > 1000) {
                logsOutput.textContent = lines.slice(-1000).join('\n');
            }
        };
        
        logWebSocket.onerror = (error) => {
            console.error('日志WebSocket错误:', error);
            // 只有在还没有通知过断连的情况下才显示提示
            if (!disconnectNotified) {
                disconnectNotified = true;
                // 如果WebSocket出错，认为连接可能已断开
                updateConnectionStatus(false, '连接已断开');
                showDisconnectDialog();
                // 切换到连接页面
                switchTab('connection');
            }
        };
        
        logWebSocket.onclose = () => {
            console.log('日志WebSocket连接已关闭');
            // 检查是否是异常关闭，如果是则更新连接状态
            if (isConnected && !disconnectNotified) {
                disconnectNotified = true;
                updateConnectionStatus(false, '连接已断开');
                showDisconnectDialog();
                // 切换到连接页面
                switchTab('connection');
            }
        };
    } catch (error) {
        console.error('连接日志WebSocket失败:', error);
        // 只有在还没有通知过断连的情况下才显示提示
        if (!disconnectNotified) {
            disconnectNotified = true;
            // 更新连接状态为断开
            updateConnectionStatus(false, '连接已断开');
            showDisconnectDialog();
            // 切换到连接页面
            switchTab('connection');
        }
    }
}

// 刷新日志
function refreshLogs() {
    if (isConnected) {
        getLogs();
    }
}

// Agent 相关功能

// 切换Agent标签页
function switchAgentTab(tabName) {
    // 更新标签页激活状态
    agentTabBtns.forEach(tab => {
        if (tab.dataset.agentTab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // 显示对应的内容区域
    agentTabContents.forEach(content => {
        if (content.id === `${tabName}-agent-tab`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
}

// 刷新Agent日志
async function refreshAgentLogs() {
    if (!isConnected) return;
    
    try {
        console.log("DEBUG: Refreshing agent logs");
        // 获取Agent日志
        const response = await apiRequest('/api/agent/logs?lines=100');
        console.log("DEBUG: Received agent logs response:", response);
        displayAgentLogs(response.logs);
    } catch (error) {
        console.error("DEBUG: Error fetching agent logs:", error);
        showToast(`获取Agent日志失败: ${error.message}`, 'error');
    }
}

// 显示Agent日志
function displayAgentLogs(logs) {
    if (!agentLogsOutput) return;
    
    // 清空现有内容
    agentLogsOutput.innerHTML = '';
    
    // 直接显示日志内容，每行一个div，最新日志在底部
    logs.forEach(logEntry => {
        const logDiv = document.createElement('div');
        logDiv.className = 'log-entry';
        
        // 根据日志级别设置样式
        if (logEntry.includes('ERROR') || logEntry.includes('Error')) {
            logDiv.classList.add('log-error');
        } else if (logEntry.includes('WARNING') || logEntry.includes('Warning')) {
            logDiv.classList.add('log-warning');
        } else if (logEntry.includes('DEBUG') || logEntry.includes('Debug')) {
            logDiv.classList.add('log-debug');
        } else {
            logDiv.classList.add('log-info');
        }
        
        logDiv.textContent = logEntry;
        agentLogsOutput.appendChild(logDiv);
    });
    
    // 滚动到底部以显示最新日志
    agentLogsOutput.scrollTop = agentLogsOutput.scrollHeight;
}

// 清空Agent日志
async function clearAgentLogs() {
    const confirmed = await showConfirmDialog('确定要清空Agent日志吗？');
    if (!confirmed) return;
    
    try {
        // 这里应该调用一个清空日志的API端点
        // 暂时我们只是清空显示区域
        agentLogsOutput.innerHTML = '';
        showToast('Agent日志已清空', 'success');
    } catch (error) {
        showToast(`清空Agent日志失败: ${error.message}`, 'error');
    }
}

// 刷新临时记忆
async function refreshTempMemory() {
    if (!isConnected) return;
    
    try {
        // 获取完整的临时记忆内容
        const tempMemory = await apiRequest('/api/agent/memory/temp');
        displayTempMemory(tempMemory);
    } catch (error) {
        showToast(`获取临时记忆失败: ${error.message}`, 'error');
    }
}

// 显示临时记忆
function displayTempMemory(messages) {
    if (!tempMemoryOutput) return;
    
    tempMemoryOutput.innerHTML = '';
    
    messages.forEach((msg, index) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'memory-item';
        
        const timestamp = new Date(msg.timestamp).toLocaleString();
        
        itemDiv.innerHTML = `
            <div class="memory-content">
                <div><strong>[${msg.role}]</strong> ${msg.content || msg.text || ''}</div>
                <div class="memory-time">${timestamp}</div>
            </div>
            <div class="memory-actions">
                <button class="btn small danger delete-temp-memory-btn" data-index="${index}">删除</button>
            </div>
        `;
        
        tempMemoryOutput.appendChild(itemDiv);
    });
    
    // 绑定删除按钮事件
    const deleteButtons = tempMemoryOutput.querySelectorAll('.delete-temp-memory-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = e.target.dataset.index;
            deleteTempMemoryItem(index);
        });
    });
}

// 删除临时记忆项
async function deleteTempMemoryItem(index) {
    const confirmed = await showConfirmDialog('确定要删除这条临时记忆吗？');
    if (!confirmed) return;
    
    try {
        // 对于builtin agent，我们无法直接删除单个消息
        // 这里我们简单地从显示中移除
        const items = tempMemoryOutput.querySelectorAll('.memory-item');
        if (items[index]) {
            items[index].remove();
            showToast('记忆项已删除', 'success');
        }
    } catch (error) {
        showToast(`删除记忆项失败: ${error.message}`, 'error');
    }
}

// 清空临时记忆
async function clearTempMemory() {
    const confirmed = await showConfirmDialog('确定要清空所有临时记忆吗？');
    if (!confirmed) return;
    
    try {
        await apiRequest('/api/agent/memory/temp', { method: 'DELETE' });
        tempMemoryOutput.innerHTML = '';
        showToast('临时记忆已清空', 'success');
    } catch (error) {
        showToast(`清空临时记忆失败: ${error.message}`, 'error');
    }
}

// 刷新核心记忆
async function refreshCoreMemory() {
    if (!isConnected) return;
    
    try {
        const blocks = await apiRequest('/api/agent/memory/blocks');
        displayCoreMemory(blocks);
    } catch (error) {
        showToast(`获取核心记忆失败: ${error.message}`, 'error');
    }
}

// 显示核心记忆
function displayCoreMemory(blocks) {
    if (!coreMemoryOutput) return;
    
    coreMemoryOutput.innerHTML = '';
    
    // 遍历所有记忆块
    Object.values(blocks).forEach(block => {
        const blockDiv = document.createElement('div');
        blockDiv.className = 'memory-block';
        blockDiv.dataset.blockId = block.id;
        
        blockDiv.innerHTML = `
            <div class="memory-block-header">
                <h4>${block.title}</h4>
                <div class="memory-block-actions">
                    <button class="btn small secondary edit-memory-btn" data-block-id="${block.id}">编辑</button>
                    <button class="btn small danger delete-memory-btn" data-block-id="${block.id}">删除</button>
                </div>
            </div>
            <div class="memory-block-description">${block.description}</div>
            <div class="memory-block-content">
                <ul>
                    ${block.content.map(item => `<li>${item}</li>`).join('')}
                </ul>
            </div>
        `;
        
        coreMemoryOutput.appendChild(blockDiv);
    });
    
    // 绑定编辑和删除按钮事件
    const editButtons = coreMemoryOutput.querySelectorAll('.edit-memory-btn');
    editButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const blockId = e.target.dataset.blockId;
            editMemoryBlock(blockId);
        });
    });
    
    const deleteButtons = coreMemoryOutput.querySelectorAll('.delete-memory-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const blockId = e.target.dataset.blockId;
            deleteMemoryBlock(blockId);
        });
    });
}

// 编辑记忆块
async function editMemoryBlock(blockId) {
    // 获取记忆块详情
    try {
        const block = await apiRequest(`/api/agent/memory/blocks/${blockId}`);
        
        // 显示编辑对话框（这里简化处理，实际应该有更完整的编辑界面）
        const confirmed = await showConfirmDialog(`编辑记忆块 "${block.title}"?`);
        if (confirmed) {
            showToast('编辑功能待实现', 'info');
        }
    } catch (error) {
        showToast(`获取记忆块详情失败: ${error.message}`, 'error');
    }
}

// 删除记忆块
async function deleteMemoryBlock(blockId) {
    const confirmed = await showConfirmDialog('确定要删除这个记忆块吗？');
    if (!confirmed) return;
    
    try {
        await apiRequest(`/api/agent/memory/blocks/${blockId}`, { method: 'DELETE' });
        showToast('记忆块已删除', 'success');
        refreshCoreMemory(); // 刷新显示
    } catch (error) {
        showToast(`删除记忆块失败: ${error.message}`, 'error');
    }
}

// 显示添加记忆块对话框
function showAddMemoryBlockDialog() {
    if (addMemoryBlockDialog) {
        addMemoryBlockDialog.classList.add('show');
    }
}

// 隐藏添加记忆块对话框
function hideAddMemoryBlockDialog() {
    if (addMemoryBlockDialog) {
        addMemoryBlockDialog.classList.remove('show');
    }
}

// 添加记忆块
async function addMemoryBlock(e) {
    e.preventDefault();
    
    const title = document.getElementById('memoryTitle').value;
    const description = document.getElementById('memoryDescription').value;
    const contentText = document.getElementById('memoryContent').value;
    
    // 将内容文本按行分割成数组
    const content = contentText.split('\n').filter(line => line.trim() !== '');
    
    try {
        await apiRequest('/api/agent/memory/blocks', {
            method: 'POST',
            body: JSON.stringify({ title, description, content })
        });
        
        showToast('记忆块已添加', 'success');
        hideAddMemoryBlockDialog();
        refreshCoreMemory(); // 刷新显示
        
        // 重置表单
        addMemoryBlockForm.reset();
    } catch (error) {
        showToast(`添加记忆块失败: ${error.message}`, 'error');
    }
}

// 刷新工具
async function refreshTools() {
    if (!isConnected) return;
    
    try {
        const tools = await apiRequest('/api/agent/tools');
        displayTools(tools);
    } catch (error) {
        showToast(`获取工具列表失败: ${error.message}`, 'error');
    }
}

// 显示工具
function displayTools(tools) {
    if (!toolsOutput) return;
    
    toolsOutput.innerHTML = `<pre>${tools.tools}</pre>`;
}

// 连接工具
async function connectTool() {
    const toolNameValue = toolName.value.trim();
    const aiToolNameValue = aiToolName.value.trim();
    
    if (!toolNameValue || !aiToolNameValue) {
        showToast('请填写工具名称和AI工具名称', 'warning');
        return;
    }
    
    try {
        // 这里需要调用一个连接工具的API端点
        // 目前我们只是显示一个消息
        showToast(`工具 "${toolNameValue}" 已连接到 "${aiToolNameValue}"`, 'success');
    } catch (error) {
        showToast(`连接工具失败: ${error.message}`, 'error');
    }
}

// 初始化事件监听器
function initEventListeners() {
    // 连接表单提交
    if (connectionForm) {
        connectionForm.addEventListener('submit', (e) => {
            e.preventDefault();
            connectToBackend();
        });
    }
    
    // 断开连接按钮
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', disconnectFromBackend);
    }
    
    // 直播控制按钮
    if (startStreamBtn) startStreamBtn.addEventListener('click', startStream);
    if (stopStreamBtn) stopStreamBtn.addEventListener('click', stopStream);
    if (restartStreamBtn) restartStreamBtn.addEventListener('click', restartStream);
    
    // Agent 控制按钮
    if (refreshAgentLogsBtn) refreshAgentLogsBtn.addEventListener('click', refreshAgentLogs);
    if (clearAgentLogsBtn) clearAgentLogsBtn.addEventListener('click', clearAgentLogs);
    if (refreshTempMemoryBtn) refreshTempMemoryBtn.addEventListener('click', refreshTempMemory);
    if (clearTempMemoryBtn) clearTempMemoryBtn.addEventListener('click', clearTempMemory);
    if (refreshCoreMemoryBtn) refreshCoreMemoryBtn.addEventListener('click', refreshCoreMemory);
    if (addCoreMemoryBlockBtn) addCoreMemoryBlockBtn.addEventListener('click', showAddMemoryBlockDialog);
    if (refreshToolsBtn) refreshToolsBtn.addEventListener('click', refreshTools);
    if (connectToolBtn) connectToolBtn.addEventListener('click', connectTool);
    
    // 配置管理表单
    if (configForm) configForm.addEventListener('submit', saveConfig);
    if (resetConfigBtn) resetConfigBtn.addEventListener('click', resetConfigForm);
    
    // 日志相关按钮
    if (refreshLogsBtn) refreshLogsBtn.addEventListener('click', refreshLogs);
    if (logLines) logLines.addEventListener('change', refreshLogs);
    
    // 用户友好视图切换 - 这个元素已经不存在了，所以注释掉相关代码
    // if (friendlyViewToggle) friendlyViewToggle.addEventListener('change', refreshMessages);
    
    // 标签页切换
    if (navTabs) {
        navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                switchTab(tab.dataset.tab);
                
                // 当切换到配置标签页时，自动加载配置
                if (tab.dataset.tab === 'config' && isConnected) {
                    getConfig().catch(error => {
                        console.error('获取配置失败:', error);
                        showToast(`获取配置失败: ${error.message}`, 'error');
                    });
                }
                
                // 当切换到Agent标签页时，加载相关数据
                if (tab.dataset.tab === 'agent' && isConnected) {
                    // 默认显示Agent日志标签页
                    switchAgentTab('messages');
                    refreshAgentLogs();
                }
            });
        });
    }
    
    // Agent 标签页切换
    if (agentTabBtns) {
        agentTabBtns.forEach(tab => {
            tab.addEventListener('click', () => {
                switchAgentTab(tab.dataset.agentTab);
                
                // 切换到不同Agent子标签页时加载对应数据
                if (tab.dataset.agentTab === 'messages' && isConnected) {
                    refreshAgentLogs();
                } else if (tab.dataset.agentTab === 'memory' && isConnected) {
                    refreshTempMemory();
                    refreshCoreMemory();
                } else if (tab.dataset.agentTab === 'tools' && isConnected) {
                    refreshTools();
                }
            });
        });
    }
    
    // 当主标签页切换到Agent时，默认显示Agent日志
    const agentMainTab = document.querySelector('[data-tab="agent"]');
    if (agentMainTab) {
        agentMainTab.addEventListener('click', () => {
            if (isConnected) {
                refreshAgentLogs();
            }
        });
    }
    
    // 模态对话框事件
    if (addMemoryBlockForm) {
        addMemoryBlockForm.addEventListener('submit', addMemoryBlock);
    }
    
    if (cancelAddMemoryBtn) {
        cancelAddMemoryBtn.addEventListener('click', hideAddMemoryBlockDialog);
    }
    
    // 关闭对话框按钮
    if (closeDialogBtns) {
        closeDialogBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // 查找最近的模态对话框并隐藏
                const dialog = btn.closest('.modal-dialog');
                if (dialog) {
                    dialog.classList.remove('show');
                }
            });
        });
    }
    
    // 点击对话框背景关闭对话框
    if (addMemoryBlockDialog) {
        addMemoryBlockDialog.addEventListener('click', (e) => {
            if (e.target === addMemoryBlockDialog) {
                hideAddMemoryBlockDialog();
            }
        });
    }
}

// 显示横幅提示
function showToast(message, type = 'info', duration = 5000) {
    // 如果容器不存在，创建它
    if (!toastContainer) {
        toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
    }
    
    // 创建横幅元素
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // 添加图标
    const icon = document.createElement('span');
    icon.className = 'icon';
    switch (type) {
        case 'success':
            icon.textContent = '✓';
            break;
        case 'error':
            icon.textContent = '✗';
            break;
        case 'warning':
            icon.textContent = '!';
            break;
        default:
            icon.textContent = 'ℹ';
    }
    
    // 添加消息文本
    const messageEl = document.createElement('span');
    messageEl.className = 'message';
    messageEl.textContent = message;
    
    // 添加关闭按钮
    const closeBtn = document.createElement('button');
    closeBtn.className = 'close-btn';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    };
    
    // 组装元素
    toast.appendChild(icon);
    toast.appendChild(messageEl);
    toast.appendChild(closeBtn);
    
    // 添加到容器
    toastContainer.appendChild(toast);
    
    // 触发显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 自动隐藏
    if (duration > 0) {
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);
    }
}

// 显示确认对话框
function showConfirmDialog(message) {
    // 如果对话框元素不存在，创建它
    if (!confirmDialog) {
        confirmDialog = document.getElementById('confirmDialog');
        if (!confirmDialog) {
            confirmDialog = document.createElement('div');
            confirmDialog.id = 'confirmDialog';
            confirmDialog.className = 'confirm-dialog';
            
            confirmDialog.innerHTML = `
                <div class="confirm-content">
                    <div class="confirm-message"></div>
                    <div class="confirm-buttons">
                        <button class="btn secondary confirm-cancel">取消</button>
                        <button class="btn primary confirm-ok">确定</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(confirmDialog);
        }
    }
    
    // 设置消息
    confirmDialog.querySelector('.confirm-message').textContent = message;
    
    // 显示对话框
    confirmDialog.classList.add('show');
    
    // 返回Promise
    return new Promise((resolve) => {
        // 绑定事件（每次调用时重新绑定以确保事件处理程序是最新的）
        const okButton = confirmDialog.querySelector('.confirm-ok');
        const cancelButton = confirmDialog.querySelector('.confirm-cancel');
        
        // 清除之前的事件监听器
        const newOkButton = okButton.cloneNode(true);
        okButton.parentNode.replaceChild(newOkButton, okButton);
        
        const newCancelButton = cancelButton.cloneNode(true);
        cancelButton.parentNode.replaceChild(newCancelButton, cancelButton);
        
        // 添加新的事件监听器
        newOkButton.addEventListener('click', () => {
            resolve(true);
            confirmDialog.classList.remove('show');
        });
        
        newCancelButton.addEventListener('click', () => {
            resolve(false);
            confirmDialog.classList.remove('show');
        });
    });
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

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    
    // 隐藏非连接标签页直到连接成功
    document.querySelector('[data-tab="control"]').style.display = 'none';
    document.querySelector('[data-tab="config"]').style.display = 'none';
    document.querySelector('[data-tab="agent"]').style.display = 'none';
    document.querySelector('[data-tab="logs"]').style.display = 'none';
    
    // 从localStorage恢复连接信息
    const savedUrl = localStorage.getItem('backendUrl');
    const savedPassword = localStorage.getItem('authToken');
    
    if (savedUrl) {
        document.getElementById('backendUrl').value = savedUrl;
    }
    
    if (savedPassword) {
        document.getElementById('password').value = savedPassword;
    }
    
    // 如果有保存的URL，尝试自动连接
    if (savedUrl) {
        // 使用setTimeout确保DOM完全加载后再连接
        setTimeout(() => {
            connectToBackend(true);
        }, 100);
    }
    
    // 定期更新直播状态
    setInterval(() => {
        if (isConnected) {
            updateStreamStatus();
        }
    }, 5000); // 每5秒更新一次
    
    // 定期刷新日志
    setInterval(() => {
        if (isConnected && logWebSocket && logWebSocket.readyState !== WebSocket.OPEN) {
            // 如果WebSocket连接断开，尝试重新获取日志
            getLogs();
        }
    }, 30000); // 每30秒检查一次
    
    // 添加连接健康检查
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
                        showDisconnectDialog();
                        // 切换到连接页面
                        switchTab('connection');
                    }
                }
            }
        }
    }, 10000); // 每10秒检查一次连接健康状态
});