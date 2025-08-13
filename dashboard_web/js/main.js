// dashboard_web/js/main.js

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化事件监听器
    window.uiModule.initEventListeners();
    
    // 隐藏非连接标签页直到连接成功
    document.querySelector('[data-tab="control"]').style.display = 'none';
    document.querySelector('[data-tab="config"]').style.display = 'none';
    document.querySelector('[data-tab="logs"]').style.display = 'none';
    // agent-management 和 chatbot-management 标签页的显示由配置决定
    // 不在初始化时隐藏它们，而是在连接成功并获取配置后再决定是否显示
    
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
        // 检查连接模块是否存在
        if (!window.connectionModule) {
            console.error('window.connectionModule未定义');
            return;
        }
        
        if (window.connectionModule.isConnected) {
            window.streamModule.updateStreamStatus().catch(error => {
                console.error('定期更新直播状态失败:', error);
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
            });
        }
    }, 5000); // 每5秒更新一次
    
    // 定期刷新日志
    setInterval(() => {
        if (window.connectionModule.isConnected && window.connectionModule.adminWebSocket && window.connectionModule.adminWebSocket.readyState !== WebSocket.OPEN) {
            // 如果WebSocket连接断开，尝试重新获取日志
            // getLogs(); // 这个函数在新代码中未定义，暂时注释掉
        }
    }, 30000); // 每30秒检查一次
});