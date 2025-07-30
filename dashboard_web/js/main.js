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

// 标签页相关元素
const navTabs = document.querySelectorAll('.nav-tab');
const tabContents = document.querySelectorAll('.tab-content');

// 更新连接状态显示
function updateConnectionStatus(connected, message = '') {
    isConnected = connected;
    if (connected) {
        statusDot.className = 'status-dot connected';
        statusText.textContent = message || '已连接';
        disconnectBtn.disabled = false;
        
        // 显示控制、配置和日志标签页
        document.querySelector('[data-tab="control"]').style.display = 'block';
        document.querySelector('[data-tab="config"]').style.display = 'block';
        document.querySelector('[data-tab="logs"]').style.display = 'block';
    } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = message || '未连接';
        disconnectBtn.disabled = true;
        
        // 隐藏控制、配置和日志标签页
        document.querySelector('[data-tab="control"]').style.display = 'none';
        document.querySelector('[data-tab="config"]').style.display = 'none';
        document.querySelector('[data-tab="logs"]').style.display = 'none';
        
        // 关闭日志WebSocket连接
        if (logWebSocket) {
            logWebSocket.close();
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
        } else {
            throw new Error('后端服务不健康');
        }
    } catch (error) {
        console.error('连接失败:', error);
        updateConnectionStatus(false, '连接失败');
        if (!autoConnect) {
            showToast(`连接失败: ${error.message}`, 'error');
        }
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
        showToast(`获取配置失败: ${error.message}

请检查后端日志以获取更多信息。`, 'error');
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
        };
        
        logWebSocket.onclose = () => {
            console.log('日志WebSocket连接已关闭');
        };
    } catch (error) {
        console.error('连接日志WebSocket失败:', error);
    }
}

// 刷新日志
function refreshLogs() {
    if (isConnected) {
        getLogs();
    }
}

// 初始化事件监听器
function initEventListeners() {
    // 连接表单提交
    connectionForm.addEventListener('submit', (e) => {
        e.preventDefault();
        connectToBackend();
    });
    
    // 断开连接按钮
    disconnectBtn.addEventListener('click', disconnectFromBackend);
    
    // 直播控制按钮
    startStreamBtn.addEventListener('click', startStream);
    stopStreamBtn.addEventListener('click', stopStream);
    restartStreamBtn.addEventListener('click', restartStream);
    
    // 配置管理表单
    configForm.addEventListener('submit', saveConfig);
    resetConfigBtn.addEventListener('click', resetConfigForm);
    
    // 日志相关按钮
    refreshLogsBtn.addEventListener('click', refreshLogs);
    logLines.addEventListener('change', refreshLogs);
    
    // 标签页切换
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
        });
    });
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

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    
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
});