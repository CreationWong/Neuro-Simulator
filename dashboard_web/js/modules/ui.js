// dashboard_web/js/modules/ui.js

// 全局变量
let toastContainer = null; // 横幅提示容器
let confirmDialog = null; // 确认对话框元素
let confirmResolver = null; // 确认对话框的Promise resolver
let modalDialog = null; // 模态对话框元素

// 标签页相关元素
const navTabs = document.querySelectorAll('.nav-tab');
const tabContents = document.querySelectorAll('.main-tab-content');

// 模态对话框相关元素
const addMemoryBlockDialog = document.getElementById('addMemoryBlockDialog');
const addMemoryBlockForm = document.getElementById('addMemoryBlockForm');
const cancelAddMemoryBtn = document.getElementById('cancelAddMemoryBtn');
const closeDialogBtns = document.querySelectorAll('.close-btn');

// 切换主标签页
function switchTab(tabName) {
    navTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
}

// 以编程方式切换Agent子标签页
function switchAgentTab(tabName) {
    console.log('DEBUG: Checking for bootstrap object in switchAgentTab:', typeof bootstrap);
    const tabButton = document.querySelector(`#agent-nav-tabs button[data-bs-target="#${tabName}-agent-tab"]`);
    if (tabButton) {
        const tab = bootstrap.Tab.getOrCreateInstance(tabButton);
        tab.show();
    }
}

// 显示横幅提示
function showToast(message, type = 'info', duration = 5000) {
    if (!toastContainer) {
        toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = document.createElement('span');
    icon.className = 'icon';
    switch (type) {
        case 'success': icon.textContent = '✓'; break;
        case 'error': icon.textContent = '✗'; break;
        case 'warning': icon.textContent = '!'; break;
        default: icon.textContent = 'ℹ';
    }
    const messageEl = document.createElement('span');
    messageEl.className = 'message';
    messageEl.textContent = message;
    const closeBtn = document.createElement('button');
    closeBtn.className = 'close-btn';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = () => {
        toast.classList.remove('show');
        setTimeout(() => toast.parentNode?.removeChild(toast), 300);
    };
    toast.append(icon, messageEl, closeBtn);
    toastContainer.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    if (duration > 0) {
        setTimeout(() => closeBtn.onclick(), duration);
    }
}

// 显示确认对话框
function showConfirmDialog(message) {
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
    confirmDialog.querySelector('.confirm-message').textContent = message;
    confirmDialog.classList.add('show');
    return new Promise((resolve) => {
        const okButton = confirmDialog.querySelector('.confirm-ok');
        const cancelButton = confirmDialog.querySelector('.confirm-cancel');
        const newOkButton = okButton.cloneNode(true);
        okButton.parentNode.replaceChild(newOkButton, okButton);
        const newCancelButton = cancelButton.cloneNode(true);
        cancelButton.parentNode.replaceChild(newCancelButton, cancelButton);
        newOkButton.addEventListener('click', () => { resolve(true); confirmDialog.classList.remove('show'); });
        newCancelButton.addEventListener('click', () => { resolve(false); confirmDialog.classList.remove('show'); });
    });
}

// 其他对话框函数 (showAddMemoryBlockDialog, etc.) 保持不变
function showAddMemoryBlockDialog() { if (addMemoryBlockDialog) addMemoryBlockDialog.classList.add('show'); }
function hideAddMemoryBlockDialog() { if (addMemoryBlockDialog) addMemoryBlockDialog.classList.remove('show'); }

function showAddTempMemoryDialog() {
    const dialog = document.createElement('div');
    dialog.className = 'modal-dialog show';
    dialog.id = 'addTempMemoryDialog';
    dialog.innerHTML = `
        <div class="modal-content">
            <div class="modal-header"><h3>添加临时记忆</h3><button class="close-btn">&times;</button></div>
            <div class="modal-body">
                <form id="addTempMemoryForm">
                    <div class="form-group"><label for="tempMemoryRole">角色:</label><select id="tempMemoryRole" class="form-control"><option value="system">system</option><option value="user">user</option><option value="assistant">assistant</option></select></div>
                    <div class="form-group"><label for="tempMemoryContent">内容:</label><textarea id="tempMemoryContent" rows="4" class="form-control"></textarea></div>
                    <div class="button-group"><button type="button" class="btn secondary" id="cancelAddTempMemoryBtn">取消</button><button type="submit" class="btn primary">添加</button></div>
                </form>
            </div>
        </div>
    `;
    document.body.appendChild(dialog);
    const closeDialog = () => dialog.remove();
    dialog.querySelector('.close-btn').addEventListener('click', closeDialog);
    dialog.querySelector('#cancelAddTempMemoryBtn').addEventListener('click', closeDialog);
    dialog.addEventListener('click', (e) => { if (e.target === dialog) closeDialog(); });
    dialog.querySelector('#addTempMemoryForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = document.getElementById('tempMemoryContent').value.trim();
        if (!content) { window.uiModule.showToast('请输入内容', 'warning'); return; }
        try {
            await window.connectionModule.sendAdminWsMessage('add_temp_memory', { content, role: document.getElementById('tempMemoryRole').value });
            window.uiModule.showToast('临时记忆已添加', 'success');
            closeDialog();
            window.agentModule?.refreshTempMemory();
        } catch (error) { window.uiModule.showToast(`添加临时记忆失败: ${error.message}`, 'error'); }
    });
}

