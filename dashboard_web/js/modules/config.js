// dashboard_web/js/modules/config.js

let jsonEditor = null; // To hold the JSON Editor instance

// Initializes the configuration editor
async function initializeConfigEditor() {
    if (!window.connectionModule.isConnected) {
        console.log("Cannot initialize config editor: Not connected.");
        return;
    }

    const container = document.getElementById('config-editor-container');
    if (!container) {
        console.error("Config editor container not found!");
        return;
    }
    container.innerHTML = '正在加载配置...'; // Loading indicator

    try {
        // Fetch schema and current values in parallel
        const [schema, values] = await Promise.all([
            window.connectionModule.sendAdminWsMessage('get_settings_schema'),
            window.connectionModule.sendAdminWsMessage('get_configs')
        ]);

        // Clear loading message
        container.innerHTML = '';

        // Destroy existing editor instance if it exists
        if (jsonEditor) {
            jsonEditor.destroy();
        }

        // Create the JSON Editor
        jsonEditor = new JSONEditor(container, {
            schema: schema,
            startval: values,
            theme: 'html',
            show_errors: 'interaction',
            disable_edit_json: true,
            disable_properties: true,
        });

        // Check for Agent type and update tab visibility
        updateAgentManagementVisibility(values);

    } catch (error) {
        console.error('初始化配置编辑器失败:', error);
        container.innerHTML = `<p style="color: red;">加载配置失败: ${error.message}</p>`;
        window.uiModule.showToast(`加载配置失败: ${error.message}`, 'error');
    }
}

// Saves the configuration
async function saveConfig() {
    if (!jsonEditor) {
        window.uiModule.showToast('编辑器未初始化', 'error');
        return;
    }

    if (!window.connectionModule.isConnected) {
        window.uiModule.showToast('未连接到后端', 'warning');
        return;
    }

    // Validate the editor's content
    const errors = jsonEditor.validate();
    if (errors.length) {
        console.error('配置验证失败:', errors);
        window.uiModule.showToast('配置中有错误，请修正后再保存', 'error');
        return;
    }

    try {
        const updatedValues = jsonEditor.getValue();
        await window.connectionModule.sendAdminWsMessage('update_configs', updatedValues);
        window.uiModule.showToast('配置保存成功！', 'success');

        // After saving, also update the agent management tab visibility
        updateAgentManagementVisibility(updatedValues);

    } catch (error) {
        console.error('保存配置失败:', error);
        window.uiModule.showToast(`保存配置失败: ${error.message}`, 'error');
    }
}

// Checks the agent_type from config and shows/hides the Agent Management tab
function updateAgentManagementVisibility(config) {
    const agentManagementTab = document.querySelector('[data-tab="agent-management"]');
    const chatbotManagementTab = document.querySelector('[data-tab="chatbot-management"]');

    if (chatbotManagementTab) {
        chatbotManagementTab.style.display = 'block'; // Always show Chatbot Management
    }

    if (agentManagementTab) {
        const isBuiltinAgent = !config.agent_type || config.agent_type === 'builtin';
        if (isBuiltinAgent) {
            agentManagementTab.style.display = 'block';
        } else {
            agentManagementTab.style.display = 'none';
            const activeTab = document.querySelector('.nav-tab.active');
            if (activeTab && activeTab.dataset.tab === 'agent-management') {
                window.uiModule.switchTab('control');
            }
        }
    }
}

// Export functions to be used by other modules
window.configModule = {
    initializeConfigEditor,
    saveConfig
};