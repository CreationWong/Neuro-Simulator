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
    if (!window.connectionModule.isConnected) {
        return;
    }
    
    try {
        const contextMessages = await window.connectionModule.apiRequest('/api/agent/context');
        displayContext(contextMessages);
    } catch (error) {
        console.error('获取上下文失败:', error);
        window.uiModule.showToast(`获取上下文失败: ${error.message}`, 'error');
    }
}

// 刷新初始化记忆
async function refreshInitMemory() {
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    try {
        const initMemory = await window.connectionModule.apiRequest('/api/agent/memory/init');
        displayInitMemory(initMemory);
    } catch (error) {
        console.error('获取初始化记忆失败:', error);
        window.uiModule.showToast(`获取初始化记忆失败: ${error.message}`, 'error');
    }
}

// 显示初始化记忆
function displayInitMemory(memory) {
    const initMemoryOutput = document.getElementById('initMemoryOutput');
    if (!initMemoryOutput) {
        return;
    }
    
    initMemoryOutput.innerHTML = '';
    
    // 创建编辑表单
    const form = document.createElement('form');
    form.id = 'initMemoryForm';
    
    // 添加一个隐藏的输入框来存储原始的键列表
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.id = 'initMemoryKeys';
    hiddenInput.value = JSON.stringify(Object.keys(memory));
    form.appendChild(hiddenInput);
    
    // 遍历记忆对象的每个属性
    for (const [key, value] of Object.entries(memory)) {
        const formGroup = document.createElement('div');
        formGroup.className = 'form-group';
        formGroup.dataset.key = key; // 添加数据属性以便于识别
        
        const label = document.createElement('label');
        label.textContent = key;
        label.setAttribute('for', `init-memory-${key}`);
        
        // 创建删除按钮
        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'btn small danger delete-init-key-btn';
        deleteBtn.textContent = '删除';
        deleteBtn.dataset.key = key;
        deleteBtn.style.float = 'right';
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            deleteInitMemoryKey(key);
        });
        
        let input;
        if (Array.isArray(value)) {
            // 对于数组，使用文本域
            input = document.createElement('textarea');
            input.value = value.join('\n');
            input.rows = 4;
        } else if (typeof value === 'object' && value !== null) {
            // 对于对象，使用文本域显示JSON
            input = document.createElement('textarea');
            input.value = JSON.stringify(value, null, 2);
            input.rows = 6;
        } else {
            // 对于字符串和其他基本类型，使用输入框
            input = document.createElement('input');
            input.type = 'text';
            input.value = value;
        }
        
        input.id = `init-memory-${key}`;
        input.name = key;
        input.className = 'form-control';
        
        label.appendChild(deleteBtn);
        formGroup.appendChild(label);
        formGroup.appendChild(input);
        form.appendChild(formGroup);
    }
    
    // 添加新增键的表单
    const addKeyGroup = document.createElement('div');
    addKeyGroup.className = 'form-group';
    
    const addKeyLabel = document.createElement('label');
    addKeyLabel.textContent = '添加新键:';
    
    const newKeyInput = document.createElement('input');
    newKeyInput.type = 'text';
    newKeyInput.id = 'newInitMemoryKey';
    newKeyInput.placeholder = '输入新键名';
    newKeyInput.className = 'form-control';
    
    const addKeyBtn = document.createElement('button');
    addKeyBtn.type = 'button';
    addKeyBtn.className = 'btn secondary';
    addKeyBtn.textContent = '添加';
    addKeyBtn.addEventListener('click', addInitMemoryKey);
    
    addKeyGroup.appendChild(addKeyLabel);
    addKeyGroup.appendChild(newKeyInput);
    addKeyGroup.appendChild(addKeyBtn);
    form.appendChild(addKeyGroup);
    
    // 添加保存按钮
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'button-group';
    
    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn primary';
    saveBtn.textContent = '保存';
    saveBtn.addEventListener('click', saveInitMemory);
    
    const resetBtn = document.createElement('button');
    resetBtn.type = 'button';
    resetBtn.className = 'btn secondary';
    resetBtn.textContent = '重置';
    resetBtn.addEventListener('click', refreshInitMemory);
    
    buttonGroup.appendChild(resetBtn);
    buttonGroup.appendChild(saveBtn);
    form.appendChild(buttonGroup);
    
    initMemoryOutput.appendChild(form);
}

