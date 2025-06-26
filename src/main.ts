// src/main.ts

// === 类型声明,解决 'Timeout' 警告 ===
declare var setTimeout: typeof import('timers').setTimeout;
declare var clearTimeout: typeof import('timers').clearTimeout;

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; // 后端基础 URL
const MY_USERNAME = "Files_Transfer"; // 你的用户名

// 获取 HTML 元素
const chatInput = document.getElementById('chat-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const chatMessages = document.getElementById('chat-messages') as HTMLDivElement;
const neuroCaption = document.getElementById('neuro-caption') as HTMLDivElement; // 主播画面上的字幕
// const chatSidebar = document.getElementById('chat-sidebar') as HTMLDivElement; // 修复：chatSidebar 不再需要获取，因为它不再与按钮交互
// const sidebarToggle = document.getElementById('sidebar-toggle') as HTMLButtonElement; // 修复：侧边栏切换按钮不再需要获取

let captionTimeout: NodeJS.Timeout | undefined;

// === 音频播放队列和相关状态 ===
interface AudioSegment {
    text: string;
    audio: HTMLAudioElement;
}

const audioQueue: AudioSegment[] = [];
let isPlayingAudio = false; // 标记当前是否有音频正在播放
let allSegmentsReceived = false; // 标记所有段是否已从后端接收

// 辅助函数:生成随机颜色 (用于聊天用户名)
function getRandomChatColor(): string {
    const colors = [
        '#FF0000', '#00FF00', '#0000FF', '#00FFFF', '#FF00FF', // Primary/Secondary
        '#FF4500', '#ADFF2F', '#1E90FF', '#FFD700', '#8A2BE2', '#00CED1', // Common web colors
        '#FF69B4', '#DA70D6', '#BA55D3', '#87CEEB', '#32CD32', '#CD853F'  // More diverse
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

// 辅助函数:将消息添加到聊天界面
// 新增 username 参数和 isAI 参数
function appendChatMessage(username: string, text: string, isAI: boolean = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isAI ? 'ai-chat-message' : 'user-chat-message'}`; // 用于未来区分AI观众

    const usernameSpan = document.createElement('span');
    usernameSpan.className = 'username';
    usernameSpan.textContent = username + ': ';
    usernameSpan.style.color = getRandomChatColor(); // 为用户名设置随机颜色

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    textSpan.style.color = '#EFEFF1'; // 消息内容统一白色

    messageDiv.appendChild(usernameSpan);
    messageDiv.appendChild(textSpan);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight; // 滚动到底部
}


// 辅助函数:显示 Neuro 的字幕 (只负责显示,不设置消失计时器)
function showNeuroCaption(text: string) {
    // 每次显示新字幕,都清除之前的消失计时器
    if (captionTimeout) {
        clearTimeout(captionTimeout);
        captionTimeout = undefined;
    }
    neuroCaption.textContent = text;
    neuroCaption.classList.add('show'); // 立即显示
}

// 辅助函数:隐藏 Neuro 的字幕 (在所有音频播放结束后调用)
function hideNeuroCaptionAfterDelay() {
    // 确保在所有音频播放完毕后,且所有段都已接收,才启动这个计时器
    if (!isPlayingAudio && allSegmentsReceived) {
        if (captionTimeout) {
            clearTimeout(captionTimeout);
        }
        captionTimeout = setTimeout(() => {
            neuroCaption.classList.remove('show');
            neuroCaption.textContent = '';
            captionTimeout = undefined;
        }, 10000); // 播放结束后,字幕再持续 10 秒
    }
}

// === 处理音频队列播放 ===
function playNextAudioSegment() {
    if (audioQueue.length > 0 && !isPlayingAudio) {
        isPlayingAudio = true;
        const currentSegment = audioQueue.shift()!; // 取出队列中的第一个
        
        // 更新字幕为当前播放的音频段文本
        showNeuroCaption(currentSegment.text);

        currentSegment.audio.play().then(() => {
            // 音频播放成功开始
        }).catch(e => {
            console.error("播放音频时出错:", e);
            isPlayingAudio = false; // 播放失败,标记为不再播放
            playNextAudioSegment(); // 尝试播放下一个
        });

        currentSegment.audio.addEventListener('ended', () => {
            isPlayingAudio = false;
            playNextAudioSegment(); // 播放结束后,尝试播放下一个
        }, { once: true }); // 确保事件监听器只触发一次
    } else if (audioQueue.length === 0 && allSegmentsReceived) {
        // 队列已空,且所有段都已接收,此时可以启动最终的字幕消失计时器
        hideNeuroCaptionAfterDelay();
    }
}

// === 播放特定错误语音的函数 ===
async function playVedalErrorSpeech(errorMessage: string = "Someone tell Vedal there is a problem with my AI.") {
    console.error("Attempting to play error speech:", errorMessage);
    try {
        // 调用后端新的错误语音合成接口
        const response = await fetch(`${BACKEND_BASE_URL}/synthesize_error_speech`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: errorMessage, voice_name: "en-US-AshleyNeural", pitch: 1.25 }),
        });

        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`Failed to get error speech from backend: ${response.status} - ${errorBody}`);
            return;
        }

        const data = await response.json();
        if (data.audio_base64) {
            const errorAudio = new Audio('data:audio/mp3;base64,' + data.audio_base64);
            errorAudio.play().catch(e => console.error("Error playing fetched error audio:", e));
        } else {
            console.warn("No audio_base64 received for error speech.");
        }
    } catch (error) {
        console.error("Error making HTTP request for error speech:", error);
    }
}


// WebSocket 连接
let ws: WebSocket | null = null;

function connectWebSocket() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        console.log("WebSocket already connected or connecting.");
        return;
    }

    ws = new WebSocket(`${BACKEND_BASE_URL.replace('http', 'ws')}/ws/chat_stream`);

    ws.onopen = (event) => {
        console.log("WebSocket opened:", event);
        sendButton.disabled = false; // 连接成功后启用发送按钮
        chatInput.disabled = false;
        // 初始消息仅显示在聊天室
        appendChatMessage(MY_USERNAME, '欢迎来到 Neuro-Sama 的直播间!', false); 
        
        // 移除字幕区的初始连接提示,保持字幕区清爽
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log("Received WS message:", message);

        if (message.type === "segment") {
            const audio = new Audio('data:audio/mp3;base64,' + message.audio_base64);
            audioQueue.push({ text: message.text, audio: audio });
            if (!isPlayingAudio) {
                playNextAudioSegment();
            }
        } else if (message.type === "end") {
            allSegmentsReceived = true;
            if (audioQueue.length === 0 && !isPlayingAudio) {
                hideNeuroCaptionAfterDelay();
            }
            sendButton.disabled = false;
            chatInput.disabled = false;
        } else if (message.type === "error") {
            console.error("Backend error received:", message.message);
            showNeuroCaption("Someone tell Vedal there is a problem with my AI.");
            playVedalErrorSpeech(); // 调用函数播放错误语音
            
            allSegmentsReceived = true; 
            hideNeuroCaptionAfterDelay(); 

            sendButton.disabled = false;
            chatInput.disabled = false;
            audioQueue.length = 0; 
            isPlayingAudio = false;
        }
    };

    ws.onclose = (event) => {
        console.log("WebSocket closed:", event.code, event.reason);
        sendButton.disabled = true; 
        chatInput.disabled = true;
        isPlayingAudio = false;
        allSegmentsReceived = false;
        audioQueue.length = 0; 
        // 连接断开不显示在字幕区
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';
        setTimeout(connectWebSocket, 3000); // 3秒后尝试重连
    };

    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        // 连接失败不显示在字幕区
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';
        
        allSegmentsReceived = true;
        hideNeuroCaptionAfterDelay();
        sendButton.disabled = false;
        chatInput.disabled = false;
    };
}


// 发送消息的主函数 (现在通过 WebSocket 发送)
async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (!userMessage) return;

    appendChatMessage(MY_USERNAME, userMessage, false); // 显示用户消息在聊天侧边栏
    chatInput.value = ''; // 清空输入框

    if (ws && ws.readyState === WebSocket.OPEN) {
        try {
            // 重置状态
            audioQueue.length = 0;
            isPlayingAudio = false;
            allSegmentsReceived = false;
            // 清除任何旧的字幕计时器,立即隐藏旧字幕
            if (captionTimeout) {
                clearTimeout(captionTimeout);
                captionTimeout = undefined;
            }
            neuroCaption.classList.remove('show');
            neuroCaption.textContent = '';

            // 禁用输入，防止在AI处理时用户再次发送
            sendButton.disabled = true;
            chatInput.disabled = true;

            // 通过 WebSocket 发送消息给后端
            await ws.send(JSON.stringify({ message: userMessage })); 
            console.log("Message sent via WebSocket:", userMessage);

        } catch (error) {
            console.error('通过 WebSocket 发送消息时发生错误:', error);
            // 发送消息失败不显示在字幕区
            neuroCaption.classList.remove('show');
            neuroCaption.textContent = '';

            allSegmentsReceived = true; 
            hideNeuroCaptionAfterDelay();
            sendButton.disabled = false; // 确保发送失败后输入框可用
            chatInput.disabled = false;
        }
    } else {
        console.warn("WebSocket is not open. Trying to reconnect...");
        // 网络连接断开不显示在字幕区
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';

        connectWebSocket(); // 尝试重新连接
        allSegmentsReceived = true; 
        hideNeuroCaptionAfterDelay();
        sendButton.disabled = false; 
        chatInput.disabled = false;
    }
}

// 修复：移除 sidebarToggle 的事件监听器，因为它和折叠功能一并移除了
// sidebarToggle.addEventListener('click', () => { ... });


// 添加事件监听器
sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// === 页面加载完成时自动连接 WebSocket ===
document.addEventListener('DOMContentLoaded', () => {
    sendButton.disabled = true; // 默认禁用,直到WebSocket连接建立
    chatInput.disabled = true;
    connectWebSocket();
});

// 在 Electron 的渲染进程中,如果你需要访问 Electron API (如 ipcRenderer)
// 你可以通过 window.electronAPI (在 preload.ts 中暴露) 来访问。
// 例如:window.electronAPI.doSomething();