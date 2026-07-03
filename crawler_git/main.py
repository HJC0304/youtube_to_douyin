"""
爬虫项目主入口
支持命令行方式查看功能和使用示例
"""
# hu
import sys
from cli import CrawlerCLI


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 如果有参数，使用 CLI 工具
        from cli import main as cli_main
        cli_main()
    else:
        # 无参数时显示所有功能
        cli = CrawlerCLI()
        cli.show_all_features()
        print()
        print("💡 提示: 使用 'python main.py list' 查看所有功能")
        print("💡 提示: 使用 'python -m cli youtube search \"关键词\"' 执行搜索")


if __name__ == '__main__':
    main()
