"""
VPN应用打开功能
使用macOS系统命令打开PrivadoVPN应用程序
"""
import subprocess
import time
import sys
from pathlib import Path


def open_privadovpn():
    """
    打开PrivadoVPN应用程序
    
    Returns:
        bool: 是否成功打开
    """
    # PrivadoVPN 应用路径（常见位置）
    possible_paths = [
        "/Applications/PrivadoVPN.app",
        "/Applications/PrivadoVPN/PrivadoVPN.app",
        "~/Applications/PrivadoVPN.app",
    ]
    
    vpn_path = None
    for path in possible_paths:
        expanded_path = Path(path).expanduser()
        if expanded_path.exists():
            vpn_path = str(expanded_path)
            break
    
    if not vpn_path:
        print(f"❌ 错误: 未找到PrivadoVPN应用程序")
        print(f"   请确保PrivadoVPN已安装在以下位置之一:")
        for path in possible_paths:
            print(f"     - {path}")
        return False
    
    try:
        print(f"🔄 正在打开PrivadoVPN...")
        # 使用open命令打开应用程序
        subprocess.run(["open", vpn_path], check=True)
        print(f"✅ PrivadoVPN已打开")
        
        # 等待应用程序启动
        time.sleep(2)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 打开PrivadoVPN失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False


