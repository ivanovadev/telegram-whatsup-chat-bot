# Channel Posts Service (Production)

Telegram userbot service for automated travel posts to **channels** (production environment). Generates country rankings and posts them on schedule.

## Features

- Scheduled morning and evening posts to Telegram channels
- Country rankings with images
- LLM-powered content generation
- Image fetching from Unsplash
- Duplicate prevention

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
- `CHANNEL_POSTS_ENABLED=on`
- `CHANNEL_ID` or `CHANNEL_USERNAME`
- `OPENAI_API_KEY` (for LLM)
- `UNSPLASH_ACCESS_KEY` (for images)

See `.env.example` for complete list.

## Project Structure

```
channel-posts-service/
├── app/
│   └── main.py
├── services/
│   ├── channel_content.py
│   ├── channel_handler.py
│   └── image_service.py
├── storage/
│   └── db.py
├── .env
├── .env.example
├── README.md
├── requirements.txt
└── run.sh
```

## Production Use

This service is designed for production use with Telegram channels. For development and testing in groups, use `group-posts-service`.
