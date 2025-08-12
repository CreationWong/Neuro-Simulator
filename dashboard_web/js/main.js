// dashboard_web/js/main.js

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化事件监听器
    window.uiModule.initEventListeners();
    
    // 隐藏非连接标签页直到连接成功
    document.querySelector('[data-tab="control"]').style.display = 'none';
    document.querySelector('[data-tab="config"]').style.display = 'none';
    document.querySelector('[data-tab="agent"]').style.display = 'none';
    
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
            window.connectionModule.connectToBackend(true);
        }, 100);
    }
    
    // 定期更新直播状态
    setInterval(() => {
        if (window.connectionModule.isConnected) {
            window.streamModule.updateStreamStatus();
        }
    }, 5000); // 每5秒更新一次
    
    // 定期刷新日志
    setInterval(() => {
        if (window.connectionModule.isConnected && window.connectionModule.adminWebSocket && window.connectionModule.adminWebSocket.readyState !== WebSocket.OPEN) {
            // 如果WebSocket连接断开，尝试重新获取日志
            // getLogs(); // 这个函数在新代码中未定义，暂时注释掉
        }
    }, 30000); // 每30秒检查一次
    
    // 添加连接健康检查
    window.connectionModule.healthCheckInterval = setInterval(async () => {
        if (window.connectionModule.isConnected) {
            try {
                // 发送一个简单的健康检查请求
                await window.connectionModule.apiRequest('/api/system/health', {}, true);
            } catch (error) {
                // 如果是网络错误，认为连接已断开
                if (error instanceof TypeError && error.message === 'Failed to fetch') {
                    // 只有在还没有通知过断连的情况下才显示提示
                    if (!window.connectionModule.disconnectNotified) {
                        window.connectionModule.disconnectNotified = true;
                        window.connectionModule.updateConnectionStatus(false, '连接已断开');
                        window.uiModule.showDisconnectDialog();
                        // 切换到连接页面
                        window.uiModule.switchTab('connection');
                    }
                }
            }
        }
    }, 10000); // 每10秒检查一次连接健康状态
});