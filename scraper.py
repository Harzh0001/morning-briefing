import os
import requests
from google import genai

# 1. Environment Injection Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "").strip()

def generate_search_query():
    print("Agent thinking: Generating dynamic search query for NewsAPI...")
    client = genai.Client(api_key=LLM_API_KEY)
    
    prompt = """
    You are an autonomous engineering operations agent filtering data for Harsh Mishra.
    His interests include: AI-related technologies, autonomous agents (like Hermes), brilliant AI inventions, practical day-to-day AI applications, Advanced Machine Learning, FinTech Quantitative Analytics, and Deep Learning in Healthcare.
    
    Generate a SINGLE boolean search query string (using AND / OR / parentheses) optimized for the NewsAPI 'q' parameter that will find the most relevant news today. 
    Do NOT use quotes in your response. Output ONLY the raw query string. Keep it under 100 characters.
    Example output: artificial intelligence OR machine learning OR autonomous agents
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        query = response.text.strip()
        print(f"Agent generated query: {query}")
        return query
    except Exception as e:
        print(f"Agent query generation failed. Falling back to default query. Error: {e}")
        return "artificial intelligence OR machine learning OR autonomous agents"

def fetch_live_news(query):
    print("Initializing NewsAPI ingestion...")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "popularity",  # Use popularity instead of publishedAt to get REAL, reliable sources!
        "language": "en",
        "pageSize": 100,
        "apiKey": NEWS_API_KEY
    }
    
    scraped_articles = []
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        for article in data.get("articles", []):
            scraped_articles.append({
                "title": article.get("title"),
                "link": article.get("url"),
                "summary": str(article.get("description", ""))[:300]
            })
    except Exception as e:
        print(f"Ingestion failure from NewsAPI: {e}")
        
    return scraped_articles

def generate_report(articles):
    print("Initiating semantic analysis via Gemini Client...")
    client = genai.Client(api_key=LLM_API_KEY)
    
    # Format the input data cleanly so Gemini doesn't get confused by Python dictionaries
    raw_text = ""
    for idx, art in enumerate(articles):
        raw_text += f"Article {idx+1}:\nTitle: {art['title']}\nLink: {art['link']}\nSummary: {art['summary']}\n\n"
    
    prompt = f"""
You are an autonomous engineering operations agent filtering data for Harsh Mishra.

His engineering focus and specific interests include:
- AI-related technologies, particularly autonomous agents (like Hermes agents and similar architectures).
- Brilliant ideas and cutting-edge inventions regarding AI.
- Practical applications of how AI can be helpful in day-to-day life.
- Advanced Machine Learning, FinTech Quantitative Analytics, and Deep Learning in Healthcare.

CRITICAL INSTRUCTION: You must ONLY select articles from the raw text batch provided below. DO NOT invent, hallucinate, or make up your own articles. If you make up an article, the system will fail.

Review this raw text batch of real news articles:
{raw_text}

Perform semantic matching. Select EXACTLY the top 10 most relevant entries from the list above.

You must format your response in EXACTLY two sections, separated by the exact text "---REPORT_SEPARATOR---".

Section 1 (Short List):
A simple, numbered list of the 10 selected articles containing ONLY the bolded title and the absolute URL link. Do not include summaries here.

---REPORT_SEPARATOR---

Section 2 (Detailed Report):
For each of the 10 articles, provide the bolded title, the link, and a detailed, informative summary (3-4 sentences long) that provides in-depth knowledge about the article, the specific invention, or the practical implication.
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

def publish_to_rentry(markdown_text):
    print("Publishing detailed report to Rentry.co...")
    try:
        url = "https://rentry.co/api/new"
        payload = {"text": markdown_text}
        response = requests.post(url, data=payload)
        response.raise_for_status()
        data = response.json()
        if 'url' in data:
            return data['url']
        else:
            print("Rentry API did not return a URL.")
            return None
    except Exception as e:
        print(f"Rentry publish failed: {e}")
        return None

def heal_payload(broken_payload, error_msg):
    print("Agent self-healing initiated: Fixing broken payload...")
    client = genai.Client(api_key=LLM_API_KEY)
    
    prompt = f"""
    You are an autonomous agent fixing a Telegram API delivery failure.
    The Telegram API rejected the following Markdown payload with this error:
    {error_msg}
    
    Broken Payload:
    {broken_payload}
    
    Fix the Markdown syntax (e.g., escape special characters if necessary, fix unclosed tags, or simplify the formatting) so that Telegram accepts it.
    Output ONLY the fixed payload text. Do not wrap it in markdown code blocks.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Self-healing failed: {e}")
        return broken_payload

def send_telegram_message(text, retries=0):
    if retries > 2:
        print("Max retries exceeded. Agent failed to self-heal payload.")
        return
        
    print("Pushing payload to production communication gateway...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Chunk long payloads safely if they breach limits
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    else:
        chunks = [text]
        
    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(url, json=payload)
            res.raise_for_status()
        except Exception as e:
            error_msg = str(e)
            try:
                error_msg = res.json().get('description', str(e))
            except:
                pass
            print(f"Failed to transmit payload node: {error_msg}")
            
            # Initiate self-healing loop
            fixed_chunk = heal_payload(chunk, error_msg)
            # Recursively retry with the healed payload
            send_telegram_message(fixed_chunk, retries=retries+1)



if __name__ == "__main__":
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LLM_API_KEY, NEWS_API_KEY]):
        print("Critical System Invalidation: Environment variables missing.")
        exit(1)
        
    query = generate_search_query()
    raw_news = fetch_live_news(query)
    if raw_news:
        full_response = generate_report(raw_news)
        
        try:
            short_message, detailed_report = full_response.split("---REPORT_SEPARATOR---")
        except ValueError:
            print("Warning: Gemini failed to output the separator. Using full response as short message.")
            short_message = "Here is your morning briefing:\n"
            detailed_report = full_response
            
        full_markdown = f"# Detailed Morning Tech Report\n\n{detailed_report.strip()}"
        
        report_url = publish_to_rentry(full_markdown)
        if not report_url:
            print("Fallback: Saving to local markdown file due to Rentry failure.")
            with open("latest_report.md", "w", encoding="utf-8") as f:
                f.write(full_markdown)
            report_url = "https://github.com/Harzh0001/morning-briefing/blob/main/latest_report.md"
            
        final_payload = f"{short_message.strip()}\n\n📖 *Read Detailed Report Here:* {report_url}"
        
        send_telegram_message(final_payload)
        print("Success! Morning intelligence briefing deployed.")
    else:
        print("Processing halted: No upstream articles retrieved.")
