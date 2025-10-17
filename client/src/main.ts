// src/main.ts

// 导入 Inter 字体
import '@fontsource/inter';

// 导入单例管理器
import { singletonManager } from './core/singletonManager';

// 定义主异步函数
async function main() {
    console.log("Main function started.");

    // 通过单例管理器获取 AppInitializer 实例
    const app = singletonManager.getAppInitializer();

    // 首先异步初始化应用（加载设置等）
    await app.init();

    // 然后启动应用
    app.start();

    console.log("App initialized and started.");
}

// 调用主函数来启动整个应用程序
main().catch(console.error);

console.log("main.ts loaded. Running main function.");