# Group Posts Service (Dev Environment)

Telegram userbot service for automated travel posts to **groups** (development/testing environment). Generates country rankings and posts them on schedule.

## Features

- Scheduled morning and evening posts to Telegram groups
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
- `GROUP_POSTS_ENABLED=on`
- `GROUP_ID` or `GROUP_USERNAME`
- `OPENAI_API_KEY` (for LLM)
- `UNSPLASH_ACCESS_KEY` (for images)

See `.env.example` for complete list.

## Differences from Channel Posts Service

- Uses `GROUP_POSTS_ENABLED` instead of `CHANNEL_POSTS_ENABLED`
- Uses `GROUP_ID`/`GROUP_USERNAME` instead of `CHANNEL_ID`/`CHANNEL_USERNAME`
- Designed for development and testing in groups
- Same functionality, different target (groups vs channels)
