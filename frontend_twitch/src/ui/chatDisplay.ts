// src/ui/chatDisplay.ts

import { ChatMessage } from '../types/common'; // 导入聊天消息的类型

// 获取 HTML 元素
const chatMessagesContainer = document.getElementById('chat-messages') as HTMLDivElement;

// 定义您的用户名，这应该与后端配置的 MY_USERNAME 一致，或者从某个配置中读取
const MY_USERNAME = "Files_Transfer"; 

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
        messageDiv.className = 'message';
        
        // 根据用户名和 is_user_message 添加不同的 CSS 类，以便样式区分
        if (message.username === MY_USERNAME && message.is_user_message) {
            messageDiv.classList.add('user-sent-message'); 
        } else if (message.username === "System") {
            messageDiv.classList.add('system-message');
        }
        else {
            messageDiv.classList.add('audience-ai-message');
        }

        const usernameSpan = document.createElement('span');
        usernameSpan.className = 'username';
        usernameSpan.textContent = message.username + ': ';
        // 你的用户名固定紫色，其他随机
        usernameSpan.style.color = (message.username === MY_USERNAME) ? '#9147FF' : this.getRandomChatColor(); 

        const textSpan = document.createElement('span');
        textSpan.textContent = message.text;
        textSpan.style.color = 'var(--twitch-text-color)'; // 使用 CSS 变量定义文本颜色

        messageDiv.appendChild(usernameSpan);
        messageDiv.appendChild(textSpan);

        chatMessagesContainer.appendChild(messageDiv);
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