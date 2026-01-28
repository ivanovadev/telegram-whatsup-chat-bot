# 🤖 Telegram Userbot - Microservices Architecture

Telegram userbot split into three independent microservices:
1. **Auto-Reply Service** - Handles incoming messages and generates response options
2. **Group Posts Service** - Generates and posts travel content to groups (dev environment)
3. **Channel Posts Service** - Generates and posts travel content to channels (production)

All services can run independently in separate terminals.

## 🧠 Graph Database (Neo4j)

This project actively uses a **Neo4j graph database** to model users, cities and relationships:
- Users: Iva, Eugen, Katerina, Alex
- Locations: London, Krakow, Warsaw, countries (UK, Poland)
- Relationships: `LIVES_IN`, `FRIEND_OF`, `HUSBAND_OF`, `WIFE_OF`, `COLLEAGUE_OF`, `IN_COUNTRY`

The social graph is **automatically (re)seeded on service startup** (see `neo4j_app/user_relationships.py`), so if you delete nodes or relationships in Neo4j Browser, they will be restored the next time the bot starts.

Neo4j integration is used by:
- `group-posts-service/app/main.py` – connects to Neo4j and seeds the demo social graph
- `channel-posts-service/app/main.py` – connects to Neo4j and seeds the same graph

Docker-based Neo4j setup and configuration live in:
- `neo4j/` – `docker-compose.neo4j.yml`, `run-neo4j.sh`, service helpers

Automation & infrastructure:
- `docker/` – helper scripts for Docker workflows
- `ansible/` – Ansible playbooks to automate setup and running Neo4j/Docker tooling

To explore the graph manually, use queries like:

```cypher
MATCH (u:User)-[r]->(x) RETURN u, r, x;
```

## 🏗️ Architecture

```
telegram-whatsup-chat-bot/
├── auto-reply-service/
│   ├── app/      # Entry point
│   │   ├── __init__.py
│   │   └── main.py
│   ├── handlers/      # inbox, control
│   │   ├── __init__.py
│   │   ├── control.py
│   │   └── inbox.py
│   ├── services/      # suggester, budget_guard
│   │   ├── __init__.py
│   │   ├── budget_guard.py
│   │   └── suggester.py
│   ├── storage/      # database
│   │   ├── __init__.py
│   │   └── db.py
│   ├── README.md
│   ├── get_channel_id.py
│   ├── requirements.txt
│   └── run.sh
├── channel-posts-service/
│   ├── app/      # Entry point
│   │   ├── __init__.py
│   │   └── main.py
│   ├── services/      # suggester, budget_guard
│   │   ├── __init__.py
│   │   ├── channel_content.py
│   │   ├── channel_handler.py
│   │   └── image_service.py
│   ├── storage/      # database
│   │   ├── __init__.py
│   │   └── db.py
│   ├── README.md
│   ├── requirements.txt
│   └── run.sh
├── group-posts-service/
│   ├── app/      # Entry point
│   │   ├── __init__.py
│   │   └── main.py
│   ├── content/      # Content generators (channel, person, tech, etc.)
│   │   ├── __init__.py
│   │   ├── africa_content.py
│   │   ├── base_content_generator.py
│   │   ├── channel_content.py
│   │   ├── london_content.py
│   │   ├── person_content.py
│   │   ├── quote_content.py
│   │   ├── spider_content.py
│   │   ├── tech_content.py
│   │   ├── uk_content.py
│   │   └── weather_content.py
│   ├── services/      # suggester, budget_guard
│   │   ├── __init__.py
│   │   ├── channel_handler.py
│   │   ├── image_service.py
│   │   ├── job_content.py
│   │   ├── news_service.py
│   │   ├── services_list.py
│   │   └── ukraine_news_service.py
│   ├── storage/      # database
│   │   ├── __init__.py
│   │   └── db.py
│   ├── tests/      # Test files
│   │   ├── README.md
│   │   ├── test_content_validation.py
│   │   ├── test_services.py
│   │   └── test_services.sh
│   ├── README.md
│   ├── check_weather_api_limit.py
│   ├── requirements.txt
│   ├── run.sh
│   └── test_weather_api.py
├── shared_services/
│   ├── __init__.py
│   ├── budget_guard.py
│   ├── channel_content.py
│   ├── image_service.py
│   ├── suggester.py
│   └── topic_extractor.py
├── tests/
│   ├── __init__.py
│   ├── check_env_vars.py
│   ├── check_extra_markdown.py
│   ├── check_readme.py
│   ├── check_security.py
│   ├── count_lines.py
│   ├── generate_structure.py
│   ├── run_all.sh
│   ├── test_code_quality.py
│   └── test_db.py
└── README.md
```

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

**LLM providers (OpenAI + Gemini):**
This project supports **multiple LLM providers**:
- **OpenAI** is used for most content generation (`OPENAI_API_KEY`, `OPENAI_MODEL`)
- **Gemini** can be enabled for Africa content in `group-posts-service` (`GEMINI_API_KEY`, `GEMINI_MODEL`)
  - Switch with: `AFRICA_LLM_PROVIDER=openai|gemini`
  - Global toggle: `LLM_ENABLED=on|off`

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
- `services/suggester.py` - Response generation
- `services/budget_guard.py` - Cost control

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
- ✅ LLM integration (OpenAI GPT-5.2)
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

group-posts-service/
├── app/
│   └── main.py
├── content/
│   ├── africa_content.py
│   ├── base_content_generator.py
│   ├── channel_content.py
│   ├── london_content.py
│   ├── person_content.py
│   ├── quote_content.py
│   ├── spider_content.py
│   ├── tech_content.py
│   ├── uk_content.py
│   └── weather_content.py
├── data/
│   ├── bot.db
│   ├── person_history.json
│   ├── quote_history.json
│   ├── session.session
│   ├── session_test.session
│   ├── spider_history.json
│   ├── tech_history.json
│   └── weather_api_calls.json
├── services/
│   ├── channel_handler.py
│   ├── image_service.py
│   ├── job_content.py
│   ├── news_service.py
│   ├── services_list.py
│   └── ukraine_news_service.py
├── storage/
│   └── db.py
├── tests/
│   ├── .checklist
│   ├── README.md
│   ├── test_content_validation.py
│   ├── test_services.py
│   └── test_services.sh
├── .env
├── .env.example
├── README.md
├── check_weather_api_limit.py
├── requirements.txt
├── run.sh
└── test_weather_api.py

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
- `status` - Check budget and service status
- `africa` - Generate Africa exploration post
- `canary` - Generate Canary Wharf post
- `job` - Generate job vacancies
- `news` - Generate news summary
- `person` - Generate famous person post
- `quote` - Generate quote of the day
- `spider` - Generate spider post
- `tech` - Generate tech device post
- `travel` / `travel morning` - Generate travel posts
- `uk` - Generate UK post
- `ukraine` - Generate Ukraine news
- `weather` - Generate weather forecastststst

## 📝 License

MIT
