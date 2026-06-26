import os
import requests
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
    url = f"https://newsapi.org/v2/everything?q=(artificial intelligence OR machine learning OR autonomous agents OR AI)&sortBy=publishedAt&language=en&pageSize=100&apiKey={NEWS_API_KEY}"
    
    scraped_articles = []
    try:
        response = requests.get(url)
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
    # Instantiate the standard SDK Client
    client = genai.Client(api_key=LLM_API_KEY)
    
    prompt = f"""
You are an autonomous engineering operations agent filtering data for Harsh Mishra.

His engineering focus and specific interests include:
- AI-related technologies, particularly autonomous agents (like Hermes agents and similar architectures).
- Brilliant ideas and cutting-edge inventions regarding AI.
- Practical applications of how AI can be helpful in day-to-day life.
- Advanced Machine Learning, FinTech Quantitative Analytics, and Deep Learning in Healthcare.

Review this raw unstructured web data batch:
{{str(articles)}}

Perform semantic matching. Select EXACTLY the top 10 entries that align directly with his interests.
For each matched node, output:
1. A bolded clean title
2. A precise, single-sentence summary explaining the practical implication or invention
3. The absolute URL source link

Format the complete payload in clean Markdown optimized for high readability on a mobile device. Ensure you output exactly 10 summaries.
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
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LLM_API_KEY, NEWS_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, WHATSAPP_TO_NUMBER]):
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
