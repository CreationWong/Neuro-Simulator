// dashboard_web/js/modules/agent.js

// Agent 控制相关元素
const serverLogsOutput = document.getElementById('serverLogsOutput');
const agentLogsOutput = document.getElementById('agentLogsOutput');
const contextOutput = document.getElementById('contextOutput');
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

// Agent 相关功能

// 刷新上下文
async function refreshContext() {
    if (!window.connectionModule.isConnected) return;
    
    try {
        const contextMessages = await window.connectionModule.apiRequest('/api/agent/context');
        displayContext(contextMessages);
    } catch (error) {
        window.uiModule.showToast(`获取上下文失败: ${error.message}`, 'error');
    }
}

// 显示Agent日志
function displayAgentLogs(logs) {
    if (!agentLogsOutput) return;
    
    // 直接显示日志内容，每行一个div，最新日志在底部
    logs.forEach(logEntry => {
        const logDiv = document.createElement('div');
        logDiv.className = 'log-entry';
        
        // 根据日志级别设置样式
        if (logEntry.includes('ERROR') || logEntry.includes('Error')) {
            logDiv.classList.add('log-error');
        } else if (logEntry.includes('WARNING') || logEntry.includes('Warning')) {
            logDiv.classList.add('log-warning');
        } else if (logEntry.includes('DEBUG') || logEntry.includes('Debug')) {
            logDiv.classList.add('log-debug');
        } else {
            logDiv.classList.add('log-info');
        }
        
        logDiv.textContent = logEntry;
        agentLogsOutput.appendChild(logDiv);
    });
    
    // 保持只显示最新的1000行日志
    const logEntries = agentLogsOutput.querySelectorAll('.log-entry');
    if (logEntries.length > 1000) {
        // 删除多余的日志条目
        for (let i = 0; i < logEntries.length - 1000; i++) {
            logEntries[i].remove();
        }
    }
    
    // 滚动到底部以显示最新日志
    agentLogsOutput.scrollTop = agentLogsOutput.scrollHeight;
}

// 显示上下文
function displayContext(messages) {
    // 不再使用这个函数，上下文通过WebSocket实时处理
}

// 刷新临时记忆
async function refreshTempMemory() {
    if (!window.connectionModule.isConnected) return;
    
    try {
        // 获取完整的临时记忆内容
        const tempMemory = await window.connectionModule.apiRequest('/api/agent/memory/temp');
        displayTempMemory(tempMemory);
    } catch (error) {
        window.uiModule.showToast(`获取临时记忆失败: ${error.message}`, 'error');
    }
}

// 显示临时记忆
function displayTempMemory(messages) {
    if (!tempMemoryOutput) return;
    
    tempMemoryOutput.innerHTML = '';
    
    messages.forEach((msg, index) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'memory-item';
        
        const timestamp = new Date(msg.timestamp).toLocaleString();
        
        itemDiv.innerHTML = `
            <div class="memory-content">
                <div><strong>[${msg.role}]</strong> ${msg.content || msg.text || ''}</div>
                <div class="memory-time">${timestamp}</div>
            </div>
            <div class="memory-actions">
                <button class="btn small danger delete-temp-memory-btn" data-index="${index}">删除</button>
            </div>
        `;
        
        tempMemoryOutput.appendChild(itemDiv);
    });
    
    // 绑定删除按钮事件
    const deleteButtons = tempMemoryOutput.querySelectorAll('.delete-temp-memory-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = e.target.dataset.index;
            deleteTempMemoryItem(index);
        });
    });
}

// 删除临时记忆项
async function deleteTempMemoryItem(index) {
    const confirmed = await window.uiModule.showConfirmDialog('确定要删除这条临时记忆吗？');
    if (!confirmed) return;
    
    try {
        // 对于builtin agent，我们无法直接删除单个消息
        // 这里我们简单地从显示中移除
        const items = tempMemoryOutput.querySelectorAll('.memory-item');
        if (items[index]) {
            items[index].remove();
            window.uiModule.showToast('记忆项已删除', 'success');
        }
    } catch (error) {
        window.uiModule.showToast(`删除记忆项失败: ${error.message}`, 'error');
    }
}

// 清空临时记忆
async function clearTempMemory() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要清空所有临时记忆吗？');
    if (!confirmed) return;
    
    try {
        await window.connectionModule.apiRequest('/api/agent/memory/temp', { method: 'DELETE' });
        tempMemoryOutput.innerHTML = '';
        window.uiModule.showToast('临时记忆已清空', 'success');
    } catch (error) {
        window.uiModule.showToast(`清空临时记忆失败: ${error.message}`, 'error');
    }
}

// 刷新核心记忆
async function refreshCoreMemory() {
    if (!window.connectionModule.isConnected) return;
    
    try {
        const blocks = await window.connectionModule.apiRequest('/api/agent/memory/blocks');
        displayCoreMemory(blocks);
    } catch (error) {
        window.uiModule.showToast(`获取核心记忆失败: ${error.message}`, 'error');
    }
}

