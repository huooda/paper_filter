from playwright.async_api import async_playwright
import time
import logging
import pandas as pd
from request import request_llm
import re
import asyncio
import os

# 清空日志文件
log_file = 'crawler.log'
if os.path.exists(log_file):
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write('')  # 清空文件内容

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.info("程序启动，日志文件已清空")

def parse_llm_response(response):
    """解析大模型的返回结果"""
    if not response:
        return None, None
    
    try:
        summary_match = re.search(r'论文总结：(.*?)(?=判断结果：|$)', response, re.DOTALL)
        result_match = re.search(r'判断结果：\s*(是|不是)', response)
        
        summary = summary_match.group(1).strip() if summary_match else None
        result = result_match.group(1) if result_match else None
        
        return summary, result
    except Exception as e:
        logging.error(f"解析大模型返回结果时出错: {str(e)}")
        return None, None

def save_to_excel(papers_data, filename='paper_results.xlsx'):
    """保存论文信息到Excel，使用追加模式"""
    try:
        try:
            existing_df = pd.read_excel(filename)
            df = pd.concat([existing_df, pd.DataFrame(papers_data)], ignore_index=True)
        except FileNotFoundError:
            df = pd.DataFrame(papers_data)
        
        df = df.drop_duplicates(subset=['论文名称'], keep='last')
        df.to_excel(filename, index=False, engine='openpyxl')
        logging.info(f"数据已追加保存到 {filename}")
    except Exception as e:
        logging.error(f"保存Excel文件时出错: {str(e)}")

async def get_full_abstract(context, paper_url):
    """获取论文完整摘要"""
    new_page = None
    try:
        # 构建完整URL
        full_url = f"https://ieeexplore.ieee.org{paper_url}"
        # 创建新页面并直接访问URL
        new_page = await context.new_page()
        # 使用 domcontentloaded 事件而不是等待所有资源加载
        response = await new_page.goto(full_url, wait_until='domcontentloaded')
        if not response:
            return None
        
        # 等待并获取完整摘要
        try:
            abstract_element = await new_page.wait_for_selector("div.abstract-text", timeout=10000)
            if abstract_element:
                full_abstract = await abstract_element.text_content()
                return full_abstract.strip() if full_abstract else None
        except Exception:
            # 如果找不到abstract-text，尝试其他可能的选择器
            try:
                abstract_element = await new_page.wait_for_selector("div.text-base-md-lh", timeout=5000)
                if abstract_element:
                    full_abstract = await abstract_element.text_content()
                    return full_abstract.strip() if full_abstract else None
            except Exception:
                return None
        
        return None
    except Exception as e:
        logging.error(f"获取完整摘要时出错: {str(e)}")
        return None
    finally:
        if new_page:
            await new_page.close()

async def process_single_paper(context, paper, index, excel_filename):
    """处理单篇论文的信息"""
    try:
        # 获取标题和链接
        title_element = await paper.query_selector("h2 a")
        title = await title_element.text_content() if title_element else "未知标题"
        paper_url = await title_element.get_attribute('href') if title_element else None
        
        # 获取作者
        authors_element = await paper.query_selector("p.author")
        authors = await authors_element.text_content() if authors_element else "未知作者"
        
        # 获取年份
        year_element = await paper.query_selector("div.publisher-info-container span")
        year = await year_element.text_content() if year_element else "未知年份"
        
        # 获取简短摘要
        abstract_element = await paper.query_selector("div.js-displayer-content span")
        short_abstract = await abstract_element.text_content() if abstract_element else None
        
        # 获取完整摘要
        if paper_url:
            full_abstract = await get_full_abstract(context, paper_url)
            abstract = full_abstract if full_abstract else short_abstract
        else:
            abstract = short_abstract
        
        if not abstract:
            logging.warning(f"未能获取到论文摘要: {title}")
            return None
        
        # 调用大模型进行分析
        llm_response = None
        max_retries = 3
        for retry in range(max_retries):
            llm_response = request_llm(title, abstract)
            if llm_response:
                summary, result = parse_llm_response(llm_response)
                if summary and result:
                    break
            logging.info(f"第{retry + 1}次尝试分析论文失败，{'准备重试' if retry < max_retries-1 else '达到最大重试次数'}")
            await asyncio.sleep(2)
        
        if not llm_response or not summary or not result:
            logging.warning(f"无法获取论文分析结果: {title}")
            return None
        
        paper_info = {
            'title': title,
            'authors': authors,
            'year': year,
            'url': f"https://ieeexplore.ieee.org{paper_url}" if paper_url else "",
            'abstract': abstract,
            'llm_summary': summary,
            'is_relevant': result
        }
        
        # 输出当前论文信息到日志
        logging.info(f"\n当前论文 {index}:")
        logging.info(f"标题: {title}")
        logging.info(f"作者: {authors}")
        logging.info(f"年份: {year}")
        logging.info(f"链接: {paper_url}")
        logging.info(f"完整摘要: {abstract}")
        logging.info(f"论文总结: {summary}")
        logging.info(f"是否相关: {result}")
        logging.info("-" * 100)
        
        if result == "是":
            save_data = [{
                '论文名称': title,
                '论文总结': summary,
                '作者': authors,
                '年份': year,
                '链接': f"https://ieeexplore.ieee.org{paper_url}" if paper_url else ""
            }]
            save_to_excel(save_data, excel_filename)
        
        logging.info(f"成功提取并分析论文信息: {title}")
        return paper_info
    
    except Exception as e:
        logging.warning(f"处理论文时出错: {str(e)}")
        return None

