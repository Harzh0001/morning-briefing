import os
import requests
import markdown
from telegraph import Telegraph
from google import genai

# 1. Environment Injection Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "").strip()

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "").strip() # e.g., whatsapp:+14155238886
WHATSAPP_TO_NUMBER = os.environ.get("WHATSAPP_TO_NUMBER", "").strip() # e.g., whatsapp:+1234567890

def fetch_live_news():
    print("Initializing NewsAPI ingestion...")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "artificial intelligence OR machine learning OR autonomous agents",
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

def send_telegram_message(text):
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
            print(f"Failed to transmit payload node: {e}")

def send_whatsapp_message(text):
    print("Pushing payload to WhatsApp gateway...")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    # Twilio API strictly limits message bodies to 1600 characters max, even for WhatsApp.
    if len(text) > 1500:
        chunks = [text[i:i+1500] for i in range(0, len(text), 1500)]
    else:
        chunks = [text]
        
    for chunk in chunks:
        payload = {
            "From": TWILIO_FROM_NUMBER,
            "To": WHATSAPP_TO_NUMBER,
            "Body": chunk
        }
        try:
            # Twilio uses form data and basic auth
            res = requests.post(url, data=payload, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
            res.raise_for_status()
        except Exception as e:
            print(f"Failed to transmit WhatsApp node: {e}")

if __name__ == "__main__":
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LLM_API_KEY, NEWS_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, WHATSAPP_TO_NUMBER]):
        print("Critical System Invalidation: Environment variables missing.")
        exit(1)
        
    raw_news = fetch_live_news()
    if raw_news:
        full_response = generate_report(raw_news)
        
        try:
            short_message, detailed_report = full_response.split("---REPORT_SEPARATOR---")
        except ValueError:
            print("Warning: Gemini failed to output the separator. Using full response as short message.")
            short_message = "Here is your morning briefing:\n"
            detailed_report = full_response
            
        print("Publishing detailed report to Telegraph...")
        try:
            tgph = Telegraph()
            tgph.create_account(short_name='AI Agent')
            # Telegraph API only accepts basic HTML tags, markdown library handles conversion
            html_content = markdown.markdown(detailed_report.strip())
            
            # Telegraph API crashes if content is missing, so provide fallback
            if not html_content:
                html_content = "<p>No detailed report generated.</p>"
                
            response = tgph.create_page(
                'Morning Tech Briefing',
                html_content=html_content,
                author_name='AI Ops Agent'
            )
            report_url = response['url']
        except Exception as e:
            print(f"Telegraph publish failed: {e}")
            report_url = "Error generating detailed report link."
            
        final_payload = f"{short_message.strip()}\n\n📖 *Read Detailed Report Here:* {report_url}"
        
        send_telegram_message(final_payload)
        send_whatsapp_message(final_payload)
        print("Success! Morning intelligence briefing deployed.")
    else:
        print("Processing halted: No upstream articles retrieved.")
