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
    private isStarted: boolean = false;
    private currentPhase: string = 'offline';

    constructor() {
        this.apiClient = new ApiClient(BACKEND_BASE_URL);

        const universalMessageHandler = (message: WebSocketMessage) => this.handleWebSocketMessage(message);

        this.neuroWsClient = new WebSocketClient({
            url: BACKEND_BASE_URL.replace('http', 'ws') + '/ws/neuro_stream',
            autoReconnect: true,
            onMessage: universalMessageHandler,
        });

        this.audienceWsClient = new WebSocketClient({
            url: BACKEND_BASE_URL.replace('http', 'ws') + '/ws/audience_chat_display',
            autoReconnect: true,
            onMessage: universalMessageHandler,
        });

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
        this.neuroWsClient.connect();
        this.audienceWsClient.connect();
        this.userInput.setInputDisabled(true); 
    }

    private handleWebSocketMessage(message: WebSocketMessage): void {
        console.log("Received event:", message);
        switch (message.type) {
            case 'play_welcome_video':
                if (this.currentPhase === 'offline') {
                    this.currentPhase = 'initializing';
                    this.videoPlayer.showAndPlayVideo(message.progress);
                }
                break;
            case 'start_avatar_intro':
                if (this.currentPhase === 'initializing') {
                    this.currentPhase = 'avatar_intro';
                    // 不再立即隐藏视频，而是将隐藏操作作为回调传递给动画函数
                    this.neuroAvatar.startIntroAnimation(() => {
                        this.videoPlayer.hideVideo(); // 在动画完成后隐藏视频
                    });
                }
                break;
            case 'enter_live_phase':
                if (this.currentPhase !== 'live') {
                    this.currentPhase = 'live';
                    this.videoPlayer.hideVideo(); // 确保视频被隐藏
                    this.neuroAvatar.setStage('step2', true); 
                    this.userInput.setInputDisabled((message as any).speaking); // 假设事件可能附带 speaking 状态
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
        this.currentPhase = 'offline';
        this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: "正在重置，请稍候...", is_user_message: false });
        try {
            // 注意：apiClient.resetNeuroAgent() 返回的是一个 Promise<string>，
            // 但后端返回的 JSON 是 {"message": "..."}，所以需要解构
            const response = await this.apiClient.resetNeuroAgent() as unknown as { message: string };
            this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: response.message, is_user_message: false });
        } catch (error) {
            this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: "重置失败！", is_user_message: false });
            this.userInput.setInputDisabled(false); 
        }
    }
}