// dashboard_web/js/modules/agent.js

// Agent 控制相关元素
const agentLogsOutput = document.getElementById('agentLogsOutput');
const contextOutput = document.getElementById('contextOutput');
const refreshTempMemoryBtn = document.getElementById('refreshTempMemoryBtn');
const clearTempMemoryBtn = document.getElementById('clearTempMemoryBtn');
const tempMemoryOutput = document.getElementById('tempMemoryOutput');
const refreshCoreMemoryBtn = document.getElementById('refreshCoreMemoryBtn');
const addCoreMemoryBlockBtn = document.getElementById('addCoreMemoryBlockBtn');
const coreMemoryOutput = document.getElementById('coreMemoryOutput');

// Agent 相关功能

// --- NEW ---
// Displays the raw prompt text in the context area
function displayContextPromptMode(prompt) {
    const contextOutput = document.getElementById('contextOutput');
    if (!contextOutput) {
        return;
    }
    contextOutput.innerHTML = ''; // Clear previous content
    const pre = document.createElement('pre');
    pre.textContent = prompt;
    contextOutput.appendChild(pre);
    contextOutput.scrollTop = contextOutput.scrollHeight;
}

// --- MODIFIED ---
// Main function to refresh the context view based on the current mode
async function refreshContext() {
    if (!window.connectionModule.isConnected) {
        // Do not show toast here, as this can be called automatically
        return;
    }

    const contextViewMode = document.getElementById('contextViewMode');
    const isContextMode = contextViewMode && contextViewMode.checked;

    if (isContextMode) {
        // Fetch and display the full prompt via WebSocket
        try {
            const response = await window.connectionModule.sendAdminWsMessage('get_last_prompt');
            // Check if we got an error response
            if (response && response.status === 'error') {
                // If the agent doesn't support prompt generation, show a specific message
                if (response.message && response.message.includes('not support prompt generation')) {
                    displayContextPromptMode("当前Agent不支持查看完整提示词");
                } else {
                    displayContextPromptMode(`获取提示词失败: ${response.message}`);
                }
            } else if (response && response.prompt) {
                // Successfully got the prompt
                displayContextPromptMode(response.prompt);
            } else {
                // Unexpected response format
                displayContextPromptMode("获取提示词失败: 响应格式不正确");
            }
        } catch (error) {
            console.error('获取最新Prompt失败:', error);
            window.uiModule.showToast(`获取最新Prompt失败: ${error.message}`, 'error');
            displayContextPromptMode("获取提示词失败: 网络错误或服务器异常");
        }
    } else {
        // Fetch and display the conversation history via WebSocket
        try {
            const contextMessages = await window.connectionModule.sendAdminWsMessage('get_agent_context');
            displayContextConversationMode(contextMessages);
        } catch (error) {
            console.error('获取上下文失败:', error);
            window.uiModule.showToast(`获取上下文失败: ${error.message}`, 'error');
        }
    }
}

// 刷新初始化记忆 (通过WebSocket) - 现在由事件驱动，此函数可以保留用于手动刷新或初始化
async function refreshInitMemory() {
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    try {
        const initMemory = await window.connectionModule.sendAdminWsMessage('get_init_memory');
        // 清空现有内容并显示完整记忆
        const initMemoryOutput = document.getElementById('initMemoryOutput');
        if (initMemoryOutput) {
            initMemoryOutput.innerHTML = '';
        }
        displayInitMemory(initMemory);
    } catch (error) {
        console.error('获取初始化记忆失败:', error);
        window.uiModule.showToast(`获取初始化记忆失败: ${error.message}`, 'error');
    }
}

