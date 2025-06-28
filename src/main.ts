// src/main.ts

// 为 TypeScript 在浏览器环境中识别 Node.js 的计时器函数进行声明
declare var setTimeout: typeof import('timers').setTimeout;
declare var clearTimeout: typeof import('timers').clearTimeout;

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; // 后端基础 URL
const MY_USERNAME = "Files_Transfer"; // 您的用户名

// 获取 HTML 元素
const chatInput = document.getElementById('chat-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const chatMessages = document.getElementById('chat-messages') as HTMLDivElement;
const neuroCaption = document.getElementById('neuro-caption') as HTMLDivElement;
const resetButton = document.getElementById('reset-button') as HTMLAnchorElement;

// 视频元素
const startupVideoOverlay = document.getElementById('startup-video-overlay') as HTMLDivElement;
const startupVideo = document.getElementById('startup-video') as HTMLVideoElement;

// 音频播放队列和状态管理
interface AudioSegment {
    text: string;
    audio: HTMLAudioElement;
}

const audioQueue: AudioSegment[] = []; // 存储 Neuro TTS 音频片段的队列
let isPlayingAudio = false; // 标记是否有音频正在播放
let currentPlayingAudio: HTMLAudioElement | null = null; // 当前正在播放的音频实例
let allSegmentsReceived = false; // 标记 Neuro 的所有音频片段是否已从后端接收完毕

// --- 辅助函数 ---
function getRandomChatColor(): string {
    // 随机生成聊天用户名的颜色
    const colors = [
        '#FF0000', '#00FF00', '#0000FF', '#00FFFF', '#FF00FF',
        '#FF4500', '#ADFF2F', '#1E90FF', '#FFD700', '#8A2BE2', '#00CED1',
        '#FF69B4', '#DA70D6', '#BA55D3', '#87CEEB', '#32CD32', '#CD853F'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

function appendChatMessage(username: string, text: string) {
    // 将聊天消息添加到显示区域
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    // 根据用户名添加不同的 CSS 类，以便样式区分
    if (username === MY_USERNAME) {
        messageDiv.classList.add('user-sent-message'); 
    } else if (username === "System") {
        messageDiv.classList.add('system-message');
    }
    else {
        messageDiv.classList.add('audience-ai-message');
    }

    const usernameSpan = document.createElement('span');
    usernameSpan.className = 'username';
    usernameSpan.textContent = username + ': ';
    usernameSpan.style.color = (username === MY_USERNAME) ? '#9147FF' : getRandomChatColor(); // 你的用户名固定紫色，其他随机

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    textSpan.style.color = 'var(--twitch-text-color)'; // 使用 CSS 变量定义文本颜色

    messageDiv.appendChild(usernameSpan);
    messageDiv.appendChild(textSpan);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight; // 滚动到最新消息
}

function showNeuroCaption(text: string) {
    // 显示 Neuro 的实时字幕
    neuroCaption.textContent = text;
    neuroCaption.classList.add('show'); // 添加 CSS 类来显示字幕
}

function playNextAudioSegment() {
    // 播放队列中的下一个音频片段
    if (audioQueue.length > 0 && !isPlayingAudio) {
        isPlayingAudio = true;
        const currentSegment = audioQueue.shift()!; // 获取并移除队列头部的片段
        currentPlayingAudio = currentSegment.audio; // 存储当前正在播放的音频实例
        
        showNeuroCaption(currentSegment.text); // 显示当前片段的字幕

        currentPlayingAudio.play().then(() => {
            // 音频播放成功启动
        }).catch(e => {
            console.error("播放音频时出错:", e);
            isPlayingAudio = false;
            currentPlayingAudio = null;
            playNextAudioSegment(); // 尝试播放下一个片段
        });

        currentPlayingAudio.addEventListener('ended', () => {
            isPlayingAudio = false;
            currentPlayingAudio = null;
            playNextAudioSegment(); // 当前片段播放完毕，播放队列中的下一个
        }, { once: true }); // 事件监听器只触发一次
    } else if (audioQueue.length === 0 && allSegmentsReceived) {
        // 如果队列为空且所有片段都已接收，则表示 Neuro 的一次完整响应已完成
        console.log("Neuro 的所有音频片段已播放并接收完毕。正在向后端发送信号。");
        if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
            neuroWs.send(JSON.stringify({ type: "tts_finished" })); // 通知后端 TTS 已完成
        }
        neuroCaption.classList.remove('show'); // 隐藏字幕
        neuroCaption.textContent = ''; // 清空字幕内容
    }
}

// 立即停止所有 Neuro TTS 音频播放的函数
function stopNeuroAudio() {
    if (currentPlayingAudio) {
        currentPlayingAudio.pause(); // 暂停当前播放的音频
        currentPlayingAudio.currentTime = 0; // 重置播放位置
        currentPlayingAudio = null;
    }
    audioQueue.length = 0; // 清空音频队列
    isPlayingAudio = false;
    allSegmentsReceived = false;
    neuroCaption.classList.remove('show'); // 隐藏字幕
    neuroCaption.textContent = ''; // 清空字幕内容
    console.log("Neuro 音频播放已停止，队列已清空。");
}


async function playVedalErrorSpeech(errorMessage: string = "有人告诉 Vedal 我的 AI 出了问题。") {
    // 播放 Vedal 错误语音提示
    console.error("尝试播放错误语音:", errorMessage);
    try {
        const response = await fetch(`${BACKEND_BASE_URL}/synthesize_error_speech`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: errorMessage, voice_name: "en-US-AshleyNeural", pitch: 1.25 }),
        });

        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`无法从后端获取错误语音: ${response.status} - ${errorBody}`);
            return;
        }

        const data = await response.json();
        if (data.audio_base64) {
            const errorAudio = new Audio('data:audio/mp3;base64,' + data.audio_base64);
            errorAudio.play().catch(e => console.error("播放获取到的错误音频时出错:", e));
        } else {
            console.warn("未收到错误语音的 audio_base64。");
        }
    } catch (error) {
        console.error("请求错误语音 HTTP 时出错:", error);
    }
}

