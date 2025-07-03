// src/core/appInitializer.ts

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
import { ChatSidebar } from '../ui/chatSidebar'; // <-- 新增导入
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
    private chatSidebar: ChatSidebar; // <-- 新增属性
    private isStarted: boolean = false;
    private currentPhase: string = 'offline';

    constructor() {
        this.layoutManager = new LayoutManager();
        this.streamTimer = new StreamTimer();
        this.apiClient = new ApiClient(BACKEND_BASE_URL);
        
        const universalMessageHandler = (message: WebSocketMessage) => this.handleWebSocketMessage(message);

        this.wsClient = new WebSocketClient({
            url: BACKEND_BASE_URL.replace('http', 'ws') + '/ws/stream', 
            autoReconnect: true,
            onMessage: universalMessageHandler,
            onDisconnect: () => this.goOffline("与服务器的连接已断开。正在尝试重新连接..."),
        });

        this.audioPlayer = new AudioPlayer();
        this.videoPlayer = new VideoPlayer();
        this.neuroAvatar = new NeuroAvatar();
        this.chatDisplay = new ChatDisplay();
        this.userInput = new UserInput();
        this.userInput.onSendMessage((messageText: string) => this.sendUserMessage(messageText));
        this.chatSidebar = new ChatSidebar(); // <-- 实例化 ChatSidebar
    }

    public start(): void {
        if (this.isStarted) return;
        this.isStarted = true;
        this.layoutManager.start();
        this.goOffline("正在连接到服务器...");
        this.wsClient.connect(); 
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
        // 确保离线时侧边栏是展开的，以便用户能看到连接消息
        this.chatSidebar.setCollapsed(false); 

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
                this.chatSidebar.setCollapsed(false); // 确保视频播放时侧边栏展开
                break;
            case 'start_avatar_intro':
                this.currentPhase = 'avatar_intro';
                this.neuroAvatar.startIntroAnimation(() => { this.videoPlayer.hideVideo(); });
                this.userInput.setInputDisabled(true);
                this.chatSidebar.setCollapsed(false); // 确保头像入场时侧边栏展开
                break;
            case 'enter_live_phase':
                this.currentPhase = 'live';
                this.videoPlayer.hideVideo();
                this.neuroAvatar.setStage('step2', true); 
                this.userInput.setInputDisabled((message as any).is_speaking ?? false);
                this.chatSidebar.setCollapsed(false); // 确保进入直播阶段侧边栏展开
                break;
            case 'neuro_is_speaking':
                if (this.currentPhase === 'live') {
                    this.userInput.setInputDisabled((message as any).speaking);
                }
                if (!(message as any).speaking) hideNeuroCaption();
                break;
            case 'neuro_speech_segment':
                if (message.is_end) this.audioPlayer.setAllSegmentsReceived(); 
                else if (message.audio_base64 && message.text && typeof message.duration === 'number') { 
                    this.audioPlayer.addAudioSegment(message.text, message.audio_base64, message.duration);
                } else {
                    console.warn("Received neuro_speech_segment message with missing audio/text/duration:", message);
                }
                break;
            case 'neuro_error_signal': 
                console.warn("Received neuro_error_signal from backend.");
                showNeuroCaption("Someone tell Vedal there is a problem with my AI.");
                this.audioPlayer.playErrorSound();
                break;
            case 'chat_message':
                // 当侧边栏收缩时，不显示 AI 生成的观众聊天，只显示用户自己的消息
                // 这能模拟聊天被“隐藏”的感觉
                if (!this.chatSidebar.getIsCollapsed() || message.is_user_message) {
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
        this.wsClient.send(message); 
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