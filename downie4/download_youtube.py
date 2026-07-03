"""
YouTube视频下载功能
使用Downie 4应用程序下载YouTube视频
"""
import subprocess
import time
import sys
from pathlib import Path


def open_downie4():
    """
    打开Downie 4应用程序
    
    Returns:
        bool: 是否成功打开
    """
    downie_path = "/Applications/Downie 4.app"
    
    if not Path(downie_path).exists():
        print(f"❌ 错误: 未找到Downie 4应用程序")
        print(f"   请确保Downie 4已安装在: {downie_path}")
        return False
    
    try:
        print(f"🔄 正在打开Downie 4...")
        # 使用open命令打开应用程序
        subprocess.run(["open", downie_path], check=True)
        print(f"✅ Downie 4已打开")
        
        # 等待应用程序启动
        time.sleep(2)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 打开Downie 4失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False


def open_url_in_downie4(url: str):
    """
    在Downie 4中打开URL链接
    
    Args:
        url: YouTube视频URL
    """
    try:
        print(f"🔄 正在在Downie 4中打开链接: {url}")
        
        # 方法1: 尝试使用AppleScript直接打开URL（最简单的方法）
        applescript_direct = f'''
        tell application "Downie 4"
            activate
            delay 0.5
            open location "{url}"
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", applescript_direct],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ 已成功在Downie 4中打开链接")
            return True
        
        # 方法2: 如果直接打开失败，尝试通过菜单操作
        print(f"⚠️  直接打开失败，尝试通过菜单操作...")
        applescript_menu = f'''
        tell application "Downie 4"
            activate
            delay 1
        end tell
        tell application "System Events"
            tell process "Downie 4"
                -- 点击菜单栏"文件"
                try
                    click menu bar item "文件" of menu bar 1
                    delay 0.5
                    -- 点击"打开链接"
                    click menu item "打开链接" of menu "文件" of menu bar item "文件" of menu bar 1
                    delay 0.5
                    -- 输入URL
                    keystroke "{url}"
                    delay 0.3
                    -- 按回车确认
                    keystroke return
                    return true
                on error
                    return false
                end try
            end tell
        end tell
        '''
        
        result = subprocess.run(
            ["osascript", "-e", applescript_menu],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ 已通过菜单操作打开链接")
            return True
        else:
            print(f"⚠️  菜单操作失败: {result.stderr}")
            # 如果菜单操作失败，尝试使用URL scheme
            return open_url_directly(url)
            
    except subprocess.TimeoutExpired:
        print(f"❌ 操作超时")
        return open_url_directly(url)
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        # 如果出错，尝试使用备用方法
        return open_url_directly(url)


def open_url_directly(url: str):
    """
    使用备用方法：直接通过URL scheme打开链接
    
    Args:
        url: YouTube视频URL
        
    Returns:
        bool: 是否成功
    """
    try:
        print(f"🔄 尝试使用备用方法打开链接...")
        
        # Downie 4支持通过URL scheme打开链接
        # 格式: downie4://x-callback-url/download?url=YOUTUBE_URL
        downie_url = f"downie4://x-callback-url/download?url={url}"
        
        result = subprocess.run(
            ["open", downie_url],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ 已通过URL scheme打开链接")
            return True
        else:
            print(f"⚠️  URL scheme方法失败")
            return False
    except Exception as e:
        print(f"❌ 备用方法失败: {e}")
        return False




def download_youtube_video(url: str, open_app: bool = True):
    """
    下载YouTube视频
    
    Args:
        url: YouTube视频URL
        open_app: 是否先打开Downie 4应用程序（默认True）
        
    Returns:
        bool: 是否成功
    """
    print("=" * 60)
    print("开始下载YouTube视频")
    print("=" * 60)
    print(f"视频URL: {url}")
    print()
    
    # 验证URL格式
    if not url or not isinstance(url, str):
        print("❌ 错误: URL不能为空")
        return False
    
    if "youtube.com" not in url and "youtu.be" not in url:
        print("⚠️  警告: URL可能不是YouTube链接")
        print("   将继续尝试...")
    
    # 打开Downie 4应用程序
    if open_app:
        if not open_downie4():
            return False
        print()
    
    # 在Downie 4中打开链接
    success = open_url_in_downie4(url)
    
    if success:
        print()
        print("=" * 60)
        print("✅ 下载任务已启动")
        print("=" * 60)
        print("请在Downie 4中确认下载设置并开始下载")
    else:
        print()
        print("=" * 60)
        print("❌ 下载任务启动失败")
        print("=" * 60)
        print("请手动在Downie 4中打开链接")
    
    return success


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python download_youtube.py <youtube_url>")
        print()
        print("示例:")
        print('  python download_youtube.py "https://www.youtube.com/watch?v=VIDEO_ID"')
        return
    
    url = sys.argv[1]
    download_youtube_video(url)


if __name__ == '__main__':
    main()