// --- WebSocket 连接管理 ---
let neuroWs: WebSocket | null = null; // Neuro TTS 和用户消息 WebSocket
let audienceWs: WebSocket | null = null; // 观众聊天显示 WebSocket

function connectNeuroWebSocket() {
    // 连接 Neuro WebSocket
    if (neuroWs && (neuroWs.readyState === WebSocket.OPEN || neuroWs.readyState === WebSocket.CONNECTING)) {
        console.log("Neuro WebSocket 已连接或正在连接。");
        return;
    }

    neuroWs = new WebSocket(`${BACKEND_BASE_URL.replace('http', 'ws')}/ws/chat_stream`);

    neuroWs.onopen = (event) => {
        console.log("Neuro WebSocket 已打开:", event);
        // 按钮启用会在 Neuro 首次发言完成后触发，保持初始禁用状态。
    };

    neuroWs.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log("收到 Neuro WS 消息:", message);

        if (message.type === "segment") {
            // 接收到音频片段
            const audio = new Audio('data:audio/mp3;base64,' + message.audio_base64);
            audioQueue.push({ text: message.text, audio: audio });
            if (!isPlayingAudio) {
                playNextAudioSegment(); // 如果没有正在播放，立即开始播放
            }
        } else if (message.type === "end") {
            // 收到所有音频片段的结束信号
            allSegmentsReceived = true;
            if (audioQueue.length === 0 && !isPlayingAudio) {
                console.log("Neuro 的响应已结束 (所有片段已接收并播放)。正在向后端发送信号。");
                if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
                    neuroWs.send(JSON.stringify({ type: "tts_finished" })); // 通知后端 TTS 已完成
                }
                neuroCaption.classList.remove('show'); // 隐藏字幕
                neuroCaption.textContent = '';
            } else {
                console.log("Neuro 的响应片段已接收，等待音频播放完成...");
            }
            sendButton.disabled = false; // Neuro 讲话结束后启用用户输入按钮
            chatInput.disabled = false;
        } else if (message.type === "error") {
            // 收到后端错误
            console.error("收到 Neuro 后端错误:", message.message);
            showNeuroCaption("有人告诉 Vedal 我的 AI 出了问题。");
            playVedalErrorSpeech();
            
            allSegmentsReceived = true;
            sendButton.disabled = false;
            chatInput.disabled = false;
            stopNeuroAudio(); // 立即停止所有音频播放和清空队列
            if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
                neuroWs.send(JSON.stringify({ type: "tts_finished" })); // 通知后端 TTS 状态
            }
        }
    };

    neuroWs.onclose = (event) => {
        console.log("Neuro WebSocket 已关闭:", event.code, event.reason);
        sendButton.disabled = true;
        chatInput.disabled = true;
        stopNeuroAudio(); // 在连接关闭时停止音频和清除状态
    };

    neuroWs.onerror = (error) => {
        console.error("Neuro WebSocket 错误:", error);
        stopNeuroAudio(); // 在连接错误时停止音频和清除状态
        sendButton.disabled = false;
        chatInput.disabled = false;
        if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
            neuroWs.send(JSON.stringify({ type: "tts_finished" }));
        }
    };
}