// 显示初始化记忆
function displayInitMemory(memory) {
    const initMemoryOutput = document.getElementById('initMemoryOutput');
    if (!initMemoryOutput) return;

    initMemoryOutput.innerHTML = ''; // 清空

    for (const [key, value] of Object.entries(memory)) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'memory-item';
        itemDiv.dataset.key = key;

        let valueDisplay;
        if (Array.isArray(value)) {
            valueDisplay = `<pre>${value.join('\n')}</pre>`;
        } else if (typeof value === 'object' && value !== null) {
            valueDisplay = `<pre>${JSON.stringify(value, null, 2)}</pre>`;
        } else {
            valueDisplay = `<span>${value}</span>`;
        }

        itemDiv.innerHTML = `
            <div class="memory-content">
                <strong>${key}:</strong>
                <div class="init-memory-value">${valueDisplay}</div>
            </div>
            <div class="memory-actions">
                <button class="btn small secondary edit-init-item-btn" data-key="${key}">编辑</button>
                <button class="btn small danger delete-init-item-btn" data-key="${key}">删除</button>
            </div>
        `;
        initMemoryOutput.appendChild(itemDiv);
    }

    // 绑定事件
    initMemoryOutput.querySelectorAll('.delete-init-item-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const key = e.target.dataset.key;
            deleteInitMemoryItem(key);
        });
    });

    initMemoryOutput.querySelectorAll('.edit-init-item-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const key = e.target.dataset.key;
            const itemDiv = e.target.closest('.memory-item');
            const value = memory[key];
            showEditInitMemoryItem(itemDiv, key, value);
        });
    });
}

// 显示编辑初始化记忆项的内联表单
function showEditInitMemoryItem(itemDiv, key, value) {
    let editValue;
    if (Array.isArray(value)) {
        editValue = value.join('\n');
    } else if (typeof value === 'object' && value !== null) {
        editValue = JSON.stringify(value, null, 2);
    } else {
        editValue = value;
    }

    const valueDiv = itemDiv.querySelector('.init-memory-value');
    const actionsDiv = itemDiv.querySelector('.memory-actions');

    // 保存原始按钮
    const originalActionsHTML = actionsDiv.innerHTML;

    valueDiv.innerHTML = `<textarea class="form-control" rows="4">${editValue}</textarea>`;
    actionsDiv.innerHTML = `
        <button class="btn small primary save-init-item-btn">保存</button>
        <button class="btn small secondary cancel-edit-init-item-btn">取消</button>
    `;

    actionsDiv.querySelector('.save-init-item-btn').addEventListener('click', async () => {
        const textarea = valueDiv.querySelector('textarea');
        const newValue = textarea.value;
        await updateInitMemoryItem(key, newValue);
    });

    actionsDiv.querySelector('.cancel-edit-init-item-btn').addEventListener('click', () => {
        // 简单起见，直接刷新
        refreshInitMemory();
    });
}


// 更新（或添加）初始化记忆项
async function updateInitMemoryItem(key, value) {
    let parsedValue = value;
    try {
        const trimmedValue = value.trim();
        if ((trimmedValue.startsWith('{') && trimmedValue.endsWith('}')) || (trimmedValue.startsWith('[') && trimmedValue.endsWith(']'))) {
            parsedValue = JSON.parse(trimmedValue);
        } else if (trimmedValue.includes('\n')) {
            parsedValue = trimmedValue.split('\n').filter(line => line.trim() !== '');
        }
    } catch (e) {
        // 解析失败，作为普通字符串处理
        console.warn("Value could not be parsed as JSON or array, saving as string.");
    }

    try {
        await window.connectionModule.sendAdminWsMessage('update_init_memory_item', { key, value: parsedValue });
        window.uiModule.showToast(`键 "${key}" 已更新`, 'success');
        // UI will be updated by the init_memory_updated event
    } catch (error) {
        window.uiModule.showToast(`更新失败: ${error.message}`, 'error');
    }
}


// 删除初始化记忆的键
async function deleteInitMemoryItem(key) {
    const confirmed = await window.uiModule.showConfirmDialog(`确定要删除键 "${key}" 吗？`);
    if (!confirmed) return;

    try {
        await window.connectionModule.sendAdminWsMessage('delete_init_memory_key', { key });
        window.uiModule.showToast(`键 "${key}" 已删除`, 'success');
        // The UI will be updated by the init_memory_updated event from the server.
    } catch (error) {
        window.uiModule.showToast(`删除失败: ${error.message}`, 'error');
    }
}


// 显示Agent日志 (由connection.js中的WebSocket消息处理，现在是流式更新)
function displayAgentLogs(logEntry) {
    if (!agentLogsOutput) return;

    // 创建并添加新的日志条目
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

    // 保持只显示最新的1000行日志
    const logEntries = agentLogsOutput.querySelectorAll('.log-entry');
    if (logEntries.length > 1000) {
        for (let i = 0; i < logEntries.length - 1000; i++) {
            logEntries[i].remove();
        }
    }

    // 滚动到底部以显示最新日志
    agentLogsOutput.scrollTop = agentLogsOutput.scrollHeight;
}

