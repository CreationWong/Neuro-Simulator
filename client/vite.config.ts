import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  // Vite 在 Tauri 模式下运行时，防止其清空 Tauri CLI 的 Rust 错误信息
  clearScreen: false,
  // Tauri v2 推荐配置
  envPrefix: ['VITE_', 'TAURI_'],
  build: {
    // Tauri v2 支持 es2021
    target: ['es2021', 'chrome100', 'safari13'],
    // 在调试构建时禁用压缩
    minify: !process.env.TAURI_DEBUG ? 'esbuild' : false,
    // 为调试构建生成 sourcemap
    sourcemap: !!process.env.TAURI_DEBUG,
  },
  // Tauri 需要一个固定的端口来连接前端开发服务器
  server: {
    port: 5173,
    strictPort: true,
    watch: {
      // 告诉 Vite 忽略对 `src-tauri` 目录的监听，避免不必要的重新加载
      ignored: ["**/src-tauri/**", "**/backend/**"],
    },
    proxy: {
      // 将 /bilibili-api 的请求代理到 Bilibili API
      '/bilibili-api': {
        target: 'https://api.bilibili.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/bilibili-api/, ''),
        // 配置代理请求头，模拟浏览器访问
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            proxyReq.setHeader('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
            proxyReq.setHeader('Referer', 'https://space.bilibili.com/');
          });
        },
      },
    },
  },
})
