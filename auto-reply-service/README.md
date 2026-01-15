# Auto-Reply Service

Telegram userbot service for automatic reply management. Handles incoming private messages and generates response options using LLM or templates.

## Features

- Automatic card creation for incoming messages
- LLM integration (OpenAI) for response generation
- Whitelist support
- Busy mode
- Cost control with daily budget
- Control chat commands

## Running

### Quick Start (Recommended)

```bash
./run.sh
```

### Manual Setup

```bash

# Create virtual environment (first time)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run service
python -m app.main
```

## Environment Variables

Create `.env` file in this directory:

```bash
cp .env.example .env

# Edit .env with your credentials
```

Required variables:
- `TG_API_ID` - Get from https://my.telegram.org/apps
- `TG_API_HASH` - Get from https://my.telegram.org/apps
- `HUSBAND_USERNAME` - Username for husband (e.g., `user0`)
- `FRIENDS_USERNAMES` - Comma-separated list of friend usernames (e.g., `user1,user2,user3`)
- `LLM_ENABLED` (optional)
- `OPENAI_API_KEY` (if LLM enabled)

**Response Types:**
- Husband: Warm, personal tone with optional endearments
- Friends: Warm and friendly but professional
- Others: Polite and neutral

See `.env.example` for complete list.

## Project Structure

```
auto-reply-service/
├── app/
│   └── main.py
├── data/
├── handlers/
│   ├── control.py
│   └── inbox.py
├── services/
│   ├── budget_guard.py
│   └── suggester.py
├── storage/
│   └── db.py
├── .env
├── .env.example
├── README.md
├── get_channel_id.py
├── requirements.txt
└── run.sh
```
