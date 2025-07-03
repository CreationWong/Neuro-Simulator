// src/core/appInitializer.ts
// (代码与上一次完全相同，无需修改)

import { WebSocketClient } from '../services/websocketClient';
import { ApiClient } from '../services/apiClient';
import { AudioPlayer } from '../services/audioPlayer';
import { VideoPlayer } from '../stream/videoPlayer';
import { NeuroAvatar } from '../stream/neuroAvatar';
import { ChatDisplay } from '../ui/chatDisplay';
import { showNeuroCaption, hideNeuroCaption } from '../ui/neuroCaption';
import { UserInput } from '../ui/userInput';
import { LayoutManager } from './layoutManager';
import { StreamTimer } from '../ui/streamTimer';
import { WebSocketMessage, ChatMessage, NeuroSpeechSegmentMessage, BackendErrorMessage, UserInputMessage } from '../types/common';

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; 
const MY_USERNAME = "Files_Transfer"; 

export class AppInitializer {
    private wsClient: WebSocketClient;
    private apiClient: ApiClient;
    private audioPlayer: AudioPlayer;
    private videoPlayer: VideoPlayer;
    private neuroAvatar: NeuroAvatar;
    private chatDisplay: ChatDisplay;
    private userInput: UserInput;   
    private layoutManager: LayoutManager;
    private streamTimer: StreamTimer;
    private isStarted: boolean = false;
    private currentPhase: string = 'offline';

    constructor() {
        this.layoutManager = new LayoutManager();
        this.streamTimer = new StreamTimer();
        this.apiClient = new ApiClient(BACKEND_BASE_URL);
        
        const universalMessageHandler = (message: WebSocketMessage) => this.handleWebSocketMessage(message);

        // --- 核心修改：只初始化一个客户端 ---
        this.wsClient = new WebSocketClient({
            url: BACKEND_BASE_URL.replace('http', 'ws') + '/ws/stream', // <-- 连接到新的统一端点
            autoReconnect: true,
            onMessage: universalMessageHandler,
            onDisconnect: () => this.goOffline("与服务器的连接已断开。正在尝试重新连接..."),
        });
        // 移除 this.audienceWsClient 的初始化

        this.audioPlayer = new AudioPlayer();
        this.videoPlayer = new VideoPlayer();
        this.neuroAvatar = new NeuroAvatar();
        this.chatDisplay = new ChatDisplay();
        this.userInput = new UserInput();
        this.userInput.onSendMessage((messageText: string) => this.sendUserMessage(messageText));
    }

    public start(): void {
        if (this.isStarted) return;
        this.isStarted = true;
        this.layoutManager.start();
        this.goOffline("正在连接到服务器...");
        this.wsClient.connect(); // <-- 只连接一次
        // 移除 this.audienceWsClient.connect();
    }

    private goOffline(systemMessage: string): void {
        this.currentPhase = 'offline';
        this.hideStreamContent();
        this.audioPlayer.stopAllAudio();
        this.videoPlayer.hideVideo();
        this.neuroAvatar.setStage('hidden', true);
        hideNeuroCaption();
        this.streamTimer.stop();
        this.userInput.setInputDisabled(true);
        this.chatDisplay.appendChatMessage({
            type: "chat_message", username: "System", text: systemMessage, is_user_message: false
        });
    }

    private handleWebSocketMessage(message: WebSocketMessage): void {
        if (this.currentPhase === 'offline' && ['play_welcome_video', 'start_avatar_intro', 'enter_live_phase'].includes(message.type)) {
            this.showStreamContent();
            this.chatDisplay.clearChat();
            this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: "已连接到服务器！", is_user_message: false });
        }
        if (message.elapsed_time_sec !== undefined) {
            this.streamTimer.start(message.elapsed_time_sec);
        }
        switch (message.type) {
            case 'play_welcome_video':
                this.currentPhase = 'initializing';
                this.videoPlayer.showAndPlayVideo(message.progress);
                this.userInput.setInputDisabled(true);
                break;
            case 'start_avatar_intro':
                this.currentPhase = 'avatar_intro';
                this.neuroAvatar.startIntroAnimation(() => { this.videoPlayer.hideVideo(); });
                this.userInput.setInputDisabled(true);
                break;
            case 'enter_live_phase':
                this.currentPhase = 'live';
                this.videoPlayer.hideVideo();
                this.neuroAvatar.setStage('step2', true); 
                this.userInput.setInputDisabled((message as any).is_speaking ?? false);
                break;
            case 'neuro_is_speaking':
                if (this.currentPhase === 'live') {
                    this.userInput.setInputDisabled((message as any).speaking);
                }
                if (!(message as any).speaking) hideNeuroCaption();
                break;
            case 'neuro_speech_segment':
                if (message.is_end) {
                    this.audioPlayer.setAllSegmentsReceived(); 
                } else if (message.audio_base64 && message.text && typeof message.duration === 'number') { // <-- 检查 duration 类型
                    this.audioPlayer.addAudioSegment(message.text, message.audio_base64, message.duration); // <-- 传递 duration
                } else {
                    console.warn("Received neuro_speech_segment message with missing audio/text/duration:", message);
                }
                break;
            case 'neuro_error_signal': // <-- 新增的处理 case
                console.warn("Received neuro_error_signal from backend.");
                // 显示固定的错误字幕
                showNeuroCaption("Someone tell Vedal there is a problem with my AI.");
                // 播放预置的错误音效
                this.audioPlayer.playErrorSound();
                break;
            case 'chat_message':
                if (!(message.is_user_message && message.username === MY_USERNAME)) {
                    this.chatDisplay.appendChatMessage(message);
                }
                break;
            case 'error':
                this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: `后端错误: ${message.message}`, is_user_message: false });
                break;
        }
    }
    
    private sendUserMessage(messageText: string): void {
        const message = { type: "user_message", message: messageText, username: MY_USERNAME };
        this.wsClient.send(message); // <-- 确保使用单一客户端发送
        this.chatDisplay.appendChatMessage({ type: "chat_message", username: MY_USERNAME, text: messageText, is_user_message: true });
    }

    private showStreamContent(): void {
        const streamArea = document.getElementById('stream-display-area');
        if (streamArea) {
            streamArea.style.visibility = 'visible';
            streamArea.style.opacity = '1';
        }
    }

    private hideStreamContent(): void {
        const streamArea = document.getElementById('stream-display-area');
        if (streamArea) {
            streamArea.style.visibility = 'hidden';
            streamArea.style.opacity = '0';
        }
    }
}