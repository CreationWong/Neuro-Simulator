// dashboard_web/js/modules/stream.js

// 直播控制相关元素
const streamStatus = document.getElementById('streamStatus');
const startStreamBtn = document.getElementById('startStreamBtn');
const stopStreamBtn = document.getElementById('stopStreamBtn');
const restartStreamBtn = document.getElementById('restartStreamBtn');

// 更新直播状态 (通过WebSocket事件驱动)
async function updateStreamStatus() {
    if (!window.connectionModule.isConnected) {
        console.log("Not connected to backend, cannot update stream status.");
        return;
    }
    
    try {
        const response = await window.connectionModule.sendAdminWsMessage('get_stream_status');
        const streamStatus = document.getElementById('streamStatus');
        if (streamStatus) {
            streamStatus.textContent = response.is_running ? '运行中' : '已停止';
            streamStatus.style.color = response.is_running ? '#4CAF50' : '#F44336';
        }
    } catch (error) {
        console.error("Failed to update stream status:", error);
        window.uiModule.showToast(`获取直播状态失败: ${error.message}`, 'error');
    }
}

// 开始直播 (通过WebSocket)
async function startStream() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要开始直播吗？');
    if (!confirmed) {
        return;
    }
    
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    try {
        const response = await window.connectionModule.sendAdminWsMessage('start_stream');
        window.uiModule.showToast(response.message, 'success');
        // 状态更新将由后端推送的 stream_status 事件处理
    } catch (error) {
        window.uiModule.showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 停止直播 (通过WebSocket)
async function stopStream() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要停止直播吗？');
    if (!confirmed) {
        return;
    }
    
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    try {
        const response = await window.connectionModule.sendAdminWsMessage('stop_stream');
        window.uiModule.showToast(response.message, 'success');
        // 状态更新将由后端推送的 stream_status 事件处理
    } catch (error) {
        window.uiModule.showToast(`操作失败: ${error.message}`, 'error');
    }
}

// 重启直播 (通过WebSocket)
async function restartStream() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要重启直播吗？这将停止并重新启动直播进程。');
    if (!confirmed) {
        return;
    }
    
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    try {
        const response = await window.connectionModule.sendAdminWsMessage('restart_stream');
        window.uiModule.showToast(response.message, 'success');
        // 状态更新将由后端推送的 stream_status 事件处理
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