async def get_paper_info(page, url):
    """获取论文信息"""
    try:
        logging.info("开始访问IEEE网站...")
        # 使用 domcontentloaded 事件
        response = await page.goto(url, wait_until='domcontentloaded')
        if not response:
            logging.error("页面加载失败")
            return []
        
        # 等待论文列表容器加载
        try:
            main_content = await page.wait_for_selector("div.List-results-items", timeout=20000)
            if not main_content:
                logging.warning("未找到主要内容容器，可能是最后一页")
                return []
        except Exception:
            logging.warning("等待主要内容容器超时")
            return []
        
        # 获取所有论文项
        papers = await page.query_selector_all("div.result-item")
        if not papers:
            papers = await page.query_selector_all("div.List-results-items article")
        
        if not papers:
            logging.warning("未找到论文列表，可能是最后一页")
            return []
        
        paper_list = []
        excel_filename = f'relevant_papers_{time.strftime("%Y%m%d")}.xlsx'
        
        # 批次处理论文，每批3篇
        batch_size = 3
        for i in range(0, len(papers), batch_size):
            batch_papers = papers[i:i + batch_size]
            logging.info(f"开始处理第 {i//batch_size + 1} 批论文，共 {len(batch_papers)} 篇")
            
            # 处理当前批次的论文
            tasks = []
            for j, paper in enumerate(batch_papers):
                task = process_single_paper(page.context, paper, i + j + 1, excel_filename)
                tasks.append(task)
            
            # 并行处理当前批次的论文
            batch_results = await asyncio.gather(*tasks)
            paper_list.extend([r for r in batch_results if r is not None])
            
            # 批次间稍作等待
            await asyncio.sleep(2)
        
        return paper_list
    
    except Exception as e:
        logging.error(f"爬取过程中出错: {str(e)}")
        raise

async def get_all_papers(base_url):
    """获取所有页面的论文信息"""
    all_papers = []
    page_number = 1  # 从第1页开始
    total_pages_processed = 0
    empty_page_count = 0
    
    async with async_playwright() as p:
        # 启动浏览器，使用无头模式
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']  # 避免被检测为自动化工具
        )
        # 创建新的上下文
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},  # 设置窗口大小
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'  # 设置用户代理
        )
        
        # 启用JavaScript
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        try:
            while True:
                current_url = re.sub(r'pageNumber=\d+', f'pageNumber={page_number}', base_url)
                logging.info(f"\n正在处理第 {page_number} 页...")
                logging.info(f"当前URL: {current_url}")
                logging.info(f"{'='*50}\n开始处理第 {page_number} 页\n{'='*50}")
                
                current_page_papers = await get_paper_info(page, current_url)
                
                if not current_page_papers:
                    empty_page_count += 1
                    logging.info(f"第 {page_number} 页未获取到论文，空页计数：{empty_page_count}")
                    if empty_page_count >= 2:
                        logging.info(f"连续 {empty_page_count} 页未获取到论文，爬取结束")
                        break
                else:
                    empty_page_count = 0
                    all_papers.extend(current_page_papers)
                    total_pages_processed += 1
                    logging.info(f"第 {page_number} 页处理完成，获取到 {len(current_page_papers)} 篇论文")
                
                page_number += 1
                await page.wait_for_timeout(5000)
        
        except Exception as e:
            logging.error(f"爬取过程中出错: {str(e)}")
            raise
        finally:
            await browser.close()
    
    logging.info(f"爬取完成，共处理 {total_pages_processed} 页，获取 {len(all_papers)} 篇论文")
    return all_papers

def main():
    base_url = "https://ieeexplore.ieee.org/xpl/conhome/10801246/proceeding?isnumber=10801290&sortType=vol-only-seq&pageNumber=1"
    try:
        all_papers = asyncio.run(get_all_papers(base_url))
        logging.info(f"共获取到 {len(all_papers)} 篇论文信息")
        
    except Exception as e:
        logging.error(f"主程序执行出错: {str(e)}")

if __name__ == "__main__":
    main() 