// dashboard_web/js/modules/stream.js

// 直播控制相关元素
const streamStatus = document.getElementById('streamStatus');
const startStreamBtn = document.getElementById('startStreamBtn');
const stopStreamBtn = document.getElementById('stopStreamBtn');
const restartStreamBtn = document.getElementById('restartStreamBtn');

// 更新直播状态 (通过WebSocket事件驱动，不再主动轮询)
async function updateStreamStatus() {
    // 此函数已不再需要，因为状态由后端主动推送
    // 保留空函数以避免其他地方调用时报错
    console.log("Stream status update is now event-driven via WebSocket.");
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