function connectAudienceWebSocket() {
    // 连接观众聊天显示 WebSocket
    if (audienceWs && (audienceWs.readyState === WebSocket.OPEN || audienceWs.readyState === WebSocket.CONNECTING)) {
        console.log("Audience WebSocket 已连接或正在连接。");
        return;
    }

    audienceWs = new WebSocket(`${BACKEND_BASE_URL.replace('http', 'ws')}/ws/audience_chat_display`);

    audienceWs.onopen = (event) => {
        console.log("Audience WebSocket 已打开:", event);
    };

    audienceWs.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "audience_chat") {
            appendChatMessage(message.username, message.text); // 显示观众聊天
        }
    };

    audienceWs.onclose = (event) => {
        console.log("Audience WebSocket 已关闭:", event.code, event.reason);
    };

    audienceWs.onerror = (error) => {
        console.error("Audience WebSocket 错误:", error);
    };
}


// 发送消息函数 (处理用户输入)
async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (!userMessage) return; // 如果消息为空，则不发送

    if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
        try {
            sendButton.disabled = true; // 暂时禁用输入，等待 Neuro 响应
            chatInput.disabled = true;

            // 通过 Neuro WebSocket 发送用户消息
            await neuroWs.send(JSON.stringify({ type: "user_message", message: userMessage, username: MY_USERNAME }));
            console.log(`用户消息 '${userMessage}' 已通过 Neuro WebSocket 发送。`);

        }
        catch (error) {
            console.error('发送消息到 Neuro WebSocket 时出错:', error);
            showNeuroCaption("发送消息时出了点问题。");
            playVedalErrorSpeech();
            sendButton.disabled = false; // 重新启用输入
            chatInput.disabled = false;
        }
    } else {
        console.warn("Neuro WebSocket 未打开。尝试重新连接...");
        showNeuroCaption("连接已断开。正在重试...");
        playVedalErrorSpeech("与 Neuro-Sama 后端的连接已断开。正在重试。");
        sendButton.disabled = false;
        chatInput.disabled = false;
    }
    chatInput.value = ''; // 清空输入框
}

