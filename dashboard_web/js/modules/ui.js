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

// 显示添加临时记忆对话框
function showAddTempMemoryDialog() {
    // 创建对话框元素
    const dialog = document.createElement('div');
    dialog.className = 'modal-dialog show';
    dialog.id = 'addTempMemoryDialog';
    
    dialog.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>添加临时记忆</h3>
                <button class="close-btn">&times;</button>
            </div>
            <div class="modal-body">
                <form id="addTempMemoryForm">
                    <div class="form-group">
                        <label for="tempMemoryRole">角色:</label>
                        <select id="tempMemoryRole" class="form-control">
                            <option value="system">system</option>
                            <option value="user">user</option>
                            <option value="assistant">assistant</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="tempMemoryContent">内容:</label>
                        <textarea id="tempMemoryContent" rows="4" class="form-control"></textarea>
                    </div>
                    <div class="button-group">
                        <button type="button" class="btn secondary" id="cancelAddTempMemoryBtn">取消</button>
                        <button type="submit" class="btn primary">添加</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    // 添加到文档中
    document.body.appendChild(dialog);
    
    // 绑定事件
    const closeBtn = dialog.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelAddTempMemoryBtn');
    const form = document.getElementById('addTempMemoryForm');
    
    const closeDialog = () => {
        dialog.remove();
    };
    
    closeBtn.addEventListener('click', closeDialog);
    cancelBtn.addEventListener('click', closeDialog);
    
    // 点击对话框背景关闭
    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
            closeDialog();
        }
    });
    
    // 表单提交事件
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const role = document.getElementById('tempMemoryRole').value;
        const content = document.getElementById('tempMemoryContent').value;
        
        if (!content.trim()) {
            window.uiModule.showToast('请输入内容', 'warning');
            return;
        }
        
        try {
            await window.connectionModule.apiRequest('/api/agent/memory/temp', {
                method: 'POST',
                body: JSON.stringify({ content, role })
            });
            
            window.uiModule.showToast('临时记忆已添加', 'success');
            closeDialog();
            if (window.agentModule && window.agentModule.refreshTempMemory) {
                window.agentModule.refreshTempMemory(); // 刷新显示
            }
        } catch (error) {
            window.uiModule.showToast(`添加临时记忆失败: ${error.message}`, 'error');
        }
    });
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
    const refreshInitMemoryBtn = document.getElementById('refreshInitMemoryBtn');
    const refreshTempMemoryBtn = document.getElementById('refreshTempMemoryBtn');
    const addTempMemoryBtn = document.getElementById('addTempMemoryBtn');
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
    
    if (refreshInitMemoryBtn) {
        refreshInitMemoryBtn.addEventListener('click', () => {
            if (window.agentModule && window.agentModule.refreshInitMemory) {
                window.agentModule.refreshInitMemory();
            }
        });
    }
    if (refreshTempMemoryBtn) {
        refreshTempMemoryBtn.addEventListener('click', () => {
            if (window.agentModule && window.agentModule.refreshTempMemory) {
                window.agentModule.refreshTempMemory();
            }
        });
    }
    if (clearTempMemoryBtn) {
        clearTempMemoryBtn.addEventListener('click', () => {
            if (window.agentModule && window.agentModule.clearTempMemory) {
                window.agentModule.clearTempMemory();
            }
        });
    }
    if (addTempMemoryBtn) {
        addTempMemoryBtn.addEventListener('click', showAddTempMemoryDialog);
    }
    if (refreshCoreMemoryBtn) {
        refreshCoreMemoryBtn.addEventListener('click', () => {
            if (window.agentModule && window.agentModule.refreshCoreMemory) {
                window.agentModule.refreshCoreMemory();
            }
        });
    }
    if (addCoreMemoryBlockBtn) {
        addCoreMemoryBlockBtn.addEventListener('click', () => {
            showAddMemoryBlockDialog();
        });
    }
    if (refreshToolsBtn) {
        refreshToolsBtn.addEventListener('click', () => {
            if (window.agentModule && window.agentModule.refreshTools) {
                window.agentModule.refreshTools();
            }
        });
    }
    if (connectToolBtn) {
        connectToolBtn.addEventListener('click', () => {
            if (window.agentModule && window.agentModule.connectTool) {
                window.agentModule.connectTool();
            }
        });
    }
    
    // 配置管理表单
    const configForm = document.getElementById('configForm');
    const resetConfigBtn = document.getElementById('resetConfigBtn');
    
    if (configForm) {
        configForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (window.configModule && window.configModule.saveConfig) {
                window.configModule.saveConfig(e);
            }
        });
    }
    if (resetConfigBtn) {
        resetConfigBtn.addEventListener('click', () => {
            if (window.configModule && window.configModule.resetConfigForm) {
                window.configModule.resetConfigForm();
            }
        });
    }
    
    // 标签页切换
    const navTabs = document.querySelectorAll('.nav-tab');
    
    if (navTabs) {
        navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                switchTab(tab.dataset.tab);
                
                // 当切换到配置标签页时，自动加载配置
                if (tab.dataset.tab === 'config' && window.connectionModule && window.connectionModule.isConnected) {
                    if (window.configModule && window.configModule.getConfig) {
                        window.configModule.getConfig().catch(error => {
                            console.error('获取配置失败:', error);
                            showToast(`获取配置失败: ${error.message}`, 'error');
                        });
                    }
                }
                
                // 当切换到日志标签页时，加载Server日志
                if (tab.dataset.tab === 'logs' && window.connectionModule && window.connectionModule.isConnected) {
                    // 这里可以添加加载Server日志的逻辑
                }
                
                // 当切换到Agent管理标签页时，加载相关数据
                if (tab.dataset.tab === 'agent-management' && window.connectionModule && window.connectionModule.isConnected) {
                    // 默认显示上下文标签页
                    switchAgentTab('context');
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
                if (tab.dataset.agentTab === 'memory' && window.connectionModule && window.connectionModule.isConnected) {
                    if (window.agentModule && window.agentModule.refreshInitMemory && window.agentModule.refreshTempMemory && window.agentModule.refreshCoreMemory) {
                        window.agentModule.refreshInitMemory();
                        window.agentModule.refreshTempMemory();
                        window.agentModule.refreshCoreMemory();
                    }
                } else if (tab.dataset.agentTab === 'tools' && window.connectionModule && window.connectionModule.isConnected) {
                    if (window.agentModule && window.agentModule.refreshTools) {
                        window.agentModule.refreshTools();
                    }
                } else if (tab.dataset.agentTab === 'agent-logs' && window.connectionModule && window.connectionModule.isConnected) {
                    // 这里可以添加加载Agent日志的逻辑
                } else if (tab.dataset.agentTab === 'context' && window.connectionModule && window.connectionModule.isConnected) {
                    // 这里可以添加加载上下文的逻辑
                }
                // 注意：对于日志和上下文标签页，我们不再清空内容，而是保持已有的内容
            });
        });
    }
    
    // 当主标签页切换到Agent管理时，默认显示上下文
    const agentManagementTab = document.querySelector('[data-tab="agent-management"]');
    
    if (agentManagementTab) {
        agentManagementTab.addEventListener('click', () => {
            if (window.connectionModule && window.connectionModule.isConnected) {
                // 切换到上下文标签页
                switchAgentTab('context');
            }
        });
    }
    
    // 模态对话框事件
    if (addMemoryBlockForm) {
        addMemoryBlockForm.addEventListener('submit', function(e) {
            if (window.agentModule && window.agentModule.addMemoryBlock) {
                window.agentModule.addMemoryBlock(e);
            } else {
                console.error('window.agentModule.addMemoryBlock未定义');
            }
        });
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
    
    // 上下文显示模式切换
    const contextViewMode = document.getElementById('contextViewMode');
    const modeLabel = document.getElementById('modeLabel');
    if (contextViewMode && modeLabel) {
        contextViewMode.addEventListener('change', function() {
            modeLabel.textContent = this.checked ? '原始模式' : '对话模式';
            // 重新渲染上下文显示
            if (window.connectionModule.isConnected) {
                // 使用重新渲染函数
                window.agentModule.rerenderContext();
            } else {
                // 如果未连接，仍然需要更新显示
                window.agentModule.refreshContext();
            }
        });
    }
}

