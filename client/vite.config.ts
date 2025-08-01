import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  // Vite 在 Tauri 模式下运行时，防止其清空 Tauri CLI 的 Rust 错误信息
  clearScreen: false,
  // Tauri 需要一个固定的端口来连接前端开发服务器
  server: {
    port: 5173,
    strictPort: true,
    watch: {
      // 告诉 Vite 忽略对 `src-tauri` 目录的监听，避免不必要的重新加载
      ignored: ["**/src-tauri/**", "**/backend/**"],
    },
  },
})