// 显示上下文 - 对话模式
function displayContextConversationMode(messages) {
    const contextOutput = document.getElementById('contextOutput');
    if (!contextOutput) {
        return;
    }
    
    // 在手动刷新时，清空现有内容并重新显示所有消息
    contextOutput.innerHTML = '';
    
    messages.forEach(msg => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'memory-item';
        itemDiv.dataset.messageId = msg.id;
        
        const timestampDisplay = new Date(msg.timestamp).toLocaleString();
        
        // 根据消息类型显示不同内容
        if (msg.type === "llm_interaction") {
            // 详细上下文条目（AI响应）
            // 格式化输入消息
            const inputMessagesHtml = msg.input_messages && msg.input_messages.length > 0 ? 
                `<div class="context-section">
                    <div><strong>输入消息:</strong></div>
                    <ul>
                        ${msg.input_messages.map(input => `<li><strong>${input.username}:</strong> ${input.text}</li>`).join('')}
                    </ul>
                </div>` : '';
            
            // 格式化工具执行
            const toolExecutionsHtml = msg.tool_executions && msg.tool_executions.length > 0 ? 
                `<div class="context-section">
                    <div><strong>工具执行:</strong></div>
                    <ul>
                        ${msg.tool_executions.map(tool => `
                            <li>
                                <div><strong>${tool.tool_name || tool.name || '未知工具'}</strong></div>
                                <div>参数: ${JSON.stringify(tool.arguments || tool.params || {}, null, 2)}</div>
                                ${tool.result ? `<div>结果: ${JSON.stringify(tool.result, null, 2)}</div>` : ''}
                                ${tool.error ? `<div class="error">错误: ${tool.error}</div>` : ''}
                            </li>
                        `).join('')}
                    </ul>
                </div>` : '';
            
            // 格式化提示词（截取前500个字符，避免过长）
            const promptPreview = msg.prompt ? msg.prompt.substring(0, 500) + (msg.prompt.length > 500 ? '...' : '') : '';
            const promptHtml = msg.prompt ? 
                `<div class="context-section">
                    <div><strong>提示词:</strong></div>
                    <div class="prompt-preview">${promptPreview}</div>
                    <button class="btn small secondary expand-prompt-btn" data-full-prompt="${encodeURIComponent(msg.prompt)}">展开完整提示词</button>
                </div>` : '';
            
            // 格式化LLM响应（截取前500个字符，避免过长）
            const llmResponsePreview = msg.llm_response ? msg.llm_response.substring(0, 500) + (msg.llm_response.length > 500 ? '...' : '') : '';
            const llmResponseHtml = msg.llm_response ? 
                `<div class="context-section">
                    <div><strong>LLM原始响应:</strong></div>
                    <div class="llm-response-preview">${llmResponsePreview}</div>
                    ${msg.llm_response.length > 500 ? `<button class="btn small secondary expand-llm-response-btn" data-full-response="${encodeURIComponent(msg.llm_response)}">展开完整响应</button>` : ''}
                </div>` : '';
            
            itemDiv.innerHTML = `
                <div class="memory-content">
                    <div><strong>[AI响应]</strong></div>
                    <div class="memory-time">${timestampDisplay}</div>
                </div>
                <div class="memory-details">
                    <div class="context-section">
                        <div><strong>最终响应:</strong></div>
                        <div>${msg.final_response || '无响应'}</div>
                    </div>
                    ${inputMessagesHtml}
                    ${toolExecutionsHtml}
                    ${promptHtml}
                    ${llmResponseHtml}
                </div>
            `;
        } else {
            // 简单上下文条目（用户消息或系统消息）
            const roleDisplay = msg.role === "user" ? "用户" : 
                              msg.role === "assistant" ? "助手" : 
                              msg.role === "system" ? "系统" : msg.role;
            
            itemDiv.innerHTML = `
                <div class="memory-content">
                    <div><strong>[${roleDisplay}]</strong> ${msg.content || ''}</div>
                    <div class="memory-time">${timestampDisplay}</div>
                </div>
            `;
        }
        
        contextOutput.appendChild(itemDiv);
    });
    
    // 绑定展开按钮事件
    bindExpandButtons();
    
    // 滚动到底部以显示最新内容
    contextOutput.scrollTop = contextOutput.scrollHeight;
}