function showAddInitMemoryItemDialog() {
    const dialog = document.createElement('div');
    dialog.className = 'modal-dialog show';
    dialog.id = 'addInitMemoryItemDialog';
    dialog.innerHTML = `
        <div class="modal-content">
            <div class="modal-header"><h3>添加/编辑初始化记忆项</h3><button class="close-btn">&times;</button></div>
            <div class="modal-body">
                <form id="addInitMemoryItemForm">
                    <div class="form-group"><label for="initMemoryKey">键:</label><input type="text" id="initMemoryKey" class="form-control" required></div>
                    <div class="form-group"><label for="initMemoryValue">值:</label><textarea id="initMemoryValue" rows="4" class="form-control"></textarea><small>可以是字符串、JSON对象或数组（每行一个元素）。</small></div>
                    <div class="button-group"><button type="button" class="btn secondary" id="cancelAddInitMemoryBtn">取消</button><button type="submit" class="btn primary">保存</button></div>
                </form>
            </div>
        </div>
    `;
    document.body.appendChild(dialog);
    const closeDialog = () => dialog.remove();
    dialog.querySelector('.close-btn').addEventListener('click', closeDialog);
    dialog.querySelector('#cancelAddInitMemoryBtn').addEventListener('click', closeDialog);
    dialog.addEventListener('click', (e) => { if (e.target === dialog) closeDialog(); });
    dialog.querySelector('#addInitMemoryItemForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const key = document.getElementById('initMemoryKey').value.trim();
        if (!key) { window.uiModule.showToast('请输入键', 'warning'); return; }
        await window.agentModule?.updateInitMemoryItem(key, document.getElementById('initMemoryValue').value);
        closeDialog();
    });
}

