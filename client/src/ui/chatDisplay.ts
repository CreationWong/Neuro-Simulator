// src/ui/chatDisplay.ts

import { ChatMessage } from '../types/common'; // 导入聊天消息的类型

// 获取 HTML 元素
const chatMessagesContainer = document.getElementById('chat-messages') as HTMLDivElement;
const twitchChatOverlay = document.getElementById('twitch-chat-overlay') as HTMLDivElement;

// 定义您的用户名，这应该与后端配置的 MY_USERNAME 一致，或者从某个配置中读取
const MY_USERNAME = "One_of_Swarm"; 

export class ChatDisplay {

    constructor() {
        if (!chatMessagesContainer) {
            console.error("ChatDisplay: Required chat messages container not found in DOM!");
        } else {
            console.log("ChatDisplay initialized.");
        }
    }

    /**
     * 将一条聊天消息添加到显示区域。
     * @param message 聊天消息对象。
     */
    public appendChatMessage(message: ChatMessage): void {
        if (!chatMessagesContainer) {
            console.error("ChatDisplay: Cannot append message, container not found.");
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-line__message'; // 使用 Twitch 风格的类名

        // 容器，用于消息高亮等
        const messageContainer = document.createElement('div');
        messageContainer.className = 'chat-line__message-container';

        // 根据消息来源添加特定类
        if (message.username === MY_USERNAME && message.is_user_message) {
            messageDiv.classList.add('user-sent-message'); 
        } else if (message.username === "System") {
            messageDiv.classList.add('system-message');
        } else {
            messageDiv.classList.add('audience-ai-message');
        }

        // 用户名容器
        const usernameContainer = document.createElement('span');
        usernameContainer.className = 'chat-line__username';
        usernameContainer.style.color = (message.username === MY_USERNAME) ? '#9147FF' : this.getRandomChatColor(); 

        const usernameSpan = document.createElement('span');
        usernameSpan.className = 'chat-author__display-name';
        usernameSpan.textContent = message.username;
        usernameContainer.appendChild(usernameSpan);

        // 冒号和消息文本
        const colonSpan = document.createElement('span');
        colonSpan.textContent = ': ';
        colonSpan.style.marginRight = '0.3rem';
        colonSpan.className = 'text-fragment'; // 添加与文本相同的类名

        const textSpan = document.createElement('span');
        textSpan.className = 'text-fragment';
        textSpan.textContent = message.text;

        messageContainer.appendChild(usernameContainer);
        messageContainer.appendChild(colonSpan);
        messageContainer.appendChild(textSpan);
        
        messageDiv.appendChild(messageContainer);

        // 添加到主聊天区域
        chatMessagesContainer.appendChild(messageDiv);
        
        // 同时添加到 Twitch 风格覆盖层（如果存在）
        if (twitchChatOverlay) {
            const overlayMessageDiv = messageDiv.cloneNode(true) as HTMLDivElement;
            twitchChatOverlay.appendChild(overlayMessageDiv);
            this.scrollToBottomOverlay(); // 滚动覆盖层到最新消息
        }
        
        this.scrollToBottom(); // 滚动到最新消息
    }

    /**
     * 清空所有显示的聊天消息。
     */
    public clearChat(): void {
        if (chatMessagesContainer) {
            chatMessagesContainer.innerHTML = '';
            console.log("Chat display cleared.");
        }
        
        // 同时清空 Twitch 风格覆盖层（如果存在）
        if (twitchChatOverlay) {
            twitchChatOverlay.innerHTML = '';
        }
    }

    /**
     * 滚动聊天显示区域到最底部。
     */
    private scrollToBottom(): void {
        if (chatMessagesContainer) {
            chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
        }
    }
    
    /**
     * 滚动 Twitch 风格覆盖层到最底部。
     */
    private scrollToBottomOverlay(): void {
        if (twitchChatOverlay) {
            twitchChatOverlay.scrollTop = twitchChatOverlay.scrollHeight;
        }
    }

    /**
     * 随机生成聊天用户名的颜色。
     * @returns CSS 颜色字符串。
     */
    private getRandomChatColor(): string {
        const colors = [
            '#FF0000', '#00FF00', '#0000FF', '#00FFFF', '#FF00FF',
            '#FF4500', '#ADFF2F', '#1E90FF', '#FFD700', '#8A2BE2', '#00CED1',
            '#FF69B4', '#DA70D6', '#BA55D3', '#87CEEB', '#32CD32', '#CD853F'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }
}