// This function is now only for conversation mode.
function displayContext(messages) {
    displayContextConversationMode(messages);
}

// Handles live updates from WebSocket.
function displayAgentContext(newMessages) {
    const contextOutput = document.getElementById('contextOutput');
    if (!contextOutput || !Array.isArray(newMessages)) {
        return;
    }
    
    const contextViewMode = document.getElementById('contextViewMode');
    const isContextMode = contextViewMode && contextViewMode.checked;

    // If we are in prompt mode, we need to refresh the prompt display
    // because context changes affect the generated prompt
    if (isContextMode) {
        // Refresh the prompt view
        refreshContext();
        return;
    }

    // Proceed with conversation mode update
    // Clear existing content and display all messages (for WebSocket updates)
    contextOutput.innerHTML = '';
    newMessages.forEach(msg => addMessageToContext(contextOutput, msg, false));
    
    bindExpandButtons();
    contextOutput.scrollTop = contextOutput.scrollHeight;
    
    const messageItems = contextOutput.querySelectorAll('.memory-item');
    if (messageItems.length > 1000) {
        for (let i = 0; i < messageItems.length - 1000; i++) {
            messageItems[i].remove();
        }
    }
}

// Rerenders the context view when the toggle is switched.
function rerenderContext() {
    // The main refresh function now handles the mode switching
    refreshContext();
}

// 添加单条消息到上下文显示区域
function addMessageToContext(contextOutput, msg, isRawMode) {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'memory-item';
    itemDiv.dataset.messageId = msg.id; // 添加消息ID作为数据属性
    
    const timestampDisplay = new Date(msg.timestamp).toLocaleString();
    
    // This function is now only for conversation mode.
    if (isRawMode) {
        // This block is now legacy, as raw mode is replaced by prompt mode.
        // Kept for safety, but should not be triggered.
        itemDiv.innerHTML = `
            <div class="memory-content">
                <div><strong>[消息]</strong></div>
                <div class="memory-time">${timestampDisplay}</div>
            </div>
            <div class="memory-details">
                <pre>${JSON.stringify(msg, null, 2)}</pre>
            </div>
        `;
    } else {
        // 对话模式显示
        if (msg.type === "llm_interaction") {
            // 详细上下文条目（AI响应）
            // 格式化输入消息
            const inputMessagesHtml = msg.input_messages && msg.input_messages.length > 0 ? 
                `<div class="context-section">
                    <div><strong>输入消息:</strong></div>
                    <ul>
                        ${msg.input_messages.map(input => `<li><strong>${input.username}:</strong> ${input.text}</li>`).join('')}
                    </ul>
                </div>` : '';
            
            // 格式化工具执行
            const toolExecutionsHtml = msg.tool_executions && msg.tool_executions.length > 0 ? 
                `<div class="context-section">
                    <div><strong>工具执行:</strong></div>
                    <ul>
                        ${msg.tool_executions.map(tool => `
                            <li>
                                <div><strong>${tool.tool_name || tool.name || '未知工具'}</strong></div>
                                <div>参数: ${JSON.stringify(tool.arguments || tool.params || {}, null, 2)}</div>
                                ${tool.result ? `<div>结果: ${JSON.stringify(tool.result, null, 2)}</div>` : ''}
                                ${tool.error ? `<div class="error">错误: ${tool.error}</div>` : ''}
                            </li>
                        `).join('')}
                    </ul>
                </div>` : '';
            
            // 格式化提示词（截取前500个字符，避免过长）
            const promptPreview = msg.prompt ? msg.prompt.substring(0, 500) + (msg.prompt.length > 500 ? '...' : '') : '';
            const promptHtml = msg.prompt ? 
                `<div class="context-section">
                    <div><strong>提示词:</strong></div>
                    <div class="prompt-preview">${promptPreview}</div>
                    <button class="btn small secondary expand-prompt-btn" data-full-prompt="${encodeURIComponent(msg.prompt)}">展开完整提示词</button>
                </div>` : '';
            
            // 格式化LLM响应（截取前500个字符，避免过长）
            const llmResponsePreview = msg.llm_response ? msg.llm_response.substring(0, 500) + (msg.llm_response.length > 500 ? '...' : '') : '';
            const llmResponseHtml = msg.llm_response ? 
                `<div class="context-section">
                    <div><strong>LLM原始响应:</strong></div>
                    <div class="llm-response-preview">${llmResponsePreview}</div>
                    ${msg.llm_response.length > 500 ? `<button class="btn small secondary expand-llm-response-btn" data-full-response="${encodeURIComponent(msg.llm_response)}">展开完整响应</button>` : ''}
                </div>` : '';
            
            itemDiv.innerHTML = `
                <div class="memory-content">
                    <div><strong>[AI响应]</strong></div>
                    <div class="memory-time">${timestampDisplay}</div>
                </div>
                <div class="memory-details">
                    <div class="context-section">
                        <div><strong>最终响应:</strong></div>
                        <div>${msg.final_response || '无响应'}</div>
                    </div>
                    ${inputMessagesHtml}
                    ${toolExecutionsHtml}
                    ${promptHtml}
                    ${llmResponseHtml}
                </div>
            `;
        } else {
            // 简单上下文条目（用户消息或系统消息）
            const roleDisplay = msg.role === "user" ? "用户" : 
                              msg.role === "assistant" ? "助手" : 
                              msg.role === "system" ? "系统" : msg.role;
            
            itemDiv.innerHTML = `
                <div class="memory-content">
                    <div><strong>[${roleDisplay}]</strong> ${msg.content || ''}</div>
                    <div class="memory-time">${timestampDisplay}</div>
                </div>
            `;
        }
    }
    
    contextOutput.appendChild(itemDiv);
}