def check_privadovpn_running():
    """
    检查PrivadoVPN是否正在运行
    
    Returns:
        bool: 是否正在运行
    """
    try:
        # 使用pgrep检查进程
        result = subprocess.run(
            ["pgrep", "-f", "PrivadoVPN"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def close_privadovpn():
    """
    关闭PrivadoVPN应用程序
    
    Returns:
        bool: 是否成功关闭
    """
    try:
        # 先检查是否正在运行
        if not check_privadovpn_running():
            print(f"ℹ️  PrivadoVPN未运行，无需关闭")
            return True
        
        print(f"🔄 正在关闭PrivadoVPN...")
        
        # 方法1: 使用AppleScript优雅地关闭应用
        applescript_close = '''
        tell application "PrivadoVPN"
            quit
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript_close],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 等待应用关闭
                time.sleep(2)
                if not check_privadovpn_running():
                    print(f"✅ PrivadoVPN已成功关闭")
                    return True
        except Exception as e:
            print(f"⚠️  AppleScript关闭失败: {e}，尝试强制关闭...")
        
        # 方法2: 如果优雅关闭失败，使用kill命令强制关闭
        print(f"🔄 尝试强制关闭...")
        try:
            # 查找进程ID
            result = subprocess.run(
                ["pgrep", "-f", "PrivadoVPN"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            subprocess.run(["kill", pid], check=True, timeout=3)
                            print(f"   已终止进程 {pid}")
                        except Exception as e:
                            print(f"   ⚠️  终止进程 {pid} 失败: {e}")
                
                # 等待进程关闭
                time.sleep(2)
                if not check_privadovpn_running():
                    print(f"✅ PrivadoVPN已强制关闭")
                    return True
                else:
                    print(f"⚠️  部分进程可能仍在运行")
                    return False
            else:
                print(f"ℹ️  未找到运行中的进程")
                return True
        except Exception as e:
            print(f"❌ 强制关闭失败: {e}")
            return False
        
    except Exception as e:
        print(f"❌ 关闭PrivadoVPN时发生错误: {e}")
        return False


def list_all_buttons():
    """
    列出PrivadoVPN应用中所有可用的按钮（用于调试）
    
    Returns:
        list: 按钮标题列表
    """
    try:
        applescript = '''
        tell application "System Events"
            tell process "PrivadoVPN"
                try
                    set buttonList to {}
                    set allButtons to buttons of window 1
                    repeat with btn in allButtons
                        try
                            set btnTitle to title of btn
                            set buttonList to buttonList & btnTitle
                        end try
                    end repeat
                    return buttonList
                on error
                    return {}
                end try
            end tell
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # 解析 AppleScript 返回的列表
            buttons = result.stdout.strip().split(", ")
            return buttons
        return []
    except Exception:
        return []


def click_connect_button():
    """
    点击PrivadoVPN应用中的连接按钮
    
    Returns:
        bool: 是否成功点击
    """
    try:
        print(f"🔄 正在查找并点击连接按钮...")
        
        # 先激活应用窗口
        try:
            activate_script = '''
            tell application "PrivadoVPN"
                activate
            end tell
            '''
            subprocess.run(
                ["osascript", "-e", activate_script],
                capture_output=True,
                timeout=3
            )
            time.sleep(1)
        except Exception:
            pass
        
        # 等待应用界面加载
        print(f"⏳ 等待应用界面加载...")
        time.sleep(5)
        
        # 列出所有按钮用于调试
        print(f"🔍 正在查找可用按钮...")
        buttons = list_all_buttons()
        if buttons:
            print(f"   找到以下按钮: {', '.join(buttons)}")
        else:
            print(f"   ⚠️  未找到按钮，可能需要更多等待时间")
            time.sleep(3)
            buttons = list_all_buttons()
            if buttons:
                print(f"   找到以下按钮: {', '.join(buttons)}")
        
        # 使用 AppleScript 查找并点击连接按钮
        # 尝试多种可能的按钮文本和定位方式
        applescript_commands = [
            # 方法1: 通过按钮文本查找（精确匹配）
            '''
            tell application "System Events"
                tell process "PrivadoVPN"
                    activate
                    delay 0.5
                    try
                        set connectButton to button "点击链接" of window 1
                        click connectButton
                        return "success:点击链接"
                    on error
                        try
                            set connectButton to button "连接" of window 1
                            click connectButton
                            return "success:连接"
                        on error
                            try
                                set connectButton to button "Connect" of window 1
                                click connectButton
                                return "success:Connect"
                            on error
                                return "error:not found"
                            end try
                        end try
                    end try
                end tell
            end tell
            ''',
            # 方法2: 遍历所有按钮，查找包含连接相关文本的按钮
            '''
            tell application "System Events"
                tell process "PrivadoVPN"
                    activate
                    delay 0.5
                    try
                        set allButtons to buttons of window 1
                        repeat with btn in allButtons
                            try
                                set btnTitle to title of btn
                                if btnTitle contains "连接" or btnTitle contains "Connect" or btnTitle contains "链接" or btnTitle contains "Link" or btnTitle contains "点击" or btnTitle contains "Click" then
                                    click btn
                                    return "success:" & btnTitle
                                end if
                            end try
                        end repeat
                        return "error:not found"
                    on error errMsg
                        return "error:" & errMsg
                    end try
                end tell
            end tell
            ''',
            # 方法3: 尝试点击最大的按钮（通常是主要的操作按钮）
            '''
            tell application "System Events"
                tell process "PrivadoVPN"
                    activate
                    delay 0.5
                    try
                        set allButtons to buttons of window 1
                        set maxSize to 0
                        set targetButton to missing value
                        repeat with btn in allButtons
                            try
                                set btnSize to size of btn
                                if btnSize > maxSize then
                                    set maxSize to btnSize
                                    set targetButton to btn
                                end if
                            end try
                        end repeat
                        if targetButton is not missing value then
                            click targetButton
                            return "success:largest button"
                        end if
                        return "error:not found"
                    on error errMsg
                        return "error:" & errMsg
                    end try
                end tell
            end tell
            ''',
            # 方法4: 尝试点击第一个按钮
            '''
            tell application "System Events"
                tell process "PrivadoVPN"
                    activate
                    delay 0.5
                    try
                        set firstButton to button 1 of window 1
                        click firstButton
                        return "success:first button"
                    on error errMsg
                        return "error:" & errMsg
                    end try
                end tell
            end tell
            ''',
            # 方法5: 尝试通过按钮的描述或辅助功能标签查找
            '''
            tell application "System Events"
                tell process "PrivadoVPN"
                    activate
                    delay 0.5
                    try
                        set allButtons to buttons of window 1
                        repeat with btn in allButtons
                            try
                                set btnDescription to description of btn
                                if btnDescription contains "连接" or btnDescription contains "Connect" or btnDescription contains "链接" or btnDescription contains "Link" then
                                    click btn
                                    return "success:by description"
                                end if
                            end try
                        end repeat
                        return "error:not found"
                    on error errMsg
                        return "error:" & errMsg
                    end try
                end tell
            end tell
            '''
        ]
        
        for i, script in enumerate(applescript_commands, 1):
            try:
                print(f"   尝试方法 {i}...")
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=8
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if output.startswith("success:"):
                        method_name = output.split(":", 1)[1] if ":" in output else f"方法 {i}"
                        print(f"✅ 已成功点击连接按钮（{method_name}）")
                        # 等待一下，确认连接开始
                        time.sleep(2)
                        return True
                    else:
                        print(f"   ⚠️  方法 {i} 未找到按钮: {output}")
                else:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    print(f"   ⚠️  方法 {i} 失败: {error_msg}")
            except subprocess.TimeoutExpired:
                print(f"   ⚠️  方法 {i} 超时，尝试下一个方法...")
                continue
            except Exception as e:
                print(f"   ⚠️  方法 {i} 发生异常: {e}")
                continue
        
        print(f"❌ 未能找到连接按钮")
        print(f"   提示: 请手动在 PrivadoVPN 应用中点击连接按钮")
        if buttons:
            print(f"   可用按钮列表: {', '.join(buttons)}")
        return False
        
    except Exception as e:
        print(f"❌ 点击连接按钮时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def open_privadovpn_if_not_running():
    """
    如果PrivadoVPN未运行，则打开它
    
    Returns:
        bool: 是否成功打开或已在运行
    """
    if check_privadovpn_running():
        print(f"ℹ️  PrivadoVPN已在运行中")
        return True
    
    return open_privadovpn()


def open_and_connect_privadovpn():
    """
    打开PrivadoVPN应用程序（仅打开应用，不点击按钮）
    
    Returns:
        bool: 是否成功打开
    """
    # 如果应用未运行，打开它
    if not check_privadovpn_running():
        print(f"🔄 PrivadoVPN未运行，正在打开...")
        if not open_privadovpn():
            return False
        # 等待应用启动
        print(f"⏳ 等待应用启动...")
        time.sleep(2)
        print(f"✅ PrivadoVPN已打开")
        return True
    else:
        print(f"ℹ️  PrivadoVPN已在运行中")
        return True


def main():
    """主函数"""
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--close":
        # 关闭应用
        print("=" * 60)
        print("关闭PrivadoVPN应用程序")
        print("=" * 60)
        print()
        
        success = close_privadovpn()
        
        if success:
            print()
            print("=" * 60)
            print("✅ PrivadoVPN已成功关闭")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("⚠️  关闭PrivadoVPN时出现问题")
            print("=" * 60)
    else:
        # 打开应用并连接
        print("=" * 60)
        print("打开PrivadoVPN应用程序并连接")
        print("=" * 60)
        print()
        
        # 打开应用并点击连接按钮
        success = open_and_connect_privadovpn()
        
        if success:
            print()
            print("=" * 60)
            print("✅ PrivadoVPN已成功打开并尝试连接")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("⚠️  打开PrivadoVPN成功，但连接按钮可能未找到")
            print("=" * 60)
            print("请手动点击连接按钮")


if __name__ == '__main__':
    main()

