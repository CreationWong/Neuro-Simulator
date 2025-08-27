// dashboard_web/js/modules/tools.js

// --- DOM Elements ---
const reloadToolsBtn = document.getElementById('reloadToolsBtn');
const saveToolAllocationsBtn = document.getElementById('saveToolAllocationsBtn');
const allToolsContainer = document.getElementById('allToolsContainer');
const neuroAgentToolsContainer = document.getElementById('neuroAgentTools');
const memoryAgentToolsContainer = document.getElementById('memoryAgentTools');

let allToolsData = [];
let allocationsData = {};

// --- Initialization ---

function initToolsPage() {
    if (!window.connectionModule || !window.connectionModule.isConnected) {
        console.warn("Cannot initialize Tools page: WebSocket not connected.");
        return;
    }

    // Attach event listeners
    if (reloadToolsBtn) reloadToolsBtn.addEventListener('click', handleReloadTools);
    if (saveToolAllocationsBtn) saveToolAllocationsBtn.addEventListener('click', handleSaveAllocations);

    // Fetch initial data
    fetchAllToolsAndAllocations();
}

// --- Data Fetching ---

async function fetchAllToolsAndAllocations() {
    try {
        const [toolsResponse, allocationsResponse] = await Promise.all([
            window.connectionModule.sendAdminWsMessage('get_all_tools'),
            window.connectionModule.sendAdminWsMessage('get_agent_tool_allocations')
        ]);

        allToolsData = toolsResponse.tools || [];
        allocationsData = allocationsResponse.allocations || {};

        renderAllToolsList();
        renderAllocatedTools();

    } catch (error) {
        console.error("Failed to fetch tools data:", error);
        window.uiModule.showToast(`获取工具数据失败: ${error.message}`, 'error');
        if (allToolsContainer) allToolsContainer.innerHTML = `<p class="error">加载工具列表失败。</p>`;
    }
}

// --- Rendering ---

function renderAllToolsList() {
    if (!allToolsContainer) return;
    allToolsContainer.innerHTML = '';

    if (allToolsData.length === 0) {
        allToolsContainer.innerHTML = '<p>没有找到可用工具。</p>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'tools-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>工具名称</th>
                <th>描述</th>
                <th>Neuro Agent</th>
                <th>Memory Agent</th>
            </tr>
        </thead>
    `;

    const tbody = document.createElement('tbody');
    allToolsData.forEach(tool => {
        const tr = document.createElement('tr');
        tr.dataset.toolName = tool.name;

        const isNeuroEnabled = (allocationsData.neuro_agent || []).includes(tool.name);
        const isMemoryEnabled = (allocationsData.memory_agent || []).includes(tool.name);

        tr.innerHTML = `
            <td>${tool.name}</td>
            <td>${tool.description}</td>
            <td><input type="checkbox" class="allocation-checkbox" data-agent="neuro_agent" data-tool-name="${tool.name}" ${isNeuroEnabled ? 'checked' : ''}></td>
            <td><input type="checkbox" class="allocation-checkbox" data-agent="memory_agent" data-tool-name="${tool.name}" ${isMemoryEnabled ? 'checked' : ''}></td>
        `;
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    allToolsContainer.appendChild(table);
}

function renderAllocatedTools() {
    if (!neuroAgentToolsContainer || !memoryAgentToolsContainer) return;

    const neuroToolNames = new Set(allocationsData.neuro_agent || []);
    const memoryToolNames = new Set(allocationsData.memory_agent || []);

    const neuroTools = allToolsData.filter(tool => neuroToolNames.has(tool.name));
    const memoryTools = allToolsData.filter(tool => memoryToolNames.has(tool.name));

    renderToolListForAgent(neuroAgentToolsContainer, neuroTools);
    renderToolListForAgent(memoryAgentToolsContainer, memoryTools);
}

function renderToolListForAgent(container, tools) {
    container.innerHTML = '';
    if (tools.length === 0) {
        container.innerHTML = '<p>无可用工具。</p>';
        return;
    }
    const ul = document.createElement('ul');
    ul.className = 'allocated-tools-list';
    tools.forEach(tool => {
        const li = document.createElement('li');
        li.textContent = tool.name;
        ul.appendChild(li);
    });
    container.appendChild(ul);
}

// --- Event Handlers & Actions ---

async function handleReloadTools() {
    try {
        await window.connectionModule.sendAdminWsMessage('reload_tools');
        window.uiModule.showToast('工具已成功重载', 'success');
        // The backend will push an 'available_tools_updated' event, which will trigger a refresh.
    } catch (error) {
        console.error("Failed to reload tools:", error);
        window.uiModule.showToast(`重载工具失败: ${error.message}`, 'error');
    }
}

async function handleSaveAllocations() {
    const newAllocations = {
        neuro_agent: [],
        memory_agent: []
    };

    const checkboxes = document.querySelectorAll('#allToolsContainer .allocation-checkbox');
    checkboxes.forEach(cb => {
        if (cb.checked) {
            const agent = cb.dataset.agent;
            const toolName = cb.dataset.toolName;
            if (agent && toolName && newAllocations[agent]) {
                newAllocations[agent].push(toolName);
            }
        }
    });

    try {
        await window.connectionModule.sendAdminWsMessage('set_agent_tool_allocations', { allocations: newAllocations });
        window.uiModule.showToast('工具分配已保存', 'success');
        // The backend will push an 'agent_tool_allocations_updated' event, which will trigger a refresh.
    } catch (error) {
        console.error("Failed to save allocations:", error);
        window.uiModule.showToast(`保存分配失败: ${error.message}`, 'error');
    }
}

// --- Public API ---

window.toolsModule = {
    initToolsPage,
    // Functions to be called by WebSocket events
    handleAvailableToolsUpdate: (tools) => {
        allToolsData = tools || [];
        renderAllToolsList();
        renderAllocatedTools();
    },
    handleAllocationsUpdate: (allocations) => {
        allocationsData = allocations || {};
        renderAllToolsList(); // Re-render the main list to update checkboxes
        renderAllocatedTools();
    }
};