// 显示核心记忆
function displayCoreMemory(blocks) {
    if (!coreMemoryOutput) return;
    
    coreMemoryOutput.innerHTML = '';
    
    // 遍历所有记忆块
    Object.values(blocks).forEach(block => {
        const blockDiv = document.createElement('div');
        blockDiv.className = 'memory-block';
        blockDiv.dataset.blockId = block.id;
        
        blockDiv.innerHTML = `
            <div class="memory-block-header">
                <h4>${block.title}</h4>
                <div class="memory-block-actions">
                    <button class="btn small secondary edit-memory-btn" data-block-id="${block.id}">编辑</button>
                    <button class="btn small danger delete-memory-btn" data-block-id="${block.id}">删除</button>
                </div>
            </div>
            <div class="memory-block-description">${block.description}</div>
            <div class="memory-block-content">
                <ul>
                    ${block.content.map(item => `<li>${item}</li>`).join('')}
                </ul>
            </div>
        `;
        
        coreMemoryOutput.appendChild(blockDiv);
    });
    
    // 绑定编辑和删除按钮事件
    const editButtons = coreMemoryOutput.querySelectorAll('.edit-memory-btn');
    editButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const blockId = e.target.dataset.blockId;
            editMemoryBlock(blockId);
        });
    });
    
    const deleteButtons = coreMemoryOutput.querySelectorAll('.delete-memory-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const blockId = e.target.dataset.blockId;
            deleteMemoryBlock(blockId);
        });
    });
}

// 编辑记忆块
async function editMemoryBlock(blockId) {
    // 获取记忆块详情
    try {
        const block = await window.connectionModule.apiRequest(`/api/agent/memory/blocks/${blockId}`);
        
        // 显示编辑对话框（这里简化处理，实际应该有更完整的编辑界面）
        const confirmed = await window.uiModule.showConfirmDialog(`编辑记忆块 "${block.title}"?`);
        if (confirmed) {
            window.uiModule.showToast('编辑功能待实现', 'info');
        }
    } catch (error) {
        window.uiModule.showToast(`获取记忆块详情失败: ${error.message}`, 'error');
    }
}

// 删除记忆块
async function deleteMemoryBlock(blockId) {
    const confirmed = await window.uiModule.showConfirmDialog('确定要删除这个记忆块吗？');
    if (!confirmed) return;
    
    try {
        await window.connectionModule.apiRequest(`/api/agent/memory/blocks/${blockId}`, { method: 'DELETE' });
        window.uiModule.showToast('记忆块已删除', 'success');
        refreshCoreMemory(); // 刷新显示
    } catch (error) {
        window.uiModule.showToast(`删除记忆块失败: ${error.message}`, 'error');
    }
}

// 添加记忆块
async function addMemoryBlock(e) {
    e.preventDefault();
    
    const title = document.getElementById('memoryTitle').value;
    const description = document.getElementById('memoryDescription').value;
    const contentText = document.getElementById('memoryContent').value;
    
    // 将内容文本按行分割成数组
    const content = contentText.split('\n').filter(line => line.trim() !== '');
    
    try {
        await window.connectionModule.apiRequest('/api/agent/memory/blocks', {
            method: 'POST',
            body: JSON.stringify({ title, description, content })
        });
        
        window.uiModule.showToast('记忆块已添加', 'success');
        window.uiModule.hideAddMemoryBlockDialog();
        refreshCoreMemory(); // 刷新显示
        
        // 重置表单
        addMemoryBlockForm.reset();
    } catch (error) {
        window.uiModule.showToast(`添加记忆块失败: ${error.message}`, 'error');
    }
}

// 刷新工具
async function refreshTools() {
    if (!window.connectionModule.isConnected) return;
    
    try {
        const tools = await window.connectionModule.apiRequest('/api/agent/tools');
        displayTools(tools);
    } catch (error) {
        window.uiModule.showToast(`获取工具列表失败: ${error.message}`, 'error');
    }
}

// 显示工具
function displayTools(tools) {
    if (!toolsOutput) return;
    
    toolsOutput.innerHTML = `<pre>${tools.tools}</pre>`;
}

// 连接工具
async function connectTool() {
    const toolNameValue = toolName.value.trim();
    const aiToolNameValue = aiToolName.value.trim();
    
    if (!toolNameValue || !aiToolNameValue) {
        window.uiModule.showToast('请填写工具名称和AI工具名称', 'warning');
        return;
    }
    
    try {
        // 这里需要调用一个连接工具的API端点
        // 目前我们只是显示一个消息
        window.uiModule.showToast(`工具 "${toolNameValue}" 已连接到 "${aiToolNameValue}"`, 'success');
    } catch (error) {
        window.uiModule.showToast(`连接工具失败: ${error.message}`, 'error');
    }
}

// 导出函数供其他模块使用
window.agentModule = {
    refreshContext,
    displayAgentLogs,
    displayContext,
    refreshTempMemory,
    displayTempMemory,
    deleteTempMemoryItem,
    clearTempMemory,
    refreshCoreMemory,
    displayCoreMemory,
    editMemoryBlock,
    deleteMemoryBlock,
    addMemoryBlock,
    refreshTools,
    displayTools,
    connectTool
};