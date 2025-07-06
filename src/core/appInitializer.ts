// src/core/appInitializer.ts

import { WebSocketClient } from '../services/websocketClient';
import { AudioPlayer } from '../services/audioPlayer';
import { VideoPlayer } from '../stream/videoPlayer';
import { NeuroAvatar } from '../stream/neuroAvatar';
import { ChatDisplay } from '../ui/chatDisplay';
import { showNeuroCaption, hideNeuroCaption } from '../ui/neuroCaption';
import { UserInput } from '../ui/userInput';
import { LayoutManager } from './layoutManager';
import { StreamTimer } from '../ui/streamTimer';
import { ChatSidebar } from '../ui/chatSidebar';
import { LiveIndicator } from '../ui/liveIndicator'; // 导入简化的 LiveIndicator
import { StreamInfoDisplay } from '../ui/streamInfoDisplay';
import { WakeLockManager } from '../utils/wakeLockManager'; // 导入 WakeLockManager
import { WebSocketMessage, ChatMessage, NeuroSpeechSegmentMessage, UserInputMessage, StreamMetadataMessage } from '../types/common';

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; 
const MY_USERNAME = "Files_Transfer"; 

export class AppInitializer {
    private wsClient: WebSocketClient;
    private audioPlayer: AudioPlayer;
    private videoPlayer: VideoPlayer;
    private neuroAvatar: NeuroAvatar;
    private chatDisplay: ChatDisplay;
    private userInput: UserInput;   
    private layoutManager: LayoutManager;
    private streamTimer: StreamTimer;
    private chatSidebar: ChatSidebar;
    private liveIndicator: LiveIndicator; // 新增 LiveIndicator 属性
    private streamInfoDisplay: StreamInfoDisplay;
    private wakeLockManager: WakeLockManager; // 新增 WakeLockManager 属性
    private isStarted: boolean = false;
    private currentPhase: string = 'offline';

    constructor() {
        this.layoutManager = new LayoutManager();
        this.streamTimer = new StreamTimer();
        
        const universalMessageHandler = (message: WebSocketMessage) => this.handleWebSocketMessage(message);

        this.wsClient = new WebSocketClient({
            url: BACKEND_BASE_URL.replace('http', 'ws') + '/ws/stream', 
            autoReconnect: true,
            onMessage: universalMessageHandler,
            // 当 WebSocket 断开时，调用 goOffline
            onDisconnect: () => this.goOffline(),
        });

        this.audioPlayer = new AudioPlayer();
        this.videoPlayer = new VideoPlayer();
        this.neuroAvatar = new NeuroAvatar();
        this.chatDisplay = new ChatDisplay();
        this.userInput = new UserInput();
        this.userInput.onSendMessage((messageText: string) => this.sendUserMessage(messageText));
        this.chatSidebar = new ChatSidebar();
        
        // 实例化新模块
        this.liveIndicator = new LiveIndicator();
        this.streamInfoDisplay = new StreamInfoDisplay();
        this.wakeLockManager = new WakeLockManager();
    }

    public start(): void {
        if (this.isStarted) return;
        this.isStarted = true;
        this.layoutManager.start();
        // 初始化时进入离线状态，这将隐藏 LIVE 指示器
        this.goOffline(); 
        this.wsClient.connect(); 
    }

    /**
     * 将应用设置为离线状态。
     * 这会隐藏所有直播内容、停止计时器、禁用输入，并隐藏 LIVE 指示器。
     */
    private goOffline(): void {
        this.currentPhase = 'offline';
        this.hideStreamContent();
        this.audioPlayer.stopAllAudio();
        this.videoPlayer.hideVideo();
        this.neuroAvatar.setStage('hidden', true);
        hideNeuroCaption();
        this.streamTimer.stop();
        this.userInput.setInputDisabled(true);

        // 使用 LiveIndicator 和 WakeLockManager
        this.liveIndicator.hide();
        this.wakeLockManager.releaseWakeLock();
    }

    /**
     * 处理从后端收到的所有 WebSocket 消息。
     */
    private handleWebSocketMessage(message: WebSocketMessage): void {
        // 当收到第一条有效的流消息时，认为连接成功
        if (this.currentPhase === 'offline' && ['play_welcome_video', 'start_avatar_intro', 'enter_live_phase'].includes(message.type)) {
            this.showStreamContent();
            this.chatDisplay.clearChat();
            
            // 显示 LIVE 指示器并请求屏幕唤醒锁
            this.liveIndicator.show();
            this.wakeLockManager.requestWakeLock();
        }

        if (message.elapsed_time_sec !== undefined) {
            this.streamTimer.start(message.elapsed_time_sec);
        }

        switch (message.type) {
            case 'update_stream_metadata':
                this.streamInfoDisplay.update(message as StreamMetadataMessage);
                break;
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
                if (!(message as any).speaking) {
                    hideNeuroCaption();
                }
                break;

            case 'neuro_speech_segment':
                const segment = message as NeuroSpeechSegmentMessage;
                if (segment.is_end) {
                    this.audioPlayer.setAllSegmentsReceived(); 
                } else if (segment.audio_base64 && segment.text && typeof segment.duration === 'number') { 
                    this.audioPlayer.addAudioSegment(segment.text, segment.audio_base64, segment.duration);
                } else {
                    console.warn("Received neuro_speech_segment message with missing audio/text/duration:", segment);
                }
                break;

            case 'neuro_error_signal': 
                console.warn("Received neuro_error_signal from backend.");
                showNeuroCaption("Someone tell Vedal there is a problem with my AI.");
                this.audioPlayer.playErrorSound();
                break;

            case 'chat_message':
                // 只有当侧边栏展开或消息是用户自己发送的时，才显示聊天
                if (!this.chatSidebar.getIsCollapsed() || (message as ChatMessage).is_user_message) {
                   this.chatDisplay.appendChatMessage(message as ChatMessage);
                }
                break;

            case 'error':
                this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: `后端错误: ${(message as any).message}`, is_user_message: false });
                break;
        }
    }
    
    /**
     * 发送用户输入的消息到后端，并立即在本地显示。
     */
    private sendUserMessage(messageText: string): void {
        const message: UserInputMessage = { type: "user_message", message: messageText, username: MY_USERNAME };
        this.wsClient.send(message); 
        
        const localChatMessage: ChatMessage = { type: "chat_message", username: MY_USERNAME, text: messageText, is_user_message: true };
        this.chatDisplay.appendChatMessage(localChatMessage);
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