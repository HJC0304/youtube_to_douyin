"""
DeepSeek API 请求功能
支持调用 DeepSeek API 并获取反馈
"""
import re
import requests
import json
from typing import Optional, Dict, Any, Callable


def call_deepseek_api(prompt: str, api_key: Optional[str] = None, 
                     model: str = "deepseek-chat",
                     temperature: float = 0.7,
                     max_tokens: int = 2000,
                     quiet: bool = False,
                     timeout: float = 30) -> Optional[Dict[str, Any]]:
    """
    调用 DeepSeek API
    
    Args:
        prompt: 输入的提示词（必需参数）
        api_key: API 密钥，如果为 None 则从环境变量或配置文件读取
        model: 使用的模型，默认为 "deepseek-chat"
        temperature: 温度参数，控制输出的随机性（0-1），默认 0.7
        max_tokens: 最大生成 token 数，默认 2000
        quiet: 为 True 时不打印请求参数与成功响应正文（仍打印错误）
        timeout: HTTP 请求超时（秒）
        
    Returns:
        API 响应数据，如果请求失败返回 None
    """
    # 打印输入的参数
    if not quiet:
        print("=" * 60)
        print("📝 输入参数:")
        print(f"   Prompt: {prompt}")
        print(f"   Model: {model}")
        print(f"   Temperature: {temperature}")
        print(f"   Max Tokens: {max_tokens}")
        print("=" * 60)
        print()
    
    # 获取 API Key（优先从 deepseek/config/deepseek_config.json 读取）
    if api_key is None:
        # 优先从 deepseek/config/deepseek_config.json 读取
        try:
            from pathlib import Path
            config_path = Path(__file__).parent / "config" / "deepseek_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_content = f.read().strip()
                    if config_content:  # 检查文件不为空
                        config = json.loads(config_content)
                        # 支持多种 key 名称
                        api_key = (config.get('api_key') or 
                                  config.get('DEEPSEEK_API_KEY') or 
                                  config.get('apiKey'))
                        if api_key and not quiet:
                            print(f"✅ 从配置文件读取 API Key: {config_path}")
        except json.JSONDecodeError as e:
            print(f"⚠️  配置文件格式错误: {e}")
            print(f"   配置文件路径: {config_path}")
            print("   请确保配置文件是有效的 JSON 格式")
        except Exception as e:
            print(f"⚠️  读取配置文件时出错: {e}")
        
        # 如果配置文件没有，尝试从环境变量读取
        if not api_key:
            import os
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if api_key and not quiet:
                print("✅ 从环境变量读取 API Key")
    
    if not api_key:
        print("❌ 错误: 未找到 API Key")
        print("   请配置以下方式之一:")
        print("   1. 在 deepseek/config/deepseek_config.json 中设置 api_key")
        print("   2. 设置环境变量 DEEPSEEK_API_KEY")
        print("   3. 直接在调用时传入 api_key 参数")
        return None
    
    # DeepSeek API 端点
    url = "https://api.deepseek.com/v1/chat/completions"
    
    # 设置请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建请求数据
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        if not quiet:
            print("🔄 正在请求 DeepSeek API...")
        # 发送 POST 请求
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        
        # 检查响应状态
        response.raise_for_status()
        
        # 解析响应
        response_data = response.json()
        
        if not quiet:
            # 打印 DeepSeek 反馈内容
            print()
            print("=" * 60)
            print("✅ DeepSeek API 响应:")
            print("=" * 60)
            
            # 提取并打印回复内容
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0].get('message', {}).get('content', '')
                print(content)
            else:
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
            
            print("=" * 60)
            print()
            
            # 打印完整的响应信息（可选）
            if 'usage' in response_data:
                usage = response_data['usage']
                print(f"📊 Token 使用情况:")
                print(f"   提示词 tokens: {usage.get('prompt_tokens', 0)}")
                print(f"   完成 tokens: {usage.get('completion_tokens', 0)}")
                print(f"   总计 tokens: {usage.get('total_tokens', 0)}")
                print()
        
        return response_data
        
    except requests.exceptions.RequestException as e:
        print()
        print("=" * 60)
        print(f"❌ 请求错误: {e}")
        print("=" * 60)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"响应内容: {e.response.text}")
        print()
        return None
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 发生错误: {e}")
        print("=" * 60)
        print()
        return None


def parse_deepseek_short_video_metadata_content(content: str) -> Optional[Dict[str, str]]:
    """
    从模型返回的正文中解析视频元数据 JSON（支持 ```json 代码块或内嵌对象）。
    期望字段: title, profile
    """
    if not content or not content.strip():
        return None
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {str(k): ("" if v is None else str(v).strip()) for k, v in obj.items()}
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        if isinstance(obj, dict):
            return {str(k): ("" if v is None else str(v).strip()) for k, v in obj.items()}
    except json.JSONDecodeError:
        return None
    return None


