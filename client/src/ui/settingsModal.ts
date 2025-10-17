import { getSettings, saveSettings } from '../services/settingsService';

// 定义设置的数据结构
export interface AppSettings {
    username: string;
    avatarDataUrl: string;
    backendUrl: string;
    reconnectAttempts: number;
}

// 定义回调函数的类型
type onSaveCallback = (newSettings: AppSettings) => void;

export class SettingsModal {
    // DOM Elements
    private modalContainer: HTMLDivElement;
    private overlay: HTMLDivElement;
    private closeButton: HTMLButtonElement;
    private saveButton: HTMLButtonElement;
    private usernameInput: HTMLInputElement;
    private backendUrlInput: HTMLInputElement;
    private avatarPreview: HTMLImageElement;
    private avatarUploadInput: HTMLInputElement;
    private avatarUploadButton: HTMLButtonElement;
    private reconnectAttemptsInput: HTMLInputElement;

    private onSave: onSaveCallback;

    constructor(saveCallback: onSaveCallback) {
        this.onSave = saveCallback;

        // 绑定 DOM 元素
        this.modalContainer = document.getElementById('settings-modal') as HTMLDivElement;
        this.overlay = document.getElementById('settings-modal-overlay') as HTMLDivElement;
        this.closeButton = document.getElementById('settings-close-button') as HTMLButtonElement;
        this.saveButton = document.getElementById('settings-save-button') as HTMLButtonElement;
        this.usernameInput = document.getElementById('username-setting-input') as HTMLInputElement;
        this.backendUrlInput = document.getElementById('backend-url-input') as HTMLInputElement;
        this.avatarPreview = document.getElementById('avatar-setting-preview') as HTMLImageElement;
        this.avatarUploadInput = document.getElementById('avatar-setting-upload') as HTMLInputElement;
        this.avatarUploadButton = document.getElementById('avatar-upload-button') as HTMLButtonElement;
        this.reconnectAttemptsInput = document.getElementById('reconnect-attempts-input') as HTMLInputElement;

        if (!this.modalContainer) throw new Error("Settings modal container not found!");

        this.setupEventListeners();
        console.log("SettingsModal initialized.");
    }

    private setupEventListeners(): void {
        this.closeButton.addEventListener('click', () => this.close());
        this.overlay.addEventListener('click', () => this.close());
        this.saveButton.addEventListener('click', () => this.handleSave());

        this.avatarUploadButton.addEventListener('click', () => this.avatarUploadInput.click());
        this.avatarUploadInput.addEventListener('change', (event) => this.handleAvatarUpload(event));
    }

    private handleAvatarUpload(event: Event): void {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                if (e.target?.result) {
                    this.avatarPreview.src = e.target.result as string;
                }
            };
            reader.readAsDataURL(input.files[0]);
        }
    }

    private async handleSave(): Promise<void> {
        const newSettings: AppSettings = {
            username: this.usernameInput.value.trim() || 'User',
            avatarDataUrl: this.avatarPreview.src,
            backendUrl: this.backendUrlInput.value.trim(),
            reconnectAttempts: parseInt(this.reconnectAttemptsInput.value, 10) || -1,
        };

        // 持久化到存储
        await saveSettings(newSettings);

        // 调用回调通知主应用
        this.onSave(newSettings);

        this.close();
    }

    public async open(): Promise<void> {
        await this.loadSettings();
        this.modalContainer.classList.remove('hidden');
    }

    public close(): void {
        this.modalContainer.classList.add('hidden');
    }

    private async loadSettings(): Promise<void> {
        const savedSettings = await getSettings();

        const settings = savedSettings || this.getDefaultSettings();

        this.usernameInput.value = settings.username;
        this.avatarPreview.src = settings.avatarDataUrl;
        this.backendUrlInput.value = settings.backendUrl;
        this.reconnectAttemptsInput.value = String(settings.reconnectAttempts);
    }

    public getDefaultSettings(): AppSettings {
        return {
            username: 'One_of_Swarm',
            avatarDataUrl: '/user_avatar.jpg', // 默认头像路径
            backendUrl: 'http://localhost:8000',
            reconnectAttempts: -1,
        };
    }
}