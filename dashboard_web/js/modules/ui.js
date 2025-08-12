// dashboard_web/js/modules/ui.js

// 全局变量
let toastContainer = null; // 横幅提示容器
let confirmDialog = null; // 确认对话框元素
let confirmResolver = null; // 确认对话框的Promise resolver
let modalDialog = null; // 模态对话框元素

// 标签页相关元素
const navTabs = document.querySelectorAll('.nav-tab');
const tabContents = document.querySelectorAll('.tab-content');

// Agent 标签页相关元素
const agentTabBtns = document.querySelectorAll('.agent-tab-btn');
const agentTabContents = document.querySelectorAll('.agent-tab-content');

// 模态对话框相关元素
const addMemoryBlockDialog = document.getElementById('addMemoryBlockDialog');
const addMemoryBlockForm = document.getElementById('addMemoryBlockForm');
const cancelAddMemoryBtn = document.getElementById('cancelAddMemoryBtn');
const closeDialogBtns = document.querySelectorAll('.close-btn');

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

// 初始化事件监听器
function initEventListeners() {
    // 连接表单提交
    const connectionForm = document.getElementById('connectionForm');
    if (connectionForm) {
        connectionForm.addEventListener('submit', (e) => {
            e.preventDefault();
            window.connectionModule.connectToBackend();
        });
    }
    
    // 断开连接按钮
    const disconnectBtn = document.getElementById('disconnectBtn');
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', window.connectionModule.disconnectFromBackend);
    }
    
    // 直播控制按钮
    const startStreamBtn = document.getElementById('startStreamBtn');
    const stopStreamBtn = document.getElementById('stopStreamBtn');
    const restartStreamBtn = document.getElementById('restartStreamBtn');
    
    if (startStreamBtn) startStreamBtn.addEventListener('click', window.streamModule.startStream);
    if (stopStreamBtn) stopStreamBtn.addEventListener('click', window.streamModule.stopStream);
    if (restartStreamBtn) restartStreamBtn.addEventListener('click', window.streamModule.restartStream);
    
    // Agent 控制按钮
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
    const addMemoryBlockForm = document.getElementById('addMemoryBlockForm');
    const cancelAddMemoryBtn = document.getElementById('cancelAddMemoryBtn');
    
    if (refreshTempMemoryBtn) refreshTempMemoryBtn.addEventListener('click', window.agentModule.refreshTempMemory);
    if (clearTempMemoryBtn) clearTempMemoryBtn.addEventListener('click', window.agentModule.clearTempMemory);
    if (refreshCoreMemoryBtn) refreshCoreMemoryBtn.addEventListener('click', window.agentModule.refreshCoreMemory);
    if (addCoreMemoryBlockBtn) addCoreMemoryBlockBtn.addEventListener('click', showAddMemoryBlockDialog);
    if (refreshToolsBtn) refreshToolsBtn.addEventListener('click', window.agentModule.refreshTools);
    if (connectToolBtn) connectToolBtn.addEventListener('click', window.agentModule.connectTool);
    
    // 配置管理表单
    const configForm = document.getElementById('configForm');
    const resetConfigBtn = document.getElementById('resetConfigBtn');
    if (configForm) configForm.addEventListener('submit', window.configModule.saveConfig);
    if (resetConfigBtn) resetConfigBtn.addEventListener('click', window.configModule.resetConfigForm);
    
    // 标签页切换
    const navTabs = document.querySelectorAll('.nav-tab');
    if (navTabs) {
        navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                switchTab(tab.dataset.tab);
                
                // 当切换到配置标签页时，自动加载配置
                if (tab.dataset.tab === 'config' && window.connectionModule.isConnected) {
                    window.configModule.getConfig().catch(error => {
                        console.error('获取配置失败:', error);
                        showToast(`获取配置失败: ${error.message}`, 'error');
                    });
                }
                
                // 当切换到Agent标签页时，加载相关数据
                if (tab.dataset.tab === 'agent' && window.connectionModule.isConnected) {
                    // 默认显示Server日志标签页
                    switchAgentTab('server-logs');
                }
            });
        });
    }
    
    // Agent 标签页切换
    const agentTabBtns = document.querySelectorAll('.agent-tab-btn');
    if (agentTabBtns) {
        agentTabBtns.forEach(tab => {
            tab.addEventListener('click', () => {
                switchAgentTab(tab.dataset.agentTab);
                
                // 切换到不同Agent子标签页时加载对应数据
                if (tab.dataset.agentTab === 'memory' && window.connectionModule.isConnected) {
                    window.agentModule.refreshTempMemory();
                    window.agentModule.refreshCoreMemory();
                } else if (tab.dataset.agentTab === 'tools' && window.connectionModule.isConnected) {
                    window.agentModule.refreshTools();
                }
                // 注意：对于日志和上下文标签页，我们不再清空内容，而是保持已有的内容
            });
        });
    }
    
    // 当主标签页切换到Agent时，默认显示Server日志
    const agentMainTab = document.querySelector('[data-tab="agent"]');
    if (agentMainTab) {
        agentMainTab.addEventListener('click', () => {
            if (window.connectionModule.isConnected) {
                // 切换到Server日志标签页
                switchAgentTab('server-logs');
            }
        });
    }
    
    // 模态对话框事件
    if (addMemoryBlockForm) {
        addMemoryBlockForm.addEventListener('submit', window.agentModule.addMemoryBlock);
    }
    
    if (cancelAddMemoryBtn) {
        cancelAddMemoryBtn.addEventListener('click', hideAddMemoryBlockDialog);
    }
    
    // 关闭对话框按钮
    const closeDialogBtns = document.querySelectorAll('.close-btn');
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
    const addMemoryBlockDialog = document.getElementById('addMemoryBlockDialog');
    if (addMemoryBlockDialog) {
        addMemoryBlockDialog.addEventListener('click', (e) => {
            if (e.target === addMemoryBlockDialog) {
                hideAddMemoryBlockDialog();
            }
        });
    }
}

// 导出函数供其他模块使用
window.uiModule = {
    switchTab,
    switchAgentTab,
    showToast,
    showConfirmDialog,
    showAddMemoryBlockDialog,
    hideAddMemoryBlockDialog,
    initEventListeners
};