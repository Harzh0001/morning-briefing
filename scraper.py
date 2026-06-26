import os
import requests
import feedparser
from google import genai

# 1. Environment Injection Validation
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "").strip() # e.g., whatsapp:+14155238886
WHATSAPP_TO_NUMBER = os.environ.get("WHATSAPP_TO_NUMBER", "").strip() # e.g., whatsapp:+1234567890

# 2. Curated Technical Information Targets
FEEDS = [
    "https://rss.arxiv.org/rss/cs.LG", # Advanced Machine Learning Research
    "https://techcrunch.com/category/artificial-intelligence/feed/", # Industrial GenAI Shift
    "https://www.biomedcentral.com/journals/rss" # Medical Image Classification
]

def fetch_live_news():
    print("Initializing multi-source ingestion...")
    scraped_articles = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            # Restrict target ingestion to top 10 latest nodes to manage context limits
            for entry in feed.entries[:10]: 
                scraped_articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", "")[:300] # Truncate noise early
                })
        except Exception as e:
            print(f"Ingestion failure on target {url}: {e}")
    return scraped_articles

def generate_report(articles):
    print("Initiating semantic analysis via Gemini Client...")
    # Instantiate the standard SDK Client
    client = genai.Client(api_key=LLM_API_KEY)
    
    prompt = f"""
You are an autonomous engineering operations agent filtering data for Harsh Mishra.

Review this raw unstructured web data batch:
{str(articles)}

Perform semantic matching. Select the top 3-4 entries that align directly with his engineering focus.
For each matched node, output:
1. A bolded clean title
2. A precise, single-sentence engineering-focused summary explaining the practical implication
3. The absolute URL source link

Format the complete payload in clean Markdown optimized for high readability on a mobile device.
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
    
    # WhatsApp limits are ~1600 chars
    if len(text) > 1600:
        chunks = [text[i:i+1600] for i in range(0, len(text), 1600)]
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
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LLM_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, WHATSAPP_TO_NUMBER]):
        print("Critical System Invalidation: Environment variables missing.")
        exit(1)
        
    raw_news = fetch_live_news()
    if raw_news:
        final_report = generate_report(raw_news)
        send_telegram_message(final_report)
        send_whatsapp_message(final_report)
        print("Success! Morning intelligence briefing deployed.")
    else:
        print("Processing halted: No upstream articles retrieved.")
