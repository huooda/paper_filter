# IEEE Conference Paper Crawler

基于Playwright的IEEE会议论文爬虫工具，支持自动获取论文信息并通过大语言模型进行分析筛选。

## 功能特点

- 自动爬取IEEE会议论文信息
- 使用Playwright实现无头浏览器操作
- 异步并发处理提高效率
- 支持大语言模型分析论文相关性
- 自动保存结果到Excel
- 完整的日志记录

## 环境要求

- Python 3.8+
- Playwright
- pandas
- openpyxl
- requests
- openai

## 安装

1. 克隆仓库
```bash
git clone https://github.com/你的用户名/paper_filter.git
cd paper_filter
```

2. 安装依赖
```bash
pip install -r requirements.txt
playwright install
```

3. 配置API
在`request.py`文件中配置以下内容：
```python
# 设置API密钥
KEY = "你的API密钥"  # 替换为你的API密钥

# 设置API基础URL（如果使用通义千问API）
URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 设置使用的模型（取消注释你想使用的模型）
# model="qwen-max"
model="qwen-plus-2025-01-25"  # 或其他支持的模型
```

4. 配置筛选条件
可以在`request.py`中修改`constraints`变量来自定义论文筛选条件：
```python
constraints = """你的筛选条件"""
```

## 使用方法

1. 修改`playwright_crawler.py`中的会议URL
2. 运行脚本
```bash
python playwright_crawler.py
```

## 项目结构

```
paper_filter/
├── playwright_crawler.py  # 主程序
├── request.py            # API请求模块（包含API配置）
├── requirements.txt      # 依赖列表
└── README.md            # 项目说明
```

## 输出

- `crawler.log`: 运行日志
- `relevant_papers_YYYYMMDD.xlsx`: 筛选后的相关论文信息

## 注意事项

- 请遵守IEEE的使用条款
- 确保API密钥配置正确
- 建议使用无头模式运行
- API调用可能产生费用，请注意控制使用量
- 建议在使用前测试API连接是否正常

## 支持的模型

目前只支持使用openai库访问大模型

可以根据需要在`request.py`中配置不同的模型。

## License

MIT License 