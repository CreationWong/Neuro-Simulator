// dashboard_web/js/main.js

// 全局变量
let backendUrl = '';
let authToken = '';
let isConnected = false;
let logWebSocket = null;

// DOM 元素
const connectionForm = document.getElementById('connectionForm');
const disconnectBtn = document.getElementById('disconnectBtn');
const streamControlSection = document.getElementById('streamControlSection');
const configSection = document.getElementById('configSection');
const logsSection = document.getElementById('logsSection');
const connectionStatus = document.getElementById('connectionStatus');
const statusDot = connectionStatus.querySelector('.status-dot');
const statusText = connectionStatus.querySelector('.status-text');

// 直播控制相关元素
const streamStatus = document.getElementById('streamStatus');
const startStreamBtn = document.getElementById('startStreamBtn');
const stopStreamBtn = document.getElementById('stopStreamBtn');
const restartStreamBtn = document.getElementById('restartStreamBtn');

// 配置管理相关元素
const getConfigBtn = document.getElementById('getConfigBtn');
const reloadConfigBtn = document.getElementById('reloadConfigBtn');
const saveConfigBtn = document.getElementById('saveConfigBtn');
const configEditor = document.getElementById('configEditor');

// 日志显示相关元素
const logsOutput = document.getElementById('logsOutput');
const logLines = document.getElementById('logLines');
const refreshLogsBtn = document.getElementById('refreshLogsBtn');

// 更新连接状态显示
function updateConnectionStatus(connected, message = '') {
    isConnected = connected;
    if (connected) {
        statusDot.className = 'status-dot connected';
        statusText.textContent = message || '已连接';
        disconnectBtn.disabled = false;
        streamControlSection.style.display = 'block';
        configSection.style.display = 'block';
        logsSection.style.display = 'block';
    } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = message || '未连接';
        disconnectBtn.disabled = true;
        streamControlSection.style.display = 'none';
        configSection.style.display = 'none';
        logsSection.style.display = 'none';
        
        // 关闭日志WebSocket连接
        if (logWebSocket) {
            logWebSocket.close();
            logWebSocket = null;
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
        throw error;
    }
}

// 连接到后端
async function connectToBackend() {
    console.log('开始连接到后端'); // 调试信息
    const url = document.getElementById('backendUrl').value.trim();
    const password = document.getElementById('password').value;
    
    console.log('后端URL:', url); // 调试信息
    console.log('密码:', password); // 调试信息
    
    if (!url) {
        alert('请输入后端地址');
        return;
    }
    
    try {
        // 更新状态为连接中
        statusDot.className = 'status-dot connecting';
        statusText.textContent = '连接中...';
        
        // 保存连接信息
        backendUrl = url;
        authToken = password || ''; // 保存密码，即使是空字符串
        
        console.log('保存的后端URL:', backendUrl); // 调试信息
        console.log('保存的认证Token:', authToken); // 调试信息
        
        // 尝试获取后端状态以验证连接（跳过连接检查）
        const response = await apiRequest('/api/system/health', {}, true);
        
        console.log('健康检查响应:', response); // 调试信息
        
        if (response.status === 'healthy') {
            updateConnectionStatus(true, '已连接');
            alert('连接成功！');
            // 更新直播状态
            updateStreamStatus();
            // 连接日志WebSocket
            connectLogWebSocket();
        } else {
            throw new Error('后端服务不健康');
        }
    } catch (error) {
        console.error('连接失败:', error);
        updateConnectionStatus(false, '连接失败');
        alert(`连接失败: ${error.message}`);
    }
}

// 断开连接
function disconnectFromBackend() {
    backendUrl = '';
    authToken = '';
    updateConnectionStatus(false, '已断开连接');
    alert('已断开连接');
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
    try {
        const response = await apiRequest('/api/stream/start', { method: 'POST' });
        alert(response.message);
        updateStreamStatus();
    } catch (error) {
        alert(`操作失败: ${error.message}`);
    }
}

// 停止直播
async function stopStream() {
    if (!confirm('确定要停止直播吗？')) {
        return;
    }
    
    try {
        const response = await apiRequest('/api/stream/stop', { method: 'POST' });
        alert(response.message);
        updateStreamStatus();
    } catch (error) {
        alert(`操作失败: ${error.message}`);
    }
}

// 重启直播
async function restartStream() {
    if (!confirm('确定要重启直播吗？这将停止并重新启动直播进程。')) {
        return;
    }
    
    try {
        const response = await apiRequest('/api/stream/restart', { method: 'POST' });
        alert(response.message);
        updateStreamStatus();
    } catch (error) {
        alert(`操作失败: ${error.message}`);
    }
}