// 删除初始化记忆的键
function deleteInitMemoryKey(key) {
    const confirmed = window.confirm(`确定要删除键 "${key}" 吗？`);
    if (!confirmed) return;
    
    const formGroup = document.querySelector(`.form-group[data-key="${key}"]`);
    if (formGroup) {
        formGroup.remove();
        
        // 更新隐藏的键列表
        const hiddenInput = document.getElementById('initMemoryKeys');
        if (hiddenInput) {
            const keys = JSON.parse(hiddenInput.value);
            const index = keys.indexOf(key);
            if (index > -1) {
                keys.splice(index, 1);
                hiddenInput.value = JSON.stringify(keys);
            }
        }
    }
}

// 添加初始化记忆的键
function addInitMemoryKey() {
    const newKeyInput = document.getElementById('newInitMemoryKey');
    const key = newKeyInput.value.trim();
    
    if (!key) {
        window.uiModule.showToast('请输入键名', 'warning');
        return;
    }
    
    // 检查键是否已存在
    const existingInput = document.getElementById(`init-memory-${key}`);
    if (existingInput) {
        window.uiModule.showToast(`键 "${key}" 已存在`, 'warning');
        return;
    }
    
    // 创建新的表单组
    const form = document.getElementById('initMemoryForm');
    const formGroup = document.createElement('div');
    formGroup.className = 'form-group';
    formGroup.dataset.key = key;
    
    const label = document.createElement('label');
    label.textContent = key;
    label.setAttribute('for', `init-memory-${key}`);
    
    // 创建删除按钮
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn small danger delete-init-key-btn';
    deleteBtn.textContent = '删除';
    deleteBtn.dataset.key = key;
    deleteBtn.style.float = 'right';
    deleteBtn.addEventListener('click', (e) => {
        e.preventDefault();
        deleteInitMemoryKey(key);
    });
    
    const input = document.createElement('input');
    input.type = 'text';
    input.id = `init-memory-${key}`;
    input.name = key;
    input.className = 'form-control';
    input.value = '';
    
    label.appendChild(deleteBtn);
    formGroup.appendChild(label);
    formGroup.appendChild(input);
    
    // 插入到添加键的表单组之前
    const addKeyGroup = document.querySelector('#newInitMemoryKey').closest('.form-group');
    form.insertBefore(formGroup, addKeyGroup);
    
    // 更新隐藏的键列表
    const hiddenInput = document.getElementById('initMemoryKeys');
    if (hiddenInput) {
        const keys = JSON.parse(hiddenInput.value);
        if (!keys.includes(key)) {
            keys.push(key);
            hiddenInput.value = JSON.stringify(keys);
        }
    }
    
    // 清空输入框
    newKeyInput.value = '';
    
    window.uiModule.showToast(`已添加键 "${key}"`, 'success');
}

// 保存初始化记忆
async function saveInitMemory() {
    const form = document.getElementById('initMemoryForm');
    if (!form) return;
    
    const updatedMemory = {};
    
    // 获取所有表单元素
    const formElements = form.querySelectorAll('.form-group[data-key] .form-control');
    
    // 构造更新后的记忆对象
    formElements.forEach(element => {
        const key = element.name;
        const value = element.value;
        
        // 尝试解析JSON对象
        try {
            const trimmedValue = value.trim();
            if (trimmedValue.startsWith('{') || trimmedValue.startsWith('[')) {
                updatedMemory[key] = JSON.parse(trimmedValue);
            } else if (trimmedValue.includes('\n')) {
                // 处理多行文本（数组）
                updatedMemory[key] = trimmedValue.split('\n').filter(line => line.trim() !== '');
            } else {
                // 其他情况作为字符串处理
                updatedMemory[key] = value;
            }
        } catch (e) {
            // 如果JSON解析失败，作为字符串处理
            updatedMemory[key] = value;
        }
    });
    
    try {
        await window.connectionModule.apiRequest('/api/agent/memory/init', {
            method: 'PUT',
            body: JSON.stringify({ memory: updatedMemory })
        });
        window.uiModule.showToast('初始化记忆保存成功', 'success');
    } catch (error) {
        console.error('保存初始化记忆失败:', error);
        window.uiModule.showToast(`保存初始化记忆失败: ${error.message}`, 'error');
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

// 显示上下文 - 原始模式
function displayContextRawMode(messages) {
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
        
        itemDiv.innerHTML = `
            <div class="memory-content">
                <div><strong>[消息]</strong></div>
                <div class="memory-time">${timestampDisplay}</div>
            </div>
            <div class="memory-details">
                <pre>${JSON.stringify(msg, null, 2)}</pre>
            </div>
        `;
        
        contextOutput.appendChild(itemDiv);
    });
    
    // 滚动到底部以显示最新内容
    contextOutput.scrollTop = contextOutput.scrollHeight;
}

