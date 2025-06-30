// src/main.ts

// 为 TypeScript 在浏览器环境中识别 Node.js 的计时器函数进行声明
declare var setTimeout: typeof import('timers').setTimeout;
declare var clearTimeout: typeof import('timers').clearTimeout;

// 导入 Inter 字体
import '@fontsource/inter';

// 导入单例管理器
import { singletonManager } from './core/singletonManager';

// 页面加载完成后，启动应用程序
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOMContentLoaded event fired.");
    
    // 通过单例管理器获取 AppInitializer 实例
    const app = singletonManager.getAppInitializer();
    
    // 调用 start 方法，该方法内部有防止重复启动的机制
    app.start(); 
});

console.log("main.ts loaded. Waiting for DOMContentLoaded to initialize the app.");