from openai import OpenAI
import time

# API配置
KEY = "your-api-key-here"  # 替换为你的API密钥
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API基础URL

# 论文筛选条件
constraints = """在此设置你的论文筛选条件
例如：论文是关于具身智能（Embodied AI）或机器人智能化的研究，
使用大语言模型/多模态模型进行机器人规划、决策和控制。"""

# 初始化OpenAI客户端
client = OpenAI(
    api_key=KEY,
    base_url=URL,
)

def request_llm(title, abstract, max_retries=3):
    """调用大模型进行论文分析，支持重试机制"""
    prompt = f"""你现在是一个专业的机器人和具身智能（Embodied AI）领域的论文分析专家，请你帮我分析一篇论文是否符合筛选条件。

具体要求：
1. 仔细阅读论文的标题和摘要
2. 用简洁的语言总结论文的主要工作（100字以内）
3. 你需要严格按照筛选条件里的内容对论文进行判断

筛选条件：{constraints}

论文信息：
- 标题：{title}
- 摘要：{abstract}

请严格按照以下格式回复，不要有任何额外内容：
论文总结：（你的总结内容）
判断结果：（是/不是）

注意：
- 总结必须是对论文工作的客观描述
- 判断结果必须且只能是"是"或"不是"
- 不要解释判断理由
- 不要添加任何其他内容"""
    
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                # 选择要使用的模型，取消注释你想使用的模型
                # model="qwen-max",
                model="qwen-plus-2025-01-25",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            response = completion.choices[0].message.content
            # 验证响应格式是否正确
            if "论文总结：" in response and "判断结果：" in response and \
               ("是" in response.split("判断结果：")[1] or "不是" in response.split("判断结果：")[1]):
                return response
            else:
                print(f"第{attempt + 1}次尝试：响应格式不正确，准备重试...")
                time.sleep(2)  # 等待2秒后重试
                continue
                
        except Exception as e:
            print(f"第{attempt + 1}次尝试出错: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)  # 等待2秒后重试
                continue
            return None
    
    return None  # 所有重试都失败后返回None