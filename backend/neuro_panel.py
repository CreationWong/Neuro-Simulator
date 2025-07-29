#!/usr/bin/env python3
"""
Neuro-Sama Simulator Control Panel
This panel controls the backend service and provides a CLI interface for management.
"""

import os
import sys
import asyncio
import subprocess
import signal
import json
from typing import Optional
from pathlib import Path

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
import yaml

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config_manager


class NeuroPanel:
    def __init__(self):
        self.backend_process: Optional[subprocess.Popen] = None
        self.backend_running = False
        self.log_lines = []
        self.config_file = "settings.yaml"
        
    async def run(self):
        """Main entry point for the control panel."""
        print("欢迎使用 Neuro-Sama Simulator 控制面板!")
        await self.main_menu()
        
    async def main_menu(self):
        """Display the main menu and handle user choices."""
        while True:
            choices = [
                Choice("backend_control", "后端控制"),
                Choice("control_panel", "直播控制"),
                Choice("config_management", "配置选项"),
                Choice("log_viewer", "日志查看"),
                Choice("toggle_web_panel", "网页面板"),
                Separator(),
                Choice("exit", "退出"),
            ]
            
            action = await inquirer.select(
                message="请选择操作:",
                choices=choices,
                vi_mode=True,
            ).execute_async()
            
            if action == "backend_control":
                await self.backend_control()
            elif action == "control_panel":
                # Check if backend is running before allowing stream control
                if not self.backend_running:
                    print("请先启动后端服务!")
                    await asyncio.sleep(1)
                    continue
                await self.control_panel()
            elif action == "config_management":
                await self.config_management()
            elif action == "log_viewer":
                await self.log_viewer()
            elif action == "toggle_web_panel":
                await self.toggle_web_panel()
            elif action == "exit":
                await self.exit_panel()
                break
                
    async def backend_control(self):
        """Backend service control options."""
        while True:
            # Build choices dynamically based on backend status
            choices = [
                Choice("start_backend", "启动后端服务"),
            ]
            
            if self.backend_running:
                choices.extend([
                    Choice("stop_backend", "停止后端服务"),
                    Choice("restart_backend", "重启后端服务"),
                ])
            else:
                # Use regular strings for disabled options
                choices.extend([
                    "后端未运行(停止)",
                    "后端未运行(重启)",
                ])
            
            choices.append(Choice("back", "返回主菜单"))
            
            action = await inquirer.select(
                message="后端控制:",
                choices=choices,
                vi_mode=True,
            ).execute_async()
            
            # Handle string choices for disabled options
            if isinstance(action, str) and "后端未运行" in action:
                print("后端服务未运行!")
                await asyncio.sleep(1)
                continue
                
            if action == "start_backend":
                await self.start_backend()
            elif action == "stop_backend":
                await self.stop_backend()
            elif action == "restart_backend":
                await self.restart_backend()
            elif action == "back":
                break
                
    async def start_backend(self):
        """Start the backend service."""
        if self.backend_running:
            print("后端服务已在运行!")
            return
            
        try:
            # Start the backend process
            self.backend_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:app", 
                 "--host", config_manager.settings.server.host,
                 "--port", str(config_manager.settings.server.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.backend_running = True
            print("后端服务启动中...")
            
            # Give it a moment to start
            await asyncio.sleep(2)
            
            # Check if it's actually running
            if self.backend_process.poll() is None:
                print("后端服务已启动!")
            else:
                print("后端服务启动失败!")
                self.backend_running = False
        except Exception as e:
            print(f"启动后端服务时出错: {e}")
            self.backend_running = False
            
    async def stop_backend(self):
        """Stop the backend service."""
        if not self.backend_running or not self.backend_process:
            print("后端服务未运行!")
            return
            
        try:
            # Terminate the process
            self.backend_process.terminate()
            self.backend_process.wait(timeout=5)
            self.backend_running = False
            print("后端服务已停止!")
        except subprocess.TimeoutExpired:
            # Force kill if it didn't terminate gracefully
            self.backend_process.kill()
            self.backend_process.wait()
            self.backend_running = False
            print("后端服务已强制停止!")
        except Exception as e:
            print(f"停止后端服务时出错: {e}")
            
    async def restart_backend(self):
        """Restart the backend service."""
        await self.stop_backend()
        await asyncio.sleep(1)
        await self.start_backend()
        
    async def control_panel(self):
        """Display live stream control options."""
        while True:
            action = await inquirer.select(
                message="直播控制:",
                choices=[
                    Choice("start_stream", "开始直播"),
                    Choice("stop_stream", "停止直播"),
                    Choice("restart_stream", "重启直播"),
                    Choice("back", "返回主菜单"),
                ],
                vi_mode=True,
            ).execute_async()
            
            if action == "start_stream":
                await self.send_backend_command("/api/control/start")
            elif action == "stop_stream":
                await self.send_backend_command("/api/control/stop")
            elif action == "restart_stream":
                await self.send_backend_command("/api/control/restart")
            elif action == "back":
                break
                
    async def send_backend_command(self, endpoint):
        """Send a command to the backend service."""
        if not self.backend_running:
            print("后端服务未运行!")
            return
            
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = f"http://{config_manager.settings.server.host}:{config_manager.settings.server.port}{endpoint}"
                response = await client.post(url)
                if response.status_code in [200, 303]:  # 303 is normal for redirects
                    print(f"命令已发送到 {endpoint}")
                else:
                    print(f"发送命令到 {endpoint} 失败: {response.status_code}")
        except Exception as e:
            print(f"发送命令时出错: {e}")
            
    async def config_management(self):
        """View and edit configuration."""
        while True:
            action = await inquirer.select(
                message="配置管理:",
                choices=[
                    Choice("view_config", "查看配置"),
                    Choice("edit_config", "编辑配置"),
                    Choice("reload_config", "热重载配置"),
                    Choice("back", "返回主菜单"),
                ],
                vi_mode=True,
            ).execute_async()
            
            if action == "view_config":
                await self.view_config()
            elif action == "edit_config":
                await self.edit_config()
            elif action == "reload_config":
                # For now, we'll just notify the user to restart the backend for config changes
                print("配置更改将在后端重启后生效")
            elif action == "back":
                break
                
    async def view_config(self):
        """Display current configuration."""
        if not self.backend_running:
            # Read config from file if backend is not running
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                print("\n当前配置:")
                print(json.dumps(config, indent=2, ensure_ascii=False))
                input("\n按回车键继续...")
            except Exception as e:
                print(f"读取配置时出错: {e}")
                input("\n按回车键继续...")
        else:
            # Fetch config from backend API
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    url = f"http://{config_manager.settings.server.host}:{config_manager.settings.server.port}/api/settings"
                    response = await client.get(url)
                    if response.status_code == 200:
                        config = response.json()
                        print("\n当前配置:")
                        print(json.dumps(config, indent=2, ensure_ascii=False))
                    else:
                        print(f"获取配置失败: {response.status_code}")
                input("\n按回车键继续...")
            except Exception as e:
                print(f"获取配置时出错: {e}")
                input("\n按回车键继续...")
                
    async def edit_config(self):
        """Edit configuration file."""
        try:
            # Use system default editor
            editor = os.environ.get('EDITOR', 'nano')
            subprocess.call([editor, self.config_file])
            print("配置文件已编辑，请记得重启后端服务以使更改生效。")
        except Exception as e:
            print(f"编辑配置时出错: {e}")
            
    async def log_viewer(self):
        """View backend logs."""
        print("实时日志查看器 (按 Ctrl+C 返回)")
        try:
            if not self.backend_running:
                print("后端服务未运行，无法获取日志!")
                input("\n按回车键继续...")
                return
                
            # Fetch logs from backend API
            import httpx
            async with httpx.AsyncClient() as client:
                url = f"http://{config_manager.settings.server.host}:{config_manager.settings.server.port}/api/logs"
                response = await client.get(url)
                if response.status_code == 200:
                    log_data = response.json()
                    logs = log_data.get("logs", [])
                    if logs:
                        for line in logs:
                            print(line)
                    else:
                        print("暂无日志")
                else:
                    print(f"获取日志失败: {response.status_code}")
            input("\n按回车键继续...")
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"查看日志时出错: {e}")
            input("\n按回车键继续...")
            
    async def toggle_web_panel(self):
        """Enable or disable the web management panel."""
        try:
            # Read current config
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Toggle panel password
            current_password = config.get('server', {}).get('panel_password')
            if current_password:
                # Disable web panel
                config['server']['panel_password'] = None
                action_text = "已禁用"
            else:
                # Enable web panel with a default password
                config['server']['panel_password'] = "neuro-panel"
                action_text = "已启用，密码设为: neuro-panel"
                
            # Save config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False, indent=2)
                
            print(f"Web管理面板 {action_text}")
            
            # Notify user about restart requirement
            print("注意: 配置更改需要重启后端服务才能生效。")
        except Exception as e:
            print(f"切换Web面板状态时出错: {e}")
            
    async def exit_panel(self):
        """Exit the control panel."""
        if self.backend_running:
            confirm = await inquirer.confirm(
                message="后端服务仍在运行，确定要退出吗?",
                default=False,
            ).execute_async()
            
            if confirm:
                await self.stop_backend()
            else:
                return
                
        print("感谢使用 Neuro-Sama Simulator 控制面板!")


if __name__ == "__main__":
    panel = NeuroPanel()
    try:
        asyncio.run(panel.run())
    except KeyboardInterrupt:
        print("\n正在退出...")
        if panel.backend_running:
            asyncio.run(panel.stop_backend())