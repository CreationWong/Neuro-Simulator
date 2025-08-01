// src/main.ts

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
    
    // 添加窗口尺寸变化监听器，自动切换布局模式
    handleWindowResize();
    window.addEventListener('resize', handleWindowResize);
});

function handleWindowResize() {
    // 获取窗口的宽高比
    const aspectRatio = window.innerWidth / window.innerHeight;
    
    // 如果宽高比小于1（即高度大于宽度），切换到竖屏模式
    if (aspectRatio < 1) {
        document.body.classList.add('vertical-mode');
    } 
    // 如果宽高比大于等于1（即宽度大于等于高度），切换回横屏模式
    else {
        document.body.classList.remove('vertical-mode');
    }
}

console.log("main.ts loaded. Waiting for DOMContentLoaded to initialize the app.");