// 显示上下文（根据当前模式）
function displayContext(messages) {
    const contextOutput = document.getElementById('contextOutput');
    if (!contextOutput) {
        return;
    }
    
    const contextViewMode = document.getElementById('contextViewMode');
    
    // 在手动刷新时，清空现有内容并重新显示所有消息
    contextOutput.innerHTML = '';
    
    if (contextViewMode && contextViewMode.checked) {
        displayContextRawMode(messages);
    } else {
        displayContextConversationMode(messages);
    }
}

// 显示Agent上下文（WebSocket消息处理）
function displayAgentContext(messages) {
    const contextOutput = document.getElementById('contextOutput');
    if (!contextOutput || !Array.isArray(messages)) {
        return;
    }
    
    // 获取当前显示模式
    const contextViewMode = document.getElementById('contextViewMode');
    const isRawMode = contextViewMode && contextViewMode.checked;
    
    // 找出新的消息（在现有上下文中不存在的消息）
    const existingMessageIds = new Set();
    const existingItems = contextOutput.querySelectorAll('.memory-item');
    existingItems.forEach(item => {
        const messageId = item.dataset.messageId;
        if (messageId) {
            existingMessageIds.add(messageId);
        }
    });
    
    // 只添加新的消息
    const newMessages = messages.filter(msg => !existingMessageIds.has(msg.id));
    
    // 逐条添加新消息
    newMessages.forEach(msg => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'memory-item';
        itemDiv.dataset.messageId = msg.id; // 添加消息ID作为数据属性
        
        const timestampDisplay = new Date(msg.timestamp).toLocaleString();
        
        if (isRawMode) {
            // 原始模式显示
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
    });
    
    // 绑定展开按钮事件
    if (newMessages.length > 0) {
        bindExpandButtons();
    }
    
    // 只有在添加了新消息时才滚动到底部
    if (newMessages.length > 0) {
        contextOutput.scrollTop = contextOutput.scrollHeight;
    }
}

// 重新渲染上下文（不重新获取数据，仅切换显示模式）
function rerenderContext() {
    // 获取当前上下文输出区域
    const contextOutput = document.getElementById('contextOutput');
    if (!contextOutput) {
        return;
    }
    
    // 获取当前的显示模式
    const contextViewMode = document.getElementById('contextViewMode');
    const isRawMode = contextViewMode && contextViewMode.checked;
    
    // 更新模式标签
    const modeLabel = document.getElementById('modeLabel');
    if (modeLabel) {
        modeLabel.textContent = isRawMode ? '原始模式' : '对话模式';
    }
    
    // 重新渲染所有消息
    const messages = Array.from(contextOutput.querySelectorAll('.memory-item')).map(item => {
        // 从现有DOM元素中提取消息数据
        // 这是一个简化的实现，实际应用中可能需要更复杂的数据提取逻辑
        return {
            id: item.dataset.messageId,
            // 其他字段需要从DOM中提取或重新获取
        };
    });
    
    // 最简单和最可靠的方法是重新获取数据
    // 这样可以确保所有消息都按照正确的格式显示
    refreshContext();
}

// 刷新临时记忆
async function refreshTempMemory() {
    // 强制检查window.connectionModule是否存在
    if (!window.connectionModule) {
        window.uiModule.showToast('系统错误：连接模块未找到', 'error');
        return;
    }
    
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    // 检查API请求函数是否存在
    if (!window.connectionModule.apiRequest) {
        window.uiModule.showToast('系统错误：API请求函数未找到', 'error');
        return;
    }
    
    try {
        // 获取完整的临时记忆内容
        const tempMemory = await window.connectionModule.apiRequest('/api/agent/memory/temp');
        displayTempMemory(tempMemory);
    } catch (error) {
        console.error('获取临时记忆失败:', error);
        window.uiModule.showToast(`获取临时记忆失败: ${error.message}`, 'error');
    }
}

// 显示临时记忆
function displayTempMemory(messages) {
    const tempMemoryOutput = document.getElementById('tempMemoryOutput');
    if (!tempMemoryOutput) {
        return;
    }
    
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
            refreshTempMemory(); // 刷新显示
        } catch (error) {
            window.uiModule.showToast(`添加临时记忆失败: ${error.message}`, 'error');
        }
    });
}