def _emit_deepseek_log(
    log_step: Optional[Callable[[str, str], None]],
    message: str,
    status: str = "INFO",
) -> None:
    """统一 DeepSeek 相关日志：接入业务 log_step 或回退到 print。"""
    if log_step:
        log_step(message, status)
    else:
        print(f"[DeepSeek][{status}] {message}")


def fetch_short_video_clip_metadata_from_video_name(
    video_name: str,
    api_key: Optional[str] = None,
    *,
    timeout: float = 90,
    log_step: Optional[Callable[[str, str], None]] = None,
) -> Optional[Dict[str, str]]:
    """
    根据视频文件名（或展示名）请求 DeepSeek，返回 title / profile。

    Args:
        log_step: 可选，与 DouyinUploader._log_step 相同签名 (message, status)，便于整条上传链路统一日志。
    """
    prompt = (
        "<role>你是一个资深的短视频内容运营，熟悉 YouTube 上热门、有趣的视频内容。</role>"
        "<task>现在我正在将 YouTube 上的有趣短视频搬运到抖音，需要根据提供的视频文件名或标题信息，"
        "生成适合抖音发布的标题和简介（需要把其他语言翻译为中文）。"
        "如果提供的内容信息不足，则根据已有信息尽可能编写标题和简介；若信息极少，可生成简洁、吸引人的标题和简介。</task>"
        "<constraints>1. 标题不能超过25个字。2. 标题请使用中文，非中文内容请翻译或改写为中文。"
        "3. 简介基于提供的内容编写，尽量不要添加无关信息。4. 简介中如需中英对照，英文名与中文名分开表述，不要用括号备注。"
        "5. 标题和简介均使用中文表述。6. 简介中不要出现「()」括弧符号。</constraints>"
        "<output>输出格式为json，key=title表示标题，key=profile表示简介。</output>"
        "<input>提供的内容为：" + video_name + "</input>"
    )
    _emit_deepseek_log(
        log_step,
        "DeepSeek：准备请求视频元数据 | POST https://api.deepseek.com/v1/chat/completions | "
        f"model=deepseek-chat | temperature=0.3 | max_tokens=1024 | timeout={timeout}s",
        "INFO",
    )
    _emit_deepseek_log(log_step, f"DeepSeek：视频名（prompt 尾部拼接）= {video_name!r}", "INFO")
    _emit_deepseek_log(log_step, f"DeepSeek：完整 Prompt =\n{prompt}", "INFO")

    resp = call_deepseek_api(
        prompt,
        api_key=api_key,
        model="deepseek-chat",
        temperature=0.3,
        max_tokens=1024,
        quiet=True,
        timeout=timeout,
    )

    if not resp:
        _emit_deepseek_log(log_step, "DeepSeek：接口返回为空（None），请检查网络、API Key 或上游错误日志", "ERROR")
        return None

    try:
        resp_preview = json.dumps(resp, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        resp_preview = str(resp)
    _emit_deepseek_log(
        log_step,
        f"DeepSeek：接口完整响应 JSON =\n{resp_preview}",
        "SUCCESS",
    )

    if not resp.get("choices"):
        _emit_deepseek_log(log_step, "DeepSeek：响应中无 choices 字段，无法解析助手正文", "ERROR")
        return None

    raw_content = resp["choices"][0].get("message", {}).get("content") or ""
    _emit_deepseek_log(
        log_step,
        f"DeepSeek：助手正文 (message.content) =\n{raw_content if raw_content else '(空)'}",
        "INFO",
    )

    usage = resp.get("usage")
    if usage:
        _emit_deepseek_log(
            log_step,
            f"DeepSeek：token 用量 prompt={usage.get('prompt_tokens')} "
            f"completion={usage.get('completion_tokens')} total={usage.get('total_tokens')}",
            "INFO",
        )

    parsed = parse_deepseek_short_video_metadata_content(raw_content)
    if not parsed:
        _emit_deepseek_log(
            log_step,
            "DeepSeek：未能从助手正文中解析出合法 JSON（title/profile）",
            "WARNING",
        )
        return None

    out = {
        "title": (parsed.get("title") or "").strip(),
        "profile": (parsed.get("profile") or "").strip(),
    }
    _emit_deepseek_log(
        log_step,
        "DeepSeek：解析后的业务字段 =\n" + json.dumps(out, ensure_ascii=False, indent=2),
        "SUCCESS",
    )
    return out


def main():
    """主函数示例"""
    # 示例：调用 DeepSeek API
    prompt = "请用一句话解释什么是人工智能"
    result = call_deepseek_api(prompt)
    
    if result:
        print("✅ API 调用成功")
    else:
        print("❌ API 调用失败")


if __name__ == '__main__':
    main()

