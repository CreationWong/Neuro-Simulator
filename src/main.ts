// src/main.ts

// 后端 API 的基础 URL
const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; // 确保与你的后端地址一致

// 获取 HTML 元素
const chatInput = document.getElementById('chat-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const chatMessages = document.getElementById('chat-messages') as HTMLDivElement;

// 辅助函数：将消息添加到聊天界面
function appendMessage(sender: 'user' | 'ai', text: string) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = text;
    chatMessages.appendChild(messageDiv);
    // 滚动到底部，显示最新消息
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 发送消息并处理 AI 回复的主函数
async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (!userMessage) return; // 如果输入为空，则不发送

    appendMessage('user', userMessage); // 显示用户消息
    chatInput.value = ''; // 清空输入框

    try {
        // 1. 调用后端 `/chat` 接口获取 AI 文本回复
        const chatResponse = await fetch(`${BACKEND_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: userMessage }),
        });

        if (!chatResponse.ok) {
            const errorText = await chatResponse.text();
            throw new Error(`Chat API error: ${chatResponse.status} ${chatResponse.statusText} - ${errorText}`);
        }

        const chatData = await chatResponse.json();
        const aiResponseText = chatData.ai_response_text;

        appendMessage('ai', aiResponseText); // 显示 AI 的文本回复

        // 2. 调用后端 `/synthesize_speech` 接口获取 AI 语音
        const ttsResponse = await fetch(`${BACKEND_BASE_URL}/synthesize_speech`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: aiResponseText,
                voice_name: "en-US-AshleyNeural", // 指定音色
                pitch: 1.25 // 指定音调
            }),
        });

        if (!ttsResponse.ok) {
            const errorText = await ttsResponse.text();
            throw new Error(`TTS API error: ${ttsResponse.status} ${ttsResponse.statusText} - ${errorText}`);
        }

        const ttsData = await ttsResponse.json();
        const audioBase64 = ttsData.audio_base64;

        // 3. 播放音频
        if (audioBase64) {
            const audio = new Audio('data:audio/mp3;base64,' + audioBase64);
            audio.play().catch(e => console.error("播放音频时出错:", e));
        }

    } catch (error) {
        console.error('与后端通信时发生错误:', error);
        appendMessage('ai', 'Someone tell Vedal there is a problem with my AI.');
    }
}

// 添加事件监听器
sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (event) => {
    // 允许用户按下 Enter 键发送消息
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// 初始消息 (可选)
appendMessage('ai', 'Hello eneryone, Neuro-sama here.');