// 编辑临时记忆项
async function editTempMemoryItem(index) {
    // 获取当前临时记忆项
    const items = tempMemoryOutput.querySelectorAll('.memory-item');
    if (!items[index]) return;
    
    // 提取当前项的内容
    const item = items[index];
    const roleElement = item.querySelector('strong');
    const contentElement = item.querySelector('.memory-content');
    
    // 获取角色和内容
    const roleMatch = roleElement.textContent.match(/\[(.*?)\]/);
    const role = roleMatch ? roleMatch[1] : 'system';
    const content = contentElement.textContent.replace(`[${role}] `, '').trim();
    
    // 创建对话框元素
    const dialog = document.createElement('div');
    dialog.className = 'modal-dialog show';
    dialog.id = 'editTempMemoryDialog';
    
    dialog.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>编辑临时记忆</h3>
                <button class="close-btn">&times;</button>
            </div>
            <div class="modal-body">
                <form id="editTempMemoryForm">
                    <input type="hidden" id="editTempMemoryIndex" value="${index}">
                    <div class="form-group">
                        <label for="editTempMemoryRole">角色:</label>
                        <select id="editTempMemoryRole" class="form-control">
                            <option value="system" ${role === 'system' ? 'selected' : ''}>system</option>
                            <option value="user" ${role === 'user' ? 'selected' : ''}>user</option>
                            <option value="assistant" ${role === 'assistant' ? 'selected' : ''}>assistant</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="editTempMemoryContent">内容:</label>
                        <textarea id="editTempMemoryContent" rows="4" class="form-control">${content}</textarea>
                    </div>
                    <div class="button-group">
                        <button type="button" class="btn secondary" id="cancelEditTempMemoryBtn">取消</button>
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
    const cancelBtn = document.getElementById('cancelEditTempMemoryBtn');
    const form = document.getElementById('editTempMemoryForm');
    
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
        
        const role = document.getElementById('editTempMemoryRole').value;
        const content = document.getElementById('editTempMemoryContent').value;
        
        if (!content.trim()) {
            window.uiModule.showToast('请输入内容', 'warning');
            return;
        }
        
        try {
            // 对于builtin agent，我们无法直接编辑单个消息
            // 所以我们删除旧项并添加新项
            const confirmed = await window.uiModule.showConfirmDialog('编辑临时记忆需要删除当前项并添加新项，确定继续吗？');
            if (!confirmed) return;
            
            // 删除当前项
            items[index].remove();
            
            // 添加新项
            await window.connectionModule.apiRequest('/api/agent/memory/temp', {
                method: 'POST',
                body: JSON.stringify({ content, role })
            });
            
            window.uiModule.showToast('临时记忆已更新', 'success');
            closeDialog();
            refreshTempMemory(); // 刷新显示
        } catch (error) {
            window.uiModule.showToast(`更新临时记忆失败: ${error.message}`, 'error');
        }
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
    // 强制检查window.connectionModule是否存在
    if (!window.connectionModule) {
        window.uiModule.showToast('系统错误：连接模块未找到', 'error');
        return;
    }
    
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    // 检查API请求函数是否存在
    if (!window.connectionModule.apiRequest) {
        window.uiModule.showToast('系统错误：API请求函数未找到', 'error');
        return;
    }
    
    try {
        const blocks = await window.connectionModule.apiRequest('/api/agent/memory/blocks');
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
    // 获取记忆块详情
    try {
        const block = await window.connectionModule.apiRequest(`/api/agent/memory/blocks/${blockId}`);
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
            await window.connectionModule.apiRequest(`/api/agent/memory/blocks/${blockId}`, {
                method: 'PUT',
                body: JSON.stringify({ title, description, content })
            });
            
            window.uiModule.showToast('记忆块已更新', 'success');
            closeDialog();
            refreshCoreMemory(); // 刷新显示
        } catch (error) {
            window.uiModule.showToast(`更新记忆块失败: ${error.message}`, 'error');
        }
    });
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
    // 强制检查window.connectionModule是否存在
    if (!window.connectionModule) {
        window.uiModule.showToast('系统错误：连接模块未找到', 'error');
        return;
    }
    
    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }
    
    // 检查API请求函数是否存在
    if (!window.connectionModule.apiRequest) {
        window.uiModule.showToast('系统错误：API请求函数未找到', 'error');
        return;
    }
    
    try {
        const tools = await window.connectionModule.apiRequest('/api/agent/tools');
        displayTools(tools);
    } catch (error) {
        console.error('获取工具列表失败:', error);
        window.uiModule.showToast(`获取工具列表失败: ${error.message}`, 'error');
    }
}

// 显示工具
function displayTools(tools) {
    const toolsOutput = document.getElementById('toolsOutput');
    if (!toolsOutput) {
        return;
    }
    
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
    displayAgentContext,
    rerenderContext,
    refreshInitMemory,
    displayInitMemory,
    saveInitMemory,
    refreshTempMemory,
    displayTempMemory,
    deleteTempMemoryItem,
    editTempMemoryItem,
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

// 绑定展开按钮事件
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