// 刷新临时记忆 (通过WebSocket) - 现在由事件驱动，此函数可以保留用于手动刷新或初始化
async function refreshTempMemory() {
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    try {
        const tempMemory = await window.connectionModule.sendAdminWsMessage('get_temp_memory');
        // 清空现有内容并显示完整记忆
        const tempMemoryOutput = document.getElementById('tempMemoryOutput');
        if (tempMemoryOutput) {
            tempMemoryOutput.innerHTML = '';
        }
        displayTempMemory(tempMemory);
    } catch (error) {
        console.error('获取临时记忆失败:', error);
        window.uiModule.showToast(`获取临时记忆失败: ${error.message}`, 'error');
    }
}

// 显示临时记忆 (支持流式更新)
function displayTempMemory(messages) {
    const tempMemoryOutput = document.getElementById('tempMemoryOutput');
    if (!tempMemoryOutput) {
        return;
    }
    
    // 如果只有一个消息对象，则认为是流式更新，追加到现有内容
    if (!Array.isArray(messages)) {
        // 创建新的记忆项
        const msg = messages;
        const itemDiv = document.createElement('div');
        itemDiv.className = 'memory-item';
        
        const timestamp = new Date(msg.timestamp).toLocaleString();
        
        // 为流式更新的消息生成一个唯一ID（如果后端没有提供）
        const messageId = msg.id || `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        itemDiv.dataset.messageId = messageId;
        
        itemDiv.innerHTML = `
            <div class="memory-content">
                <div><strong>[${msg.role}]</strong> ${msg.content || msg.text || ''}</div>
                <div class="memory-time">${timestamp}</div>
            </div>
            <div class="memory-actions">
                <button class="btn small danger delete-temp-memory-btn" data-id="${messageId}">删除</button>
            </div>
        `;
        
        tempMemoryOutput.appendChild(itemDiv);
        
        // 绑定删除按钮事件
        const deleteButton = itemDiv.querySelector('.delete-temp-memory-btn');
        if (deleteButton) {
            deleteButton.addEventListener('click', (e) => {
                // 对于流式更新的消息，我们可能需要一个不同的删除机制
                // 这里暂时只从UI上移除
                itemDiv.remove();
            });
        }
        
        // 滚动到底部
        tempMemoryOutput.scrollTop = tempMemoryOutput.scrollHeight;
        
        // 保持只显示最新的100条消息
        const messageItems = tempMemoryOutput.querySelectorAll('.memory-item');
        if (messageItems.length > 100) {
            for (let i = 0; i < messageItems.length - 100; i++) {
                messageItems[i].remove();
            }
        }
        
        return;
    }
    
    // 如果是数组，则认为是完整刷新，清空现有内容并重新显示所有消息
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
                <button class="btn small danger delete-temp-memory-btn" data-id="${msg.id}">删除</button>
            </div>
        `;
        
        tempMemoryOutput.appendChild(itemDiv);
    });
    
    // 绑定删除按钮事件
    const deleteButtons = tempMemoryOutput.querySelectorAll('.delete-temp-memory-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const itemId = e.target.dataset.id;
            deleteTempMemoryItem(itemId);
        });
    });
}