// 初始化事件监听器
function initEventListeners() {
    // 连接与断开
    document.getElementById('connectionForm')?.addEventListener('submit', (e) => { e.preventDefault(); window.connectionModule?.connectToBackend(); });
    document.getElementById('disconnectBtn')?.addEventListener('click', () => window.connectionModule?.disconnectFromBackend());

    // 直播控制
    document.getElementById('startStreamBtn')?.addEventListener('click', () => window.streamModule?.startStream());
    document.getElementById('stopStreamBtn')?.addEventListener('click', () => window.streamModule?.stopStream());
    document.getElementById('restartStreamBtn')?.addEventListener('click', () => window.streamModule?.restartStream());

    // Agent 记忆控制
    document.getElementById('refreshInitMemoryBtn')?.addEventListener('click', () => window.agentModule?.refreshInitMemory());
    document.getElementById('refreshTempMemoryBtn')?.addEventListener('click', () => window.agentModule?.refreshTempMemory());
    document.getElementById('clearTempMemoryBtn')?.addEventListener('click', () => window.agentModule?.clearTempMemory());
    document.getElementById('addTempMemoryBtn')?.addEventListener('click', showAddTempMemoryDialog);
    document.getElementById('addInitMemoryItemBtn')?.addEventListener('click', showAddInitMemoryItemDialog);
    document.getElementById('refreshCoreMemoryBtn')?.addEventListener('click', () => window.agentModule?.refreshCoreMemory());
    document.getElementById('addCoreMemoryBlockBtn')?.addEventListener('click', showAddMemoryBlockDialog);
    document.getElementById('addMemoryBlockForm')?.addEventListener('submit', (e) => window.agentModule?.addMemoryBlock(e));
    document.getElementById('cancelAddMemoryBtn')?.addEventListener('click', hideAddMemoryBlockDialog);

    // 配置管理
    document.getElementById('saveConfigBtn')?.addEventListener('click', () => window.configModule?.saveConfig());

    // 主标签页切换
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
            if (window.connectionModule?.isConnected) {
                if (tabName === 'config') window.configModule?.initializeConfigEditor();
                if (tabName === 'agent-management') {
                    // 当切换到Agent主tab时，默认显示第一个子tab并加载其内容
                    switchAgentTab('context');
                    window.agentModule?.refreshContext(); 
                }
            }
        });
    });

    // Agent 子标签页切换 (使用Bootstrap事件)
    document.querySelectorAll('#agent-nav-tabs button[data-bs-toggle="tab"]').forEach(tabEl => {
        tabEl.addEventListener('shown.bs.tab', event => {
            const tabName = event.target.dataset.bsTarget.replace('#', '').replace('-agent-tab', '');
            if (window.connectionModule?.isConnected) {
                if (tabName === 'memory') {
                    window.agentModule?.refreshInitMemory();
                    window.agentModule?.refreshTempMemory();
                    window.agentModule?.refreshCoreMemory();
                } else if (tabName === 'tools') {
                    window.toolsModule?.initToolsPage();
                } else if (tabName === 'context') {
                    window.agentModule?.refreshContext();
                }
            }
        });
    });

    // 其他UI事件
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', () => btn.closest('.modal-dialog')?.classList.remove('show'));
    });
    document.getElementById('addMemoryBlockDialog')?.addEventListener('click', (e) => {
        if (e.target === addMemoryBlockDialog) hideAddMemoryBlockDialog();
    });
    const contextViewMode = document.getElementById('contextViewMode');
    if (contextViewMode) {
        contextViewMode.addEventListener('change', () => {
            document.getElementById('modeLabel').textContent = contextViewMode.checked ? '上下文模式' : '对话模式';
            window.agentModule?.rerenderContext();
        });
    }
}

function showDisconnectDialog() {
    showConfirmDialog('与后端的连接已断开，请重新连接。').then(() => {});
    setTimeout(() => {
        const confirmDialog = document.getElementById('confirmDialog');
        if (confirmDialog) {
            confirmDialog.querySelector('.confirm-cancel').style.display = 'none';
            confirmDialog.querySelector('.confirm-ok').textContent = '确定';
            confirmDialog.querySelector('.confirm-message').textContent = '与后端的连接已断开，请重新连接。';
        }
    }, 10);
}

// 导出模块
window.uiModule = {
    switchTab,
    switchAgentTab,
    showToast,
    showConfirmDialog,
    showAddMemoryBlockDialog,
    showAddTempMemoryDialog,
    showAddInitMemoryItemDialog,
    hideAddMemoryBlockDialog,
    showDisconnectDialog,
    initEventListeners
};
