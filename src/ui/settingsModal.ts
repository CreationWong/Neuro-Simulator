// src/ui/settingsModal.ts

// 定义设置的数据结构
export interface AppSettings {
    username: string;
    avatarDataUrl: string;
    backendUrl: string;
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

    private handleSave(): void {
        const newSettings: AppSettings = {
            username: this.usernameInput.value.trim() || 'User',
            avatarDataUrl: this.avatarPreview.src,
            backendUrl: this.backendUrlInput.value.trim(),
        };

        // 持久化到 localStorage
        localStorage.setItem('neuro_settings', JSON.stringify(newSettings));
        
        // 调用回调通知主应用
        this.onSave(newSettings);
        
        this.close();
    }

    public open(): void {
        this.loadSettings();
        this.modalContainer.classList.remove('hidden');
    }

    public close(): void {
        this.modalContainer.classList.add('hidden');
    }

    private loadSettings(): void {
        // --- 核心修复点 ---
        // 调用静态方法需要使用类名，而不是 'this'
        const savedSettings = SettingsModal.getSettings();
        
        this.usernameInput.value = savedSettings.username;
        this.avatarPreview.src = savedSettings.avatarDataUrl;
        this.backendUrlInput.value = savedSettings.backendUrl;
    }
    
    /**
     * 提供一个静态方法，让外部可以方便地获取设置
     */
    public static getSettings(): AppSettings {
        const savedJson = localStorage.getItem('neuro_settings');
        if (savedJson) {
            try {
                // 添加一个try-catch以防localStorage中的JSON格式不正确
                return JSON.parse(savedJson);
            } catch (e) {
                console.error("Failed to parse settings from localStorage, returning defaults.", e);
            }
        }
        // 返回默认值
        return {
            username: 'Files_Transfer',
            avatarDataUrl: '/user_avatar.webp', // 默认头像路径
            backendUrl: 'ws://127.0.0.1:8000',
        };
    }
}