// 获取配置
async function getConfig() {
    try {
        const config = await apiRequest('/api/configs');
        // 格式化配置为YAML格式显示
        configEditor.value = formatConfigAsYaml(config);
    } catch (error) {
        alert(`获取配置失败: ${error.message}`);
    }
}

// 重载配置
async function reloadConfig() {
    try {
        const response = await apiRequest('/api/configs/reload', { method: 'POST' });
        alert(response.message);
        // 重新获取配置显示
        await getConfig();
    } catch (error) {
        alert(`重载配置失败: ${error.message}`);
    }
}

// 保存配置
async function saveConfig() {
    try {
        const configText = configEditor.value;
        // 尝试解析YAML格式的配置
        const config = parseYamlConfig(configText);
        await apiRequest('/api/configs', {
            method: 'PATCH',
            body: JSON.stringify(config)
        });
        alert('配置保存成功');
    } catch (error) {
        alert(`保存配置失败: ${error.message}`);
    }
}

// 简单的YAML格式化函数（只是美化显示，不是真正的YAML解析器）
function formatConfigAsYaml(obj, indent = 0) {
    const spaces = '  '.repeat(indent);
    let result = '';
    
    for (const [key, value] of Object.entries(obj)) {
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            result += `${spaces}${key}:\n${formatConfigAsYaml(value, indent + 1)}`;
        } else if (Array.isArray(value)) {
            result += `${spaces}${key}:\n`;
            value.forEach(item => {
                if (typeof item === 'object' && item !== null) {
                    result += `${spaces}  -\n${formatConfigAsYaml(item, indent + 2)}`;
                } else {
                    result += `${spaces}  - ${item}\n`;
                }
            });
        } else {
            result += `${spaces}${key}: ${value}\n`;
        }
    }
    
    return result;
}

// 简单的YAML解析函数（仅处理基本结构）
function parseYamlConfig(yamlText) {
    const lines = yamlText.split('\n');
    const result = {};
    const stack = [result];
    const indents = [0];
    
    for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine || trimmedLine.startsWith('#')) continue;
        
        const currentIndent = line.search(/\S/);
        const match = trimmedLine.match(/^([^:]+):\s*(.*)$/);
        
        if (match) {
            const key = match[1].trim();
            const value = match[2].trim();
            
            // 调整栈和缩进级别
            while (indents.length > 1 && currentIndent <= indents[indents.length - 1]) {
                stack.pop();
                indents.pop();
            }
            
            if (value) {
                // 简单值
                const parent = stack[stack.length - 1];
                if (/^\d+$/.test(value)) {
                    parent[key] = parseInt(value);
                } else if (/^true|false$/i.test(value)) {
                    parent[key] = value.toLowerCase() === 'true';
                } else {
                    parent[key] = value;
                }
            } else {
                // 对象或数组
                const parent = stack[stack.length - 1];
                if (trimmedLine.endsWith(':')) {
                    // 对象
                    const newObj = {};
                    parent[key] = newObj;
                    stack.push(newObj);
                    indents.push(currentIndent);
                } else if (trimmedLine.endsWith(':-')) {
                    // 数组
                    const newArr = [];
                    parent[key] = newArr;
                    stack.push(newArr);
                    indents.push(currentIndent);
                }
            }
        } else if (trimmedLine.startsWith('- ')) {
            // 数组项
            const value = trimmedLine.substring(2).trim();
            const parent = stack[stack.length - 1];
            if (parent && Array.isArray(parent)) {
                if (/^\d+$/.test(value)) {
                    parent.push(parseInt(value));
                } else if (/^true|false$/i.test(value)) {
                    parent.push(value.toLowerCase() === 'true');
                } else {
                    parent.push(value);
                }
            }
        }
    }
    
    return result;
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
    
    // 配置管理按钮
    getConfigBtn.addEventListener('click', getConfig);
    reloadConfigBtn.addEventListener('click', reloadConfig);
    saveConfigBtn.addEventListener('click', saveConfig);
    
    // 日志相关按钮
    refreshLogsBtn.addEventListener('click', refreshLogs);
    logLines.addEventListener('change', refreshLogs);
    
    // 页面加载时尝试从localStorage恢复连接信息
    window.addEventListener('load', () => {
        const savedUrl = localStorage.getItem('backendUrl');
        const savedPassword = localStorage.getItem('authToken');
        if (savedUrl) {
            document.getElementById('backendUrl').value = savedUrl;
        }
        if (savedPassword) {
            document.getElementById('password').value = savedPassword;
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    
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