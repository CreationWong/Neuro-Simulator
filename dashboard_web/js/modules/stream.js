// dashboard_web/js/modules/stream.js

// 直播控制相关元素
const streamStatus = document.getElementById('streamStatus');
const startStreamBtn = document.getElementById('startStreamBtn');
const stopStreamBtn = document.getElementById('stopStreamBtn');
const restartStreamBtn = document.getElementById('restartStreamBtn');

// 更新直播状态
async function updateStreamStatus() {
    try {
        const status = await window.connectionModule.apiRequest('/api/stream/status');
        streamStatus.textContent = status.is_running ? '运行中' : '已停止';
        streamStatus.style.color = status.is_running ? '#4CAF50' : '#F44336';
    } catch (error) {
        streamStatus.textContent = '无法获取状态';
        streamStatus.style.color = '#F44336';
        console.error('获取直播状态失败:', error);
        
        // 检查是否是连接问题，如果是则更新连接状态
        if (error.message.includes('Failed to fetch') || error.message.includes('未连接到后端')) {
            // 只有在还没有通知过断连的情况下才显示提示
            if (!window.connectionModule.disconnectNotified) {
                window.connectionModule.disconnectNotified = true;
                // 显示断连提示对话框
                window.uiModule.showDisconnectDialog();
            }
            // 更新连接状态为断开
            window.connectionModule.updateConnectionStatus(false, '连接已断开');
            // 切换到连接页面
            window.uiModule.switchTab('connection');
        }
    }
}

// 开始直播
async function startStream() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要开始直播吗？');
    if (!confirmed) {
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