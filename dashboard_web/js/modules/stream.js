// dashboard_web/js/modules/stream.js

// 直播控制相关元素
const streamStatus = document.getElementById('streamStatus');
const startStreamBtn = document.getElementById('startStreamBtn');
const stopStreamBtn = document.getElementById('stopStreamBtn');
const restartStreamBtn = document.getElementById('restartStreamBtn');

// 更新直播状态
async function updateStreamStatus() {
    // 检查连接模块是否存在
    if (!window.connectionModule) {
        return;
    }
    
    try {
        const status = await window.connectionModule.apiRequest('/api/stream/status');
        const streamStatus = document.getElementById('streamStatus');
        if (streamStatus) {
            streamStatus.textContent = status.is_running ? '运行中' : '已停止';
            streamStatus.style.color = status.is_running ? '#4CAF50' : '#F44336';
        }
    } catch (error) {
        const streamStatus = document.getElementById('streamStatus');
        if (streamStatus) {
            streamStatus.textContent = '无法获取状态';
            streamStatus.style.color = '#F44336';
        }
        
        // 只有网络错误才更新连接状态
        if (error.message.includes('Failed to fetch')) {
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

// 开始直播
async function startStream() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要开始直播吗？');
    if (!confirmed) {
        return;
    }
    
    // 检查连接模块是否存在
    if (!window.connectionModule) {
        window.uiModule.showToast('系统错误：连接模块未找到', 'error');
        return;
    }
    
    try {
        const response = await window.connectionModule.apiRequest('/api/stream/start', { method: 'POST' });
        window.uiModule.showToast(response.message, 'success');
        updateStreamStatus();
    } catch (error) {
        window.uiModule.showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 停止直播
async function stopStream() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要停止直播吗？');
    if (!confirmed) {
        return;
    }
    
    // 检查连接模块是否存在
    if (!window.connectionModule) {
        window.uiModule.showToast('系统错误：连接模块未找到', 'error');
        return;
    }
    
    try {
        const response = await window.connectionModule.apiRequest('/api/stream/stop', { method: 'POST' });
        window.uiModule.showToast(response.message, 'success');
        updateStreamStatus();
    } catch (error) {
        window.uiModule.showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 重启直播
async function restartStream() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要重启直播吗？这将停止并重新启动直播进程。');
    if (!confirmed) {
        return;
    }
    
    // 检查连接模块是否存在
    if (!window.connectionModule) {
        window.uiModule.showToast('系统错误：连接模块未找到', 'error');
        return;
    }
    
    try {
        const response = await window.connectionModule.apiRequest('/api/stream/restart', { method: 'POST' });
        window.uiModule.showToast(response.message, 'success');
        updateStreamStatus();
    } catch (error) {
        window.uiModule.showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 导出函数供其他模块使用
window.streamModule = {
    updateStreamStatus,
    startStream,
    stopStream,
    restartStream
};