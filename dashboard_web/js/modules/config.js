// dashboard_web/js/modules/config.js

// 配置管理相关元素
const configForm = document.getElementById('configForm');
const resetConfigBtn = document.getElementById('resetConfigBtn');
let currentConfig = {}; // 存储当前配置

// 将配置对象转换为表单值
function configToForm(config) {
    const configForm = document.getElementById('configForm');
    if (!configForm) {
        return;
    }
    
    // 遍历表单中的每个输入元素
    const formElements = configForm.querySelectorAll('input, select, textarea');
    
    formElements.forEach(element => {
        const name = element.name;
        if (!name) return;
        
        // 解析嵌套属性路径 (例如: stream_metadata.stream_title)
        const keys = name.split('.');
        let value = config;
        
        // 通过路径获取配置值
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                value = undefined;
                break;
            }
        }
        
        // 根据元素类型设置值
        if (value !== undefined) {
            if (element.type === 'checkbox') {
                element.checked = value;
            } else if (Array.isArray(value)) {
                // 对于数组类型，将其转换为逗号分隔的字符串
                element.value = value.join(', ');
            } else {
                element.value = value;
            }
        }
    });
}

// 将表单值转换为配置对象
function formToConfig() {
    const configForm = document.getElementById('configForm');
    if (!configForm) {
        return {};
    }
    
    const config = {};
    
    // 遍历表单中的每个输入元素
    const formElements = configForm.querySelectorAll('input, select, textarea');
    
    formElements.forEach(element => {
        const name = element.name;
        if (!name) return;
        
        // 解析嵌套属性路径 (例如: stream_metadata.stream_title)
        const keys = name.split('.');
        let obj = config;
        
        // 创建嵌套对象结构
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!(key in obj)) {
                obj[key] = {};
            }
            obj = obj[key];
        }
        
        // 设置最终值
        const lastKey = keys[keys.length - 1];
        if (element.type === 'checkbox') {
            obj[lastKey] = element.checked;
        } else if (element.type === 'number') {
            const numValue = parseFloat(element.value);
            obj[lastKey] = isNaN(numValue) ? element.value : numValue;
        } else if (element.type === 'text' && 
                  (element.name.endsWith('.stream_tags') || 
                   element.name.endsWith('.username_blocklist') ||
                   element.name.endsWith('.username_pool'))) {
            // 处理数组类型字段
            obj[lastKey] = element.value.split(',').map(item => item.trim()).filter(item => item);
        } else {
            obj[lastKey] = element.value;
        }
    });
    
    return config;
}

// 获取配置
async function getConfig() {
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
        const config = await window.connectionModule.apiRequest('/api/configs');
        currentConfig = config; // 保存当前配置
        configToForm(config); // 填充表单
        
        // 检查是否有未显示的配置项
        checkForMissingConfigItems(config);
    } catch (error) {
        console.error('获取配置失败:', error);
        window.uiModule.showToast(`获取配置失败: ${error.message}\n\n请检查后端日志以获取更多信息。`, 'error');
    }
}

// 检查是否有未在面板中显示的配置项
function checkForMissingConfigItems(config) {
    // 定义应该在面板中显示的配置项路径
    const expectedPaths = [
        'stream_metadata.stream_title',
        'stream_metadata.stream_category',
        'stream_metadata.stream_tags',
        'neuro_behavior.input_chat_sample_size',
        'neuro_behavior.post_speech_cooldown_sec',
        'neuro_behavior.initial_greeting',
        'audience_simulation.llm_provider',
        'audience_simulation.gemini_model',
        'audience_simulation.openai_model',
        'audience_simulation.llm_temperature',
        'audience_simulation.chat_generation_interval_sec',
        'audience_simulation.chats_per_batch',
        'audience_simulation.max_output_tokens',
        'audience_simulation.username_blocklist',
        'audience_simulation.username_pool',
        'agent.agent_provider',
        'agent.agent_model',
        'performance.neuro_input_queue_max_size',
        'performance.audience_chat_buffer_max_size',
        'performance.initial_chat_backlog_limit'
    ];
    
    // 收集实际配置中的所有路径
    const actualPaths = [];
    
    function collectPaths(obj, prefix = '') {
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const fullPath = prefix ? `${prefix}.${key}` : key;
                if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                    collectPaths(obj[key], fullPath);
                } else {
                    actualPaths.push(fullPath);
                }
            }
        }
    }
    
    collectPaths(config);
    
    // 检查是否有未显示的配置项
    const missingPaths = actualPaths.filter(path => 
        !expectedPaths.includes(path) && 
        !path.startsWith('api_keys') && 
        !path.startsWith('tts') && 
        !path.startsWith('server') &&
        path !== 'stream_metadata.streamer_nickname'
    );
    
    if (missingPaths.length > 0) {
        // 可以在这里添加更多用户提示逻辑
    }
}

// 重置配置表单
function resetConfigForm() {
    configToForm(currentConfig); // 使用保存的配置重置表单
}

// 保存配置
async function saveConfig(e) {
    e.preventDefault(); // 阻止表单默认提交行为
    
    try {
        const config = formToConfig(); // 从表单获取配置
        await window.connectionModule.apiRequest('/api/configs', {
            method: 'PATCH',
            body: JSON.stringify(config)
        });
        window.uiModule.showToast('配置保存成功', 'success');
        // 更新当前配置
        currentConfig = {...currentConfig, ...config};
    } catch (error) {
        console.error('保存配置失败:', error);
        window.uiModule.showToast(`保存配置失败: ${error.message}\n\n请检查后端日志以获取更多信息。`, 'error');
    }
}

// 导出函数供其他模块使用
window.configModule = {
    getConfig,
    resetConfigForm,
    saveConfig,
    configToForm,
    formToConfig
};