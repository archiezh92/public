from datetime import datetime, timedelta
import feedparser
from notion_client import Client


# === 自定义部分 ===
NOTION_TOKEN = "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"
DATABASE_ID = "23d5b5d49a0a80419586fd461b24b75f"
RSS_URLS = [
    "https://feedpress.me/wx-postlate",         
    "https://36kr.com/feed",                    
    "https://www.leiphone.com/rss",             
    "https://www.technologyreview.com/feed/",
    "https://www.artificialintelligence-news.com/feed/",
    "http://www.jiqizhixin.com/rss",
    "http://web.mit.edu/newsoffice/topic/mitcomputers-rss.xml",
    "https://www.artificialintelligence-news.com/feed/",
    "https://36kr.com/feed-article",
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://www.leiphone.com/rss",

]
AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "ChatGPT", "生成式", "多模态", 
    "OpenAI", "GPT", "Transformer", "深度学习", "LLM", 
    "文心一言", "通义千问", "Sora", "Claude", "Gemini", "AI芯片", "理想", "Claude"
]

def contains_ai_keyword(text):
    for kw in AI_KEYWORDS:
        if kw.lower() in text.lower():
            return True
    return False

def identify_source_name(url):
    if "36kr" in url:
        return "36氪"
    elif "leiphone" in url:
        return "雷锋网"
    elif "technologyreview" in url:
        return "MIT Tech Review"
    elif "wx-postlate" in url:
        return "微信早报"
    else:
        return "News"

def parse_entry_date(entry):
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6]).date()
        elif hasattr(entry, 'published'):
            return datetime.strptime(entry.published[:10], "%Y-%m-%d").date()
        else:
            return datetime.today().date()
    except:
        return datetime.today().date()

# === 抓取 RSS 并筛选 AI 新闻 ===
def get_ai_news_from_rss(rss_url):
    feed = feedparser.parse(rss_url)
    source_name = identify_source_name(rss_url)
    ai_news = []

    today = datetime.today().date()
    one_week_ago = today - timedelta(days=7)

    for entry in feed.entries:
        title = entry.title
        summary_raw = entry.summary if 'summary' in entry else ""
        full_text = title + " " + summary_raw

        news_date = parse_entry_date(entry)

        if contains_ai_keyword(full_text) and one_week_ago <= news_date <= today:
            ai_news.append({
                'headline': title,
                'url': entry.link,
                'source': source_name,
                'date': news_date,
            })
    return ai_news
        
# === 写入 Notion ===
def push_to_notion(news_list):
    notion = Client(auth=NOTION_TOKEN)

    try:
        existing_urls = set()
        response = notion.databases.query(database_id=DATABASE_ID, page_size=100)
        while response:
            for page in response['results']:
                props = page.get('properties', {})
                url_value = props.get('url', {}).get('url')
                if url_value:
                    existing_urls.add(url_value)

            if response.get("has_more"):
                response = notion.databases.query(
                    database_id=DATABASE_ID,
                    start_cursor=response["next_cursor"]
                )
            else:
                break
    except Exception as e:
        print(f"[❗️无法获取 Notion 数据库记录]：{e}")
        return

    for news in news_list:
        if news['url'] in existing_urls:
            print(f"⏩ 跳过重复新闻：{news['headline']}")
            continue

        try:
            notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties={
                    "headline": {"title": [{"text": {"content": news['headline']}}]},
                    "url": {"url": news['url']},
                    "source": {"rich_text": [{"text": {"content": news['source']}}]},
                    "date": {"date": {"start": news['date'].isoformat()}}
                }
            )
        except Exception as e:
            print(f"[Notion写入失败] {news['headline']}：{e}")


# === 主流程 ===
def main():
    all_news = []
    for url in RSS_URLS:
        print(f"🔍 抓取中：{url}")
        items = get_ai_news_from_rss(url)
        all_news.extend(items)

    print(f"🎯 共找到 {len(all_news)} 条与 AI 相关的新闻（限今天/昨天）")
    if all_news:
        push_to_notion(all_news)
        print("✅ 所有新闻已成功写入 Notion")
    else:
        print("😴 没有符合日期范围的 AI 新闻")

if __name__ == "__main__":
    main()