// 删除临时记忆项
async function deleteTempMemoryItem(itemId) {
    if (!itemId) {
        window.uiModule.showToast('无法删除：缺少项目ID', 'error');
        return;
    }
    const confirmed = await window.uiModule.showConfirmDialog('确定要删除这条临时记忆吗？');
    if (!confirmed) return;
    
    try {
        await window.connectionModule.sendAdminWsMessage('delete_temp_memory_item', { item_id: itemId });
        window.uiModule.showToast('删除请求已发送', 'success');
        // The UI will be updated by the temp_memory_updated event from the server.
    } catch (error) {
        window.uiModule.showToast(`删除记忆项失败: ${error.message}`, 'error');
    }
}

// 清空临时记忆 (通过WebSocket)
async function clearTempMemory() {
    const confirmed = await window.uiModule.showConfirmDialog('确定要清空所有临时记忆吗？');
    if (!confirmed) return;
    
    try {
        await window.connectionModule.sendAdminWsMessage('clear_temp_memory');
        tempMemoryOutput.innerHTML = '';
        window.uiModule.showToast('临时记忆已清空', 'success');
    } catch (error) {
        window.uiModule.showToast(`清空临时记忆失败: ${error.message}`, 'error');
    }
}

// 刷新核心记忆 (通过WebSocket) - 现在由事件驱动，此函数可以保留用于手动刷新或初始化
async function refreshCoreMemory() {
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    try {
        const blocks = await window.connectionModule.sendAdminWsMessage('get_core_memory_blocks');
        // 清空现有内容并显示完整记忆
        const coreMemoryOutput = document.getElementById('coreMemoryOutput');
        if (coreMemoryOutput) {
            coreMemoryOutput.innerHTML = '';
        }
        displayCoreMemory(blocks);
    } catch (error) {
        console.error('获取核心记忆失败:', error);
        window.uiModule.showToast(`获取核心记忆失败: ${error.message}`, 'error');
    }
}

// 显示核心记忆
function displayCoreMemory(blocks) {
    const coreMemoryOutput = document.getElementById('coreMemoryOutput');
    if (!coreMemoryOutput) {
        return;
    }
    
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
    // 获取记忆块详情 (通过WebSocket)
    try {
        const block = await window.connectionModule.sendAdminWsMessage('get_core_memory_block', { block_id: blockId });
        showEditMemoryBlockDialog(block);
    } catch (error) {
        window.uiModule.showToast(`获取记忆块详情失败: ${error.message}`, 'error');
    }
}

// 显示编辑记忆块对话框
function showEditMemoryBlockDialog(block) {
    // 创建对话框元素
    const dialog = document.createElement('div');
    dialog.className = 'modal-dialog show';
    dialog.id = 'editMemoryBlockDialog';
    
    dialog.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>编辑记忆块</h3>
                <button class="close-btn">&times;</button>
            </div>
            <div class="modal-body">
                <form id="editMemoryBlockForm">
                    <input type="hidden" id="editBlockId" value="${block.id}">
                    <div class="form-group">
                        <label for="editMemoryTitle">标题:</label>
                        <input type="text" id="editMemoryTitle" value="${block.title}" required class="form-control">
                    </div>
                    <div class="form-group">
                        <label for="editMemoryDescription">描述:</label>
                        <textarea id="editMemoryDescription" rows="2" class="form-control">${block.description}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="editMemoryContent">内容 (每行一条):</label>
                        <textarea id="editMemoryContent" rows="4" class="form-control">${block.content.join('\n')}</textarea>
                    </div>
                    <div class="button-group">
                        <button type="button" class="btn secondary" id="cancelEditMemoryBtn">取消</button>
                        <button type="submit" class="btn primary">保存</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    // 添加到文档中
    document.body.appendChild(dialog);
    
    // 绑定事件
    const closeBtn = dialog.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelEditMemoryBtn');
    const form = document.getElementById('editMemoryBlockForm');
    
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
        
        const blockId = document.getElementById('editBlockId').value;
        const title = document.getElementById('editMemoryTitle').value;
        const description = document.getElementById('editMemoryDescription').value;
        const contentText = document.getElementById('editMemoryContent').value;
        
        // 将内容文本按行分割成数组
        const content = contentText.split('\n').filter(line => line.trim() !== '');
        
        try {
            await window.connectionModule.sendAdminWsMessage('update_core_memory_block', { block_id: blockId, title, description, content });
            
            window.uiModule.showToast('记忆块已更新', 'success');
            closeDialog();
            refreshCoreMemory(); // 刷新显示
        } catch (error) {
            window.uiModule.showToast(`更新记忆块失败: ${error.message}`, 'error');
        }
    });
}

