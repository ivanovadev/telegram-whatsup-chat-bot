# 🤖 Telegram Userbot - Microservices Architecture

Telegram userbot split into three independent microservices:
1. **Auto-Reply Service** - Handles incoming messages and generates response options
2. **Group Posts Service** - Generates and posts travel content to groups (dev environment)
3. **Channel Posts Service** - Generates and posts travel content to channels (production)

All services can run independently in separate terminals.

## 🏗️ Architecture

```
telegram-whatsup-chat-bot/
├── auto-reply-service/      # Auto-reply microservice
│   ├── app/
│   ├── handlers/           # inbox, control
│   ├── shared_services/    # suggester, budget_guard, channel_content, image_service
│   ├── storage/            # database
│   └── requirements.txt
│
├── group-posts-service/     # Group posts microservice (dev)
│   ├── app/
│   ├── content/             # Content generators (channel, person, tech, etc.)
│   ├── services/            # channel_handler, image_service, news_service, etc.
│   ├── storage/             # database
│   └── requirements.txt
│
├── channel-posts-service/   # Channel posts microservice (production)
│   ├── app/
│   ├── services/           # channel_handler, channel_content, image_service
│   ├── storage/            # database
│   └── requirements.txt
│
├── .env.example            # Root .env.example (deprecated, use service-specific)
├── README.md
└── MANUAL_CONTROL.md
```

## 🚀 Quick Start

### Setup

Each service has its own `.env` file. Configure each service separately:

```bash
# Auto-Reply Service
cd auto-reply-service
cp .env.example .env
# Edit .env with your credentials

# Group Posts Service (Dev)
cd ../group-posts-service
cp .env.example .env
# Edit .env with your credentials

# Channel Posts Service (Production)
cd ../channel-posts-service
cp .env.example .env
# Edit .env with your credentials
```

### Run Services Individually

#### Auto-Reply Service

```bash
cd auto-reply-service
./run.sh
```

Or manually:
```bash
cd auto-reply-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

#### Group Posts Service (Dev)

```bash
cd group-posts-service
./run.sh
```

Or manually:
```bash
cd group-posts-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

#### Channel Posts Service (Production)

```bash
cd channel-posts-service
./run.sh
```

Or manually:
```bash
cd channel-posts-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

### Running Multiple Services

You can run multiple services in separate terminals:

**Terminal 1 - Auto-Reply:**
```bash
cd auto-reply-service
./run.sh
```

**Terminal 2 - Group Posts (Dev):**
```bash
cd group-posts-service
./run.sh
```

**Terminal 3 - Channel Posts (Production):**
```bash
cd channel-posts-service
./run.sh
```

## 📋 Environment Variables

Each service has its own `.env` file. See service-specific `.env.example` files:

- `auto-reply-service/.env.example` - Auto-reply configuration
- `group-posts-service/.env.example` - Group posts (dev) configuration
- `channel-posts-service/.env.example` - Channel posts (production) configuration

**Common for all services:**
- `TG_API_ID` - Get from https://my.telegram.org/apps
- `TG_API_HASH` - Get from https://my.telegram.org/apps

**Auto-Reply Service specific:**
- `LLM_ENABLED=on` (optional)
- `OPENAI_API_KEY` (if LLM enabled)
- `BUSY_MODE=on`
- `WHITELIST_ENABLED=on`

**Group Posts Service specific:**
- `GROUP_POSTS_ENABLED=on`
- `GROUP_ID` or `GROUP_USERNAME`
- `OPENAI_API_KEY` (for content generation)
- `UNSPLASH_ACCESS_KEY` (for images)

**Channel Posts Service specific:**
- `CHANNEL_POSTS_ENABLED=on`
- `CHANNEL_ID` or `CHANNEL_USERNAME`
- `OPENAI_API_KEY` (for content generation)
- `UNSPLASH_ACCESS_KEY` (for images)

## 🎯 Services Overview

### Auto-Reply Service

Handles incoming private messages:
- Creates response cards with 3 options
- Uses LLM (OpenAI) or templates
- Supports whitelist and busy mode
- Control chat commands (`status`, `busy on/off`, etc.)

**Files:**
- `app/main.py` - Entry point
- `handlers/inbox.py` - Incoming message handler
- `handlers/control.py` - Control chat commands
- `shared_services/suggester.py` - Response generation
- `shared_services/budget_guard.py` - Cost control

### Group Posts Service (Dev)

Generates and posts travel content to **groups** (development/testing):
- Scheduled morning posts (top 5 countries)
- Scheduled evening posts (top 3 travel destinations)
- Country rankings with images
- Signature dishes and facts

**Files:**
- `app/main.py` - Entry point
- `services/channel_handler.py` - Posting logic
- `content/channel_content.py` - Travel content generation
- `content/person_content.py` - Famous person content
- `content/tech_content.py` - Tech device content
- `content/` - Other content generators (spider, quote, africa, london, uk, job, weather)
- `services/image_service.py` - Image fetching
- `services/news_service.py` - News aggregation
- `services/ukraine_news_service.py` - Ukraine news

### Channel Posts Service (Production)

Generates and posts travel content to **channels** (production):
- Scheduled morning posts (top 5 countries)
- Scheduled evening posts (top 3 travel destinations)
- Country rankings with images
- Signature dishes and facts

**Files:**
- `app/main.py` - Entry point
- `services/channel_handler.py` - Posting logic
- `shared_services/channel_content.py` - Content generation (from root)
- `shared_services/image_service.py` - Image fetching (from root)

## 📁 Data Storage

Each service has its own data directory:
- **Auto-Reply Service**: `auto-reply-service/data/`
- **Group Posts Service**: `group-posts-service/data/`
- **Channel Posts Service**: `channel-posts-service/data/`

Each service stores:
- Session file: `data/session.session`
- Database: `data/bot.db`

**Note:** If you want to share the same Telegram session between services, set the same absolute path in each service's `.env` file for `TG_SESSION_PATH`.

## 📚 Documentation

- [Manual Control Guide](MANUAL_CONTROL.md) - Commands and usage
- [Auto-Reply Service README](auto-reply-service/README.md)
- [Channel Posts Service README](channel-posts-service/README.md)

## ✅ Features

### Auto-Reply Service
- ✅ Telegram userbot (Telethon)
- ✅ LLM integration (OpenAI GPT-4o-mini)
- ✅ Template fallback
- ✅ Whitelist support
- ✅ Busy mode
- ✅ Cost control
- ✅ Cooldown per user
- ✅ Status monitoring

### Channel Posts Service
- ✅ Scheduled posts
- ✅ LLM-powered content
- ✅ Image fetching (Unsplash)
- ✅ Duplicate prevention
- ✅ Country rankings
- ✅ Signature dishes
- ✅ Capital cities

## 🔧 Development

### Project Structure

```
auto-reply-service/
├── app/
│   └── main.py
├── handlers/
│   ├── inbox.py
│   └── control.py
├── shared_services/
│   ├── suggester.py
│   ├── budget_guard.py
│   ├── channel_content.py
│   └── image_service.py
└── storage/
    └── db.py

