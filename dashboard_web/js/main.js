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
            // 等待 window.connectionModule 可用
            const checkAndConnect = () => {
                if (window.connectionModule && window.connectionModule.connectToBackend) {
                    window.connectionModule.connectToBackend(true);
                } else {
                    // If window.connectionModule is not yet available, check again later.
                    setTimeout(checkAndConnect, 100);
                }
            };
            checkAndConnect();
        }, 100);
    }
    
    // 移除了旧的定期更新直播状态和日志的 setInterval 轮询逻辑
    // 现在这些状态更新将由后端通过 WebSocket 主动推送
});