// 删除记忆块 (通过WebSocket)
async function deleteMemoryBlock(blockId) {
    const confirmed = await window.uiModule.showConfirmDialog('确定要删除这个记忆块吗？');
    if (!confirmed) return;
    
    try {
        await window.connectionModule.sendAdminWsMessage('delete_core_memory_block', { block_id: blockId });
        window.uiModule.showToast('记忆块已删除', 'success');
        refreshCoreMemory(); // 刷新显示
    } catch (error) {
        window.uiModule.showToast(`删除记忆块失败: ${error.message}`, 'error');
    }
}

// 添加记忆块 (通过WebSocket)
async function addMemoryBlock(e) {
    e.preventDefault();
    
    const title = document.getElementById('memoryTitle').value;
    const description = document.getElementById('memoryDescription').value;
    const contentText = document.getElementById('memoryContent').value;
    
    // 将内容文本按行分割成数组
    const content = contentText.split('\n').filter(line => line.trim() !== '');
    
    try {
        await window.connectionModule.sendAdminWsMessage('create_core_memory_block', { title, description, content });
        
        window.uiModule.showToast('记忆块已添加', 'success');
        window.uiModule.hideAddMemoryBlockDialog();
        refreshCoreMemory(); // 刷新显示
        
        // 重置表单
        addMemoryBlockForm.reset();
    } catch (error) {
        window.uiModule.showToast(`添加记忆块失败: ${error.message}`, 'error');
    }
}



// 导出函数供其他模块使用
window.agentModule = {
    refreshContext,
    displayAgentLogs,
    displayContext,
    displayAgentContext,
    rerenderContext,
    refreshInitMemory,
    displayInitMemory,
    updateInitMemoryItem,
    refreshTempMemory,
    displayTempMemory,
    deleteTempMemoryItem,
    clearTempMemory,
    refreshCoreMemory,
    displayCoreMemory,
    editMemoryBlock,
    deleteMemoryBlock,
    addMemoryBlock
};


function bindExpandButtons() {
    // 展开完整提示词按钮
    const expandPromptButtons = document.querySelectorAll('.expand-prompt-btn');
    expandPromptButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const fullPrompt = decodeURIComponent(e.target.dataset.fullPrompt);
            // 在新窗口中显示完整提示词
            const newWindow = window.open('', '_blank');
            newWindow.document.write(`
                <html>
                <head>
                    <title>完整提示词</title>
                    <style>
                        body { font-family: monospace; white-space: pre-wrap; margin: 20px; }
                    </style>
                </head>
                <body>${fullPrompt.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</body>
                </html>
            `);
            newWindow.document.close();
        });
    });
    
    // 展开完整LLM响应按钮
    const expandLlmResponseButtons = document.querySelectorAll('.expand-llm-response-btn');
    expandLlmResponseButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const fullResponse = decodeURIComponent(e.target.dataset.fullResponse);
            // 在新窗口中显示完整LLM响应
            const newWindow = window.open('', '_blank');
            newWindow.document.write(`
                <html>
                <head>
                    <title>完整LLM响应</title>
                    <style>
                        body { font-family: monospace; white-space: pre-wrap; margin: 20px; }
                    </style>
                </head>
                <body>${fullResponse.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</body>
                </html>
            `);
            newWindow.document.close();
        });
    });
}