// 显示断连对话框
function showDisconnectDialog() {
    // 使用确认对话框显示断连信息，但只显示确定按钮
    showConfirmDialog('与后端的连接已断开，请重新连接。').then(() => {
        // 用户点击确定后，对话框会自动关闭
    });
    
    // 为了只显示确定按钮，我们需要修改对话框的HTML
    setTimeout(() => {
        const confirmDialog = document.getElementById('confirmDialog');
        if (confirmDialog) {
            const cancelButton = confirmDialog.querySelector('.confirm-cancel');
            const okButton = confirmDialog.querySelector('.confirm-ok');
            
            // 隐藏取消按钮
            if (cancelButton) {
                cancelButton.style.display = 'none';
            }
            
            // 修改确定按钮文本
            if (okButton) {
                okButton.textContent = '确定';
            }
            
            // 修改消息显示
            const messageEl = confirmDialog.querySelector('.confirm-message');
            if (messageEl) {
                messageEl.textContent = '与后端的连接已断开，请重新连接。';
            }
        }
    }, 10);
}

// 导出函数供其他模块使用
window.uiModule = {
    switchTab,
    switchAgentTab,
    showToast,
    showConfirmDialog,
    showAddMemoryBlockDialog,
    showAddTempMemoryDialog,
    hideAddMemoryBlockDialog,
    showDisconnectDialog,
    initEventListeners
};