// src/core/appInitializer.ts
import { WebSocketClient } from '../services/websocketClient';
import { ApiClient } from '../services/apiClient';
import { AudioPlayer } from '../services/audioPlayer';
import { VideoPlayer } from '../stream/videoPlayer';
import { NeuroAvatar } from '../stream/neuroAvatar';
import { ChatDisplay } from '../ui/chatDisplay';
import { hideNeuroCaption } from '../ui/neuroCaption';
import { UserInput } from '../ui/userInput';
import { Header } from '../ui/header';
import { WebSocketMessage, ChatMessage, NeuroSpeechSegmentMessage, BackendErrorMessage, UserInputMessage } from '../types/common';
import { LayoutManager } from './layoutManager'; // <-- 引入 LayoutManager

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; 
const MY_USERNAME = "Files_Transfer"; 

export class AppInitializer {
    private neuroWsClient: WebSocketClient;
    private audienceWsClient: WebSocketClient;
    private apiClient: ApiClient;
    private audioPlayer: AudioPlayer;
    private videoPlayer: VideoPlayer;
    private neuroAvatar: NeuroAvatar;
    private chatDisplay: ChatDisplay;
    private userInput: UserInput;
    private header: Header;
    private layoutManager: LayoutManager; // <-- 添加 LayoutManager 实例
    private isStarted: boolean = false;
    private currentPhase: string = 'offline';

    constructor() {
        this.layoutManager = new LayoutManager(); // <-- 实例化 LayoutManager
        this.apiClient = new ApiClient(BACKEND_BASE_URL);

        const universalMessageHandler = (message: WebSocketMessage) => this.handleWebSocketMessage(message);

        this.neuroWsClient = new WebSocketClient({ url: BACKEND_BASE_URL.replace('http', 'ws') + '/ws/neuro_stream', autoReconnect: true, onMessage: universalMessageHandler });
        this.audienceWsClient = new WebSocketClient({ url: BACKEND_BASE_URL.replace('http', 'ws') + '/ws/audience_chat_display', autoReconnect: true, onMessage: universalMessageHandler });

        this.audioPlayer = new AudioPlayer();
        this.videoPlayer = new VideoPlayer();
        this.neuroAvatar = new NeuroAvatar();
        this.chatDisplay = new ChatDisplay();
        this.userInput = new UserInput();
        this.header = new Header();
        this.userInput.onSendMessage((messageText: string) => this.sendUserMessage(messageText));
        this.header.onReset(() => this.resetApplication());
        console.log("AppInitializer constructor finished.");
    }

    public start(): void {
        if (this.isStarted) {
            console.warn("AppInitializer already started. Ignoring.");
            return;
        }
        this.isStarted = true;
        console.log("Starting application...");
        
        this.layoutManager.start(); // <-- 启动布局管理器
        this.hideStreamContent(); // <-- 初始状态下隐藏内容区
        
        this.neuroWsClient.connect();
        this.audienceWsClient.connect();
        this.userInput.setInputDisabled(true); 
    }

    private handleWebSocketMessage(message: WebSocketMessage): void {
        // 当收到第一个有效的直播流程消息时，显示内容区域
        if (this.currentPhase === 'offline' && ['play_welcome_video', 'start_avatar_intro', 'enter_live_phase'].includes(message.type)) {
            this.showStreamContent();
        }

        console.log("Received event:", message);
        // ... (switch case for message types remains the same) ...
        switch (message.type) {
            case 'play_welcome_video':
                if (this.currentPhase === 'offline') {
                    this.currentPhase = 'initializing';
                    this.videoPlayer.showAndPlayVideo(message.progress);
                }
                break;
            case 'start_avatar_intro':
                if (this.currentPhase === 'initializing' || this.currentPhase === 'offline') { // 允许从 offline 直接跳到 intro
                    this.currentPhase = 'avatar_intro';
                    this.neuroAvatar.startIntroAnimation(() => {
                        this.videoPlayer.hideVideo();
                    });
                }
                break;
            case 'enter_live_phase':
                 if (this.currentPhase !== 'live') {
                    this.currentPhase = 'live';
                    this.videoPlayer.hideVideo();
                    this.neuroAvatar.setStage('step2', true); 
                    this.userInput.setInputDisabled((message as any).speaking ?? false);
                }
                break;
            case 'neuro_is_speaking':
                if (this.currentPhase === 'live') {
                    this.userInput.setInputDisabled((message as any).speaking);
                    if (!(message as any).speaking) hideNeuroCaption();
                }
                break;
            case 'neuro_speech_segment':
                this.handleNeuroSpeechSegment(message as NeuroSpeechSegmentMessage);
                break;
            case 'chat_message':
                this.handleChatMessage(message as ChatMessage);
                break;
            case 'error':
                this.handleBackendError(message as BackendErrorMessage);
                break;
        }
    }

    // ... (other handler methods like handleNeuroSpeechSegment remain the same) ...
    private handleNeuroSpeechSegment(message: NeuroSpeechSegmentMessage): void {
        if (message.is_end) { this.audioPlayer.setAllSegmentsReceived(); } 
        else if (message.audio_base64 && message.text) { this.audioPlayer.addAudioSegment(message.text, message.audio_base64); }
    }
    private handleChatMessage(message: ChatMessage): void {
        if (message.is_user_message && message.username === MY_USERNAME) { return; }
        this.chatDisplay.appendChatMessage(message);
    }
    private async handleBackendError(message: BackendErrorMessage): Promise<void> {
        console.error("Received backend error:", message.code, message.message);
        this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: `后端错误: ${message.message}`, is_user_message: false });
    }
    private sendUserMessage(messageText: string): void {
        const message: UserInputMessage = { type: "user_message", message: messageText, username: MY_USERNAME };
        this.neuroWsClient.send(message);
        this.chatDisplay.appendChatMessage({ type: "chat_message", username: MY_USERNAME, text: messageText, is_user_message: true });
    }
    
    private async resetApplication(): Promise<void> {
        console.log("Initiating application reset...");
        this.userInput.setInputDisabled(true);
        this.chatDisplay.clearChat();
        this.audioPlayer.stopAllAudio();
        hideNeuroCaption();
        this.videoPlayer.hideVideo();
        this.neuroAvatar.setStage('hidden', true);

        this.hideStreamContent(); // <-- 在重置时隐藏内容区

        this.currentPhase = 'offline';
        this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: "正在重置，请稍候...", is_user_message: false });
        try {
            const response = await this.apiClient.resetNeuroAgent() as unknown as { message: string };
            this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: response.message, is_user_message: false });
        } catch (error) {
            this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: "重置失败！", is_user_message: false });
            this.userInput.setInputDisabled(false); 
        }
    }

    // --- 新增: 控制内容区可见性的方法 ---
    private showStreamContent(): void {
        const streamArea = document.getElementById('stream-display-area');
        if (streamArea) {
            streamArea.style.visibility = 'visible';
            streamArea.style.opacity = '1';
            console.log("Stream content area is now visible.");
        }
    }

    private hideStreamContent(): void {
        const streamArea = document.getElementById('stream-display-area');
        if (streamArea) {
            streamArea.style.visibility = 'hidden';
            streamArea.style.opacity = '0';
            console.log("Stream content area is now hidden.");
        }
    }
}