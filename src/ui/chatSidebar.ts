// src/ui/chatSidebar.ts

export class ChatSidebar {
    private sidebarElement: HTMLDivElement;
    private toggleButton: HTMLButtonElement; // 侧边栏内部的收缩按钮
    private showChatButton: HTMLButtonElement; // 视频上方的展开按钮
    private isCollapsed: boolean = false;
    private bodyElement: HTMLBodyElement; // 用于添加/移除全局类

    constructor() {
        this.sidebarElement = document.getElementById('chat-sidebar') as HTMLDivElement;
        this.toggleButton = document.getElementById('toggle-chat-button') as HTMLButtonElement;
        this.showChatButton = document.getElementById('show-chat-button') as HTMLButtonElement; // 获取新按钮
        this.bodyElement = document.body; // 获取 body 元素

        if (!this.sidebarElement || !this.toggleButton || !this.showChatButton) {
            throw new Error("ChatSidebar: Required elements not found in DOM!");
        }

        this.setupEventListeners();
        this.setCollapsed(false, true); // initialSetup = true，不触发过渡动画
        console.log("ChatSidebar initialized.");
    }

    private setupEventListeners(): void {
        this.toggleButton.addEventListener('click', () => this.toggleCollapse());
        this.showChatButton.addEventListener('click', () => this.toggleCollapse()); // 新按钮也触发切换
    }

    /**
     * 切换聊天侧边栏的收缩状态。
     */
    public toggleCollapse(): void {
        this.setCollapsed(!this.isCollapsed);
    }

    /**
     * 明确设置聊天侧边栏的收缩状态。
     * @param collapsed true 为收缩，false 为展开。
     * @param initialSetup 可选，如果为 true，则立即设置样式，不触发 CSS 过渡动画。
     */
    public setCollapsed(collapsed: boolean, initialSetup: boolean = false): void {
        this.isCollapsed = collapsed;

        // 控制 body 元素的类，驱动视频上按钮的显示/隐藏
        if (this.isCollapsed) {
            this.bodyElement.classList.add('chat-collapsed');
        } else {
            this.bodyElement.classList.remove('chat-collapsed');
        }

        // 在进行样式更改之前，如果不是初始设置，确保过渡属性生效
        if (!initialSetup) {
            this.sidebarElement.style.transition = 'width 0.3s ease-in-out, min-width 0.3s ease-in-out';
            this.toggleButton.style.transition = 'transform 0.3s ease-in-out, background-color 0.2s, color 0.2s';
            this.showChatButton.style.transition = 'opacity 0.3s ease-in-out, visibility 0.3s ease-in-out'; // 新按钮的过渡
        } else {
            // 初始设置时，暂时移除过渡，以避免页面加载时闪烁
            this.sidebarElement.style.transition = 'none';
            this.toggleButton.style.transition = 'none';
            this.showChatButton.style.transition = 'none'; // 新按钮的过渡
        }
        
        if (this.isCollapsed) {
            this.sidebarElement.classList.add('collapsed');
            this.toggleButton.setAttribute('aria-label', '展开聊天');
            // 隐藏侧边栏内部内容
            this.sidebarElement.querySelectorAll(':scope > *:not(.chat-sidebar-header)').forEach(el => {
                (el as HTMLElement).style.opacity = '0';
                (el as HTMLElement).style.pointerEvents = 'none';
            });

            console.log("Chat sidebar collapsed.");
        } else {
            this.sidebarElement.classList.remove('collapsed');
            this.toggleButton.setAttribute('aria-label', '重叠聊天');
            // 显示侧边栏内部内容
            this.sidebarElement.querySelectorAll(':scope > *:not(.chat-sidebar-header)').forEach(el => {
                (el as HTMLElement).style.opacity = '1';
                (el as HTMLElement).style.pointerEvents = 'auto';
            });
            console.log("Chat sidebar expanded.");
        }

        // 强制浏览器重绘以应用无过渡的样式，然后恢复过渡
        if (initialSetup) {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => { 
                    this.sidebarElement.style.transition = ''; 
                    this.toggleButton.style.transition = '';
                    this.showChatButton.style.transition = ''; // 恢复新按钮过渡
                });
            });
        }
    }

    /**
     * 获取当前侧边栏是否收缩。
     * @returns boolean
     */
    public getIsCollapsed(): boolean {
        return this.isCollapsed;
    }
}