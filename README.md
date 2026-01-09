# 🤖 Telegram Reply Assistant with LLM Integration

Telegram userbot that helps you manage incoming messages by generating response options using LLM (OpenAI) or templates. Works as a personal assistant that creates "cards" with 3 response options for you to choose from.

## 🎯 Project Goal

Telegram userbot that:
- Automatically creates response cards for incoming private messages
- Generates 3 response options using LLM (OpenAI) or templates
- Supports whitelist and busy mode
- Tracks costs and usage
- Ready to showcase in interviews

**Features:**
- LLM integration (OpenAI GPT-4o-mini)
- Cost control with daily budget limits
- Whitelist support (via env variable or database)
- Cooldown between cards per user
- Status monitoring via control chat

---

## 🏗️ Architecture

```
┌─────────────────────┐
│  Telegram Userbot   │
│   (Telethon API)    │
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │  Inbox      │  ← Incoming private messages
    │  Handler    │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Suggester  │  ← Generate 3 response options
    │  (LLM/Tpl)  │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Control    │  ← You reply with 1/2/3
    │  Handler    │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Database   │  ← Store cards, whitelist, usage
    └─────────────┘
```

---

## 🛠️ Tech Stack

### Tech Stack:
- **Language:** Python 3.11+
- **Telegram Library:** Telethon (userbot)
- **LLM API:** OpenAI GPT-4o-mini
- **Database:** SQLite
- **Cost Control:** Daily budget limits with alerts

---

## 💰 Monthly Costs

Estimated monthly costs for running this chatbot:

### **MVP / Low Usage** (~100-500 messages/day)
- **Hosting (Heroku/Railway):** $5-7/month
- **OpenAI API (gpt-4o-mini):** ~$2-5/month
  - ~500 messages × 200 tokens avg = ~$2-3/month
- **Twilio WhatsApp (optional):** $0-5/month
  - Free tier: 1,000 messages/month
  - After: $0.005 per message
- **Telegram Bot:** Free
- **Total:** **$7-17/month**

### **Medium Usage** (~1,000-2,000 messages/day)
- **Hosting:** $7-10/month
- **OpenAI API:** ~$10-20/month
  - ~2,000 messages × 200 tokens avg = ~$10-15/month
- **Twilio WhatsApp:** $5-15/month
  - ~1,500 messages/month = ~$7.50
- **Total:** **$22-45/month**

### **High Usage** (~5,000+ messages/day)
- **Hosting:** $25-50/month
- **OpenAI API:** ~$50-100/month
  - ~5,000 messages × 200 tokens avg = ~$50-75/month
- **Twilio WhatsApp:** $25-50/month
- **Total:** **$100-200/month**

### **Cost Optimization Tips:**
- Use **Railway.app** or **Render.com** instead of Heroku (cheaper)
- Use **gpt-4o-mini** instead of gpt-4 (10x cheaper)
- Implement **caching** for similar queries
- Use **SQLite** instead of PostgreSQL for MVP (free)
- **Telegram** is completely free (no API costs)

### **Free Alternatives:**
- **Telegram only:** $0/month (if running locally)
- **Railway free tier:** Limited, but good for testing
- **Render free tier:** Sleeps after inactivity, but free

---

## 📋 Project Structure

```
telegram-whatsup-chat-bot/
├── app/
│   └── main.py              # Main entry point (Telegram userbot)
├── handlers/
│   ├── inbox.py             # Handle incoming private messages
│   └── control.py           # Handle commands in control chat
├── services/
│   ├── suggester.py         # Generate response options (LLM or templates)
│   └── budget_guard.py      # Cost control and limits
├── storage/
│   └── db.py                # SQLite database operations
├── tests/
│   └── test_db.py           # Database tests
├── data/                    # Session and database (gitignored)
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
├── run.sh                  # Run script
└── README.md
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables Setup

Create `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Then edit `.env` and fill in your values. See `.env.example` for all available options.

**Required variables:**
- `TG_API_ID` - Get from https://my.telegram.org/apps
- `TG_API_HASH` - Get from https://my.telegram.org/apps

**Optional but recommended:**
- `LLM_ENABLED=on` - Enable LLM features
- `OPENAI_API_KEY` - Your OpenAI API key
- `CHANNEL_POSTS_ENABLED=on` - Enable travel posts
- `CHANNEL_ID` or `CHANNEL_USERNAME` - Target group/channel
- `UNSPLASH_ACCESS_KEY` - For images in posts

See `.env.example` for complete list of all variables with descriptions.

### 3. Run

```bash
./run.sh
```

Or manually:
```bash
python -m app.main
```

---

## 📚 Usage

### How It Works

1. **Incoming Message:** Someone sends you a private message
2. **Card Creation:** Bot creates a card with 3 response options in Saved Messages
3. **You Choose:** Reply to the card with `1`, `2`, or `3`
4. **Response Sent:** Bot sends the selected response to the original sender

### Commands in Control Chat (Saved Messages)

- `status` - Show current status (budget, LLM, cards)
- `busy on/off` - Enable/disable busy mode
- `whitelist add @username` - Add user to whitelist (if DB whitelist enabled)
- `whitelist list` - Show whitelist

---

## ✅ Current Features

- ✅ Telegram userbot (Telethon)
- ✅ LLM integration (OpenAI GPT-4o-mini)
- ✅ Template fallback (when LLM unavailable)
- ✅ Whitelist support (env variable or database)
- ✅ Busy mode
- ✅ Cost control with daily budget
- ✅ Cooldown per user
- ✅ Status monitoring
- ✅ SQLite database

---

## 📖 Documentation

- `QUICKSTART.md` - Quick setup guide
- `.env.example` - Environment variables template

---

## 🐛 Troubleshooting

### Issue: "LLM error: insufficient_quota"
**Solution:** Check OpenAI API key billing, add credits or use templates (`LLM_ENABLED=off`)

### Issue: Cards not appearing
**Solution:** 
- Check `BUSY_MODE=on` in `.env`
- Check whitelist if `WHITELIST_ENABLED=on`
- Check cooldown (300 seconds default)

### Issue: "Card not found or already processed"
**Solution:** Card was already replied to. Wait for new message to create new card.

---

## 📊 Status Check

In Saved Messages, type `status` to see:
- Budget spending and limits
- LLM status and usage
- Cards created today
- Current modes (busy, whitelist)

---

## 📚 Useful Resources

- [Telethon Docs](https://docs.telethon.dev/)
- [OpenAI API](https://platform.openai.com/docs)
- [Telegram API](https://core.telegram.org/api)