// 重置按钮事件监听器
resetButton.addEventListener('click', async (event) => {
    event.preventDefault(); // 阻止默认的链接行为

    console.log("重置按钮被点击。尝试重置 Neuro 的记忆并清除聊天历史。");
    
    // 重置期间禁用输入
    sendButton.disabled = true;
    chatInput.disabled = true;
    
    // 清空前端可视组件并停止音频
    chatMessages.innerHTML = ''; // 清空聊天历史显示
    stopNeuroAudio(); // 立即停止所有正在播放的音频并清空队列
    
    // 关闭现有 WebSocket 连接
    if (neuroWs) {
        neuroWs.close(); // 这将触发 onclose 处理函数
        neuroWs = null;
    }
    if (audienceWs) {
        audienceWs.close(); // 这将触发 onclose 处理函数
        audienceWs = null;
    }
    
    try {
        // 向后端发送重置请求
        const response = await fetch(`${BACKEND_BASE_URL}/reset_agent_messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`重置 API 错误: ${response.status} ${response.statusText} - ${errorText}`);
        }

        console.log("Neuro Agent 消息已在后端成功重置。");
        appendChatMessage("System", '聊天历史和 AI 记忆已重置。正在启动新的直播...');
        
        // --- 重新启动整个主流程 ---
        await startMainProcess(); // 处理显示视频、等待、连接 WebSocket 并发送启动信号。

    } catch (error) {
        console.error('重置对话时出错:', error);
        showNeuroCaption("有人告诉 Vedal 我的 AI 出了问题。");
        playVedalErrorSpeech();
        
        sendButton.disabled = false; // 如果重置本身失败，重新启用按钮，以便用户可以重试
        chatInput.disabled = false;
    }
});


// --- 核心主流程启动函数 ---
const VIDEO_DURATION_MS = 10000; // 视频持续时间：10 秒

async function startMainProcess() {
    console.log("启动主流程: 显示视频，等待 10 秒，然后连接 WebSocket。");

    // 1. 重置前端 UI 状态以开始新的会话
    // 关键：立即启用聊天输入框和发送按钮！
    sendButton.disabled = false; 
    chatInput.disabled = false;

    chatMessages.innerHTML = ''; // 清空聊天历史显示
    stopNeuroAudio(); // 确保所有音频已停止且状态干净
    
    // 2. 显示并尝试播放视频
    if (startupVideo) {
        startupVideoOverlay.classList.remove('hidden'); // 确保视频叠加层可见
        startupVideo.currentTime = 0; // 将视频重置到开始
        startupVideo.play().catch(e => {
            console.warn("启动视频自动播放被阻止或失败。将按 10 秒延迟继续。错误:", e);
            // 仅记录错误；10 秒超时将处理流程的推进。
        });
    } else {
        console.warn("未找到启动视频元素。跳过视频阶段。");
    }

    // 3. 立即连接观众聊天 WebSocket。
    // 这样观众聊天就可以在视频播放期间显示。
    connectAudienceWebSocket();
    console.log("观众 WebSocket 连接已启动 (用于早期聊天显示)。");

    // 4. 等待固定的 10 秒时间
    await new Promise(resolve => setTimeout(resolve, VIDEO_DURATION_MS));
    console.log("10 秒启动视频阶段完成。");

    // 5. 隐藏视频叠加层并连接 Neuro WebSocket
    if (startupVideoOverlay) {
        startupVideoOverlay.classList.add('hidden');
    }
    
    // 连接 Neuro WebSocket (观众 WebSocket 已在之前启动)
    connectNeuroWebSocket();

    // 6. 在 Neuro WebSocket 打开后，向后端发送启动 Neuro 初始响应的信号
    const sendStartSignal = async () => {
        if (!neuroWs) {
            console.error("Neuro WebSocket 为空，无法发送启动信号。");
            return;
        }
        if (neuroWs.readyState === WebSocket.OPEN) {
            neuroWs.send(JSON.stringify({ type: "start_live_stream" }));
            console.log("已向后端发送 'start_live_stream' 信号。");
        } else {
            // 如果 WebSocket 尚未打开，则等待它打开
            await new Promise<void>((resolve) => {
                const onOpenHandler = () => {
                    if (neuroWs) {
                        neuroWs.removeEventListener('open', onOpenHandler);
                    }
                    resolve();
                };
                if (neuroWs) {
                    neuroWs.addEventListener('open', onOpenHandler, { once: true });
                } else {
                    console.error("在添加 'open' 监听器以发送启动信号之前，Neuro WS 为空。");
                    resolve();
                }
            });
            if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
                neuroWs.send(JSON.stringify({ type: "start_live_stream" }));
                console.log("在 WebSocket 连接建立后，发送 'start_live_stream' 信号。");
            } else {
                console.error("Neuro WebSocket 未能及时打开以发送启动信号。");
            }
        }
    };
    await sendStartSignal(); // 等待信号发送完成
}


// 添加事件监听器
sendButton.addEventListener('click', sendMessage); // 发送按钮点击
chatInput.addEventListener('keypress', (event) => {
    // 输入框回车键按下
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// 页面加载完成后，启动主流程
document.addEventListener('DOMContentLoaded', startMainProcess);