group-posts-service/
├── app/
│   └── main.py
├── content/              # Content generators
│   ├── channel_content.py
│   ├── person_content.py
│   ├── tech_content.py
│   ├── spider_content.py
│   ├── quote_content.py
│   ├── africa_content.py
│   ├── london_content.py
│   ├── uk_content.py
│   ├── job_content.py
│   └── weather_content.py
└── services/
    ├── channel_handler.py
    ├── image_service.py
    ├── news_service.py
    ├── ukraine_news_service.py
    └── services_list.py

channel-posts-service/
├── app/
│   └── main.py
└── services/
    ├── channel_handler.py
    └── ... (uses shared_services for content/image)
```

### Running Tests

```bash
# From project root
pytest
```

## 💰 Costs

See `.env.example` for budget configuration:
- `DAILY_BUDGET_USD=2.0`
- `ALERT_AT_USD=1.5`
- `HARD_STOP_USD=2.5`

## ⚠️ Troubleshooting

### Commands Not Working in Saved Messages

**Problem:** Commands like `job`, `travel`, `news`, etc. are not being processed even though you see them in logs.

**Symptoms:**
- Log shows: `📨 Received message: 'job' (out=True, sender_id=XXX, me_id=XXX, reply_to=False)`
- But no response or action is taken

**Solution:**
This is expected behavior in Saved Messages. The bot processes commands correctly:
- ✅ Commands work when sent as standalone messages (not replies)
- ✅ Commands are ignored when replying to bot's messages
- ✅ All messages in Saved Messages have `out=True` (this is normal for userbots)

**How to use commands:**
1. Send command as a new message (not a reply): `job`, `travel`, `news`, etc.
2. Wait for bot's response
3. If you don't see a response, check:
   - Is the service running?
   - Are there any errors in logs?
   - Is `GROUP_POSTS_ENABLED=on` in `.env`?
   - Is `GROUP_ID` or `GROUP_USERNAME` set correctly?

**Available commands:**
- `travel` / `travel morning` - Generate travel posts
- `news` - Generate news summary
- `job` - Generate job vacancies
- `person` - Generate famous person post
- `tech` - Generate tech device post
- `ukraine` - Generate Ukraine news
- `spider` - Generate spider post
- `london` - Generate London post
- `uk` - Generate UK post
- `phrase` - Generate phrase of the day
- `africa` - Generate Africa exploration post

See [MANUAL_CONTROL.md](MANUAL_CONTROL.md) for full command documentation.

## 📝 License

MIT
