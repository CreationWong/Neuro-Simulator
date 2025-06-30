// src/core/singletonManager.ts

import { AppInitializer } from './appInitializer';

class SingletonManager {
    private static instance: SingletonManager;
    private appInitializerInstance: AppInitializer | null = null;

    private constructor() {
        // 私有构造函数，防止外部直接实例化
    }

    public static getInstance(): SingletonManager {
        if (!SingletonManager.instance) {
            SingletonManager.instance = new SingletonManager();
        }
        return SingletonManager.instance;
    }

    public getAppInitializer(): AppInitializer {
        if (!this.appInitializerInstance) {
            console.log("Creating new AppInitializer instance...");
            this.appInitializerInstance = new AppInitializer();
        } else {
            console.log("Returning existing AppInitializer instance.");
        }
        return this.appInitializerInstance;
    }
}

// 导出一个全局可用的单例管理器实例
export const singletonManager = SingletonManager.getInstance();