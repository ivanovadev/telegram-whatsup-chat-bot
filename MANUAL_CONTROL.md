# Manual Bot Control Guide

This guide explains how to manually control and check the Telegram userbot using commands in your **Saved Messages** (or configured control chat).

## How to Use Commands

All commands are sent as text messages to your **Saved Messages** (or the chat specified in `CONTROL_CHAT_ID` in `.env`). The bot will respond with confirmation or status information.

---

## Status & Monitoring Commands

### `status`
Check the current status of the bot, including budget, LLM usage, and card statistics.

**Example:**
```
status
```

**Response includes:**
- 💰 **Budget**: Current spending, daily limit, alert threshold, hard stop
- 🤖 **LLM**: Enabled status, availability, call count, tokens used
- 📝 **Cards**: Cards created today, pending cards count
- ⚙️ **Modes**: Busy mode status, whitelist status

---

## Card Management Commands

### Reply to a Card Message

When you receive a card notification in your control chat, you can reply to it with:

#### `1`, `2`, or `3`
Select one of the three response options to send to the user.

**Example:**
- Reply to card with: `1`
- Bot sends option 1 to the user and confirms: `✅ Response 1 sent`

#### `0`
Decline the card without sending a response.

**Example:**
- Reply to card with: `0`
- Bot confirms: `❌ Response declined`

#### `custom: <your text>`
Send a custom response instead of the suggested options.

**Example:**
- Reply to card with: `custom: Thanks for your message! I'll get back to you soon.`
- Bot sends your custom text to the user

#### `regen`
Regenerate the three response options for the card.

**Example:**
- Reply to card with: `regen`
- Bot sends a new card with fresh response options

---

## Busy Mode Commands

### `busy on`
Enable busy mode. When enabled, the bot will automatically create cards for incoming messages.

**Example:**
```
busy on
```

**Response:** `✅ Busy mode enabled`

### `busy off`
Disable busy mode. When disabled, the bot will not create cards automatically.

**Example:**
```
busy off
```

**Response:** `✅ Busy mode disabled`

---

## Whitelist Commands

### `whitelist add <username>`
Add a user to the whitelist. Only whitelisted users' messages will be processed when whitelist is enabled.

**Example:**
```
whitelist add @username
```

or

```
whitelist add username
```

**Response:** `✅ @username added to whitelist`

### `whitelist remove <username>`
Remove a user from the whitelist.

**Example:**
```
whitelist remove @username
```

**Response:** `✅ @username removed from whitelist`

### `whitelist list`
List all users currently in the whitelist.

**Example:**
```
whitelist list
```

**Response:**
```
📋 Whitelist:
- @user1 (id: 123456789)
- @user2 (id: 987654321)
```

---

## Travel/Group Post Commands

### `travel`
Manually trigger an evening travel post to the configured group/channel. This generates a "Top 3 Countries for [Travel Type] Travel" post.

**Example:**
```
travel
```

**Response:** 
- `🚀 Generating travel post...`
- `✅ Travel post sent to group!`

**Note:** Requires `CHANNEL_POSTS_ENABLED=on` in `.env` and proper group/channel configuration.

### `travel morning`
Manually trigger a morning post to the configured group/channel. This generates a "Top 5 Countries" post based on various topics (happiest, safest, most beautiful, etc.).

**Example:**
```
travel morning
```

**Response:**
- `🌍 Generating morning post...`
- `✅ Morning post sent to group!`

**Note:** Requires `CHANNEL_POSTS_ENABLED=on` in `.env` and proper group/channel configuration.

### `news`
Manually trigger a news summary post to the configured group/channel. This generates 3 main news items (2 from Bloomberg/BBC, 1 about Ukraine war from Ukrainian Truth).

**Example:**
```
news
```

**Response:**
- `📰 Generating news summary...`
- `✅ News post sent!`

**Note:** Requires `CHANNEL_POSTS_ENABLED=on` in `.env` and proper group/channel configuration.

### `tech`
Manually trigger a tech device post to the configured group/channel. This generates a post about an engineering/electronic device with photo, year of creation, overview, and resource link.

**Example:**
```
tech
```

**Response:**
- `🔧 Generating tech device post...`
- `✅ Tech post sent!`

**Note:** Requires `TECH_POSTS_ENABLED=on` in `.env` and proper group/channel configuration. This command is handled by the tech-posts-service.

### `person`
Manually trigger a famous person post to the configured group/channel. This generates a post about a famous inventor, engineer, or scientist with photo, tricky fact, and Wikipedia link.

**Example:**
```
person
```

**Response:**
- `👤 Generating famous person post...`
- `✅ Person post sent!`

**Note:** Requires `PERSON_POSTS_ENABLED=on` in `.env` and proper group/channel configuration. This command is handled by the famous-person-posts-service.

### `ukraine`
Manually trigger a Ukraine news post to the configured group/channel. This generates 3 main news items from the last 12 hours: economic news, political news, and war news against Russia.

**Example:**
```
ukraine
```

**Response:**
- `🇺🇦 Generating Ukraine news...`
- `✅ Ukraine news post sent!`

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service.

### `spider`
Manually trigger a spider post to the configured group/channel. This generates a post about a spider species (with photo, where to meet, size, color, hunter status, speed, lifespan, dangerous rate).

**Example:**
```
spider
```

**Response:**
- `🕷️ Generating spider post...`
- `✅ Spider post sent!`

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service.

### `london`
Manually trigger a London post to the configured group/channel. This generates information about places to visit in London, facts about London, and facts about British politicians.

**Example:**
```
london
```

**Response:**
- `🇬🇧 Generating London post...`
- `✅ London post sent!`

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service.

### `uk`
Manually trigger a UK post to the configured group/channel. This generates information about UK cities to visit and facts about the UK.

**Example:**
```
uk
```

**Response:**
- `🇬🇧 Generating UK post...`
- `✅ UK post sent!`

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service.

### `job`
Manually trigger a job vacancies post to the configured group/channel. This generates 3 job vacancies in Canary Wharf, London with requirements: DevOps/MLOps/SRE/System Engineer positions, company rating >4, NOT FAANG/bank/AI companies, salary ≥£60,000, NOT remote, with LinkedIn links.

**Example:**
```
job
```

**Response:**
- `💼 Generating job vacancies...`
- `✅ Job post sent!`

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service. Jobs are posted automatically twice per day at 08:00 and 19:00.

### `quote`
Manually trigger a quote of the day post to the configured group/channel. This generates an inspiring quote with author, author info, and practical advice.

**Note:** Previously known as `phrase` command.

**Example:**
```
quote
```

**Response:**
- `💬 Generating quote of the day...`
- `✅ Quote post sent!`

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service.

### `africa`
Manually trigger an Africa exploration post to the configured group/channel. This generates information about exploring an African country with cities, places, activities, and facts.

**Example:**
```
africa
```

**Response:**
- `🌍 Generating Africa exploration post...`
- `✅ Africa post sent!`

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service.

### `weather`
Manually trigger a weather forecast post to the configured group/channel. This generates current weather information for 6 cities (London, Bila Tserkva, Poltava, Bengaluru, Cyprus, Poland) with day/night temperatures and weather emojis.

**Example:**
```
weather
```

**Response:**
- `🌤️ Generating weather forecast...`
- `✅ Weather post sent!`

**Format:**
```
🌤️ Weather | 11 Jan 2026

☁️ UK
London: 8/3°C

❄️ Ukraine
Bila Tserkva: 6/-1°C
Poltava: 5/-2°C

☀️ India
Bengaluru: 27/15°C
```

**Features:**
- Day/Night temperatures in Celsius
- Weather emojis (☀️ sunny, ☁️ cloudy, 🌧️ rain, ❄️ snow, etc.)
- Grouped by country
- Uses OpenWeatherMap API or LLM fallback

**Note:** Requires proper group/channel configuration. This command is handled by the group-posts-service. Weather posts are automatically sent at 09:00 daily.

---

## Group/Channel Setup Commands

### `get group id`
Get the ID of a Telegram group or channel. Useful for setting up `CHANNEL_ID` in `.env`.

**How to use:**
1. Forward any message from the group/channel to your Saved Messages
2. Reply to that forwarded message with: `get group id`

**Example:**
```
get group id
```

**Response:**
```
📋 Group Info:
Title: Travel Group
ID: -1001234567890
Username: @travelgroup

💡 Add to .env:
CHANNEL_ID=-1001234567890
# OR use username:
# CHANNEL_USERNAME=travelgroup
```

---

## Command Summary

### Control & Status Commands
| Command | Description |
|---------|-------------|
| `status` | Show bot status (budget, LLM, cards, modes) |
| `busy on` | Enable busy mode (auto-create cards) |
| `busy off` | Disable busy mode |
| `get group id` | Get group/channel ID (reply to message) |

### Whitelist Management
| Command | Description |
|---------|-------------|
| `whitelist add @user` | Add user to whitelist |
| `whitelist remove @user` | Remove user from whitelist |
| `whitelist list` | List all whitelisted users |

### Content Generation Commands
| Command | Description |
|---------|-------------|
| `travel` | Trigger evening travel post |
| `travel morning` | Trigger morning travel post |
| `news` | Trigger news summary post (Bloomberg, BBC, Ukrainian Truth) |
| `tech` | Trigger tech device post (engineering devices) |
| `person` | Trigger famous person post (inventors, scientists) |
| `ukraine` | Trigger Ukraine news post (economy, politics, war) |
| `spider` | Trigger spider information post |
| `quote` | Trigger quote of the day post (previously `phrase`) |
| `africa` | Trigger Africa exploration post |
| `london` | Trigger London information post |
| `uk` | Trigger UK cities post |
| `job` | Trigger job vacancies post (DevOps/MLOps/SRE, 3 vacancies) |
| `weather` | Trigger weather forecast post (6 cities with emojis) |

### Card Response Commands
| Command | Description |
|---------|-------------|
| `1` / `2` / `3` | Select response option (reply to card) |
| `0` | Decline card (reply to card) |
| `custom: <text>` | Send custom response (reply to card) |
| `regen` | Regenerate options (reply to card) |

---

## Troubleshooting

### Bot not responding to commands?

1. **Check control chat**: Make sure you're sending commands to Saved Messages (or the chat set in `CONTROL_CHAT_ID`)
2. **Check bot is running**: Verify the bot process is active
3. **Check logs**: Look for error messages in the terminal where the bot is running

### Travel posts not working?

1. **Check configuration**: Verify `CHANNEL_POSTS_ENABLED=on` in `.env`
2. **Check group/channel ID**: Ensure `CHANNEL_ID` or `CHANNEL_USERNAME` is set correctly
3. **Check permissions**: Make sure your account has "Post messages" admin permission in the group
4. **Check API keys**: Verify `OPENAI_API_KEY` and `UNSPLASH_ACCESS_KEY` are set (if using LLM and images)

### Cards not appearing?

1. **Check busy mode**: Run `status` to see if busy mode is enabled
2. **Check whitelist**: If whitelist is enabled, ensure the user is whitelisted
3. **Check cooldown**: Users have a cooldown period between cards (default: 300 seconds)
4. **Check LLM**: If LLM is disabled, templates are used instead

---

## Environment Variables Reference

For full control, you can also configure the bot via `.env` file:

- `CONTROL_CHAT_ID`: Control chat ID (default: "me" = Saved Messages)
- `BUSY_MODE`: Enable/disable busy mode (default: "on")
- `WHITELIST_ENABLED`: Enable/disable whitelist (default: "on")
- `WHITELIST_USERNAMES`: Comma-separated list of usernames (e.g., "user1,user2")
- `COOLDOWN_SEC`: Cooldown between cards in seconds (default: 300)
- `CHANNEL_POSTS_ENABLED`: Enable group/channel posts (default: "off")
- `CHANNEL_ID`: Group/channel ID for posts
- `CHANNEL_USERNAME`: Group/channel username (alternative to ID)
- `MORNING_POST_TIME`: Time for morning posts (default: "09:00")
- `EVENING_POST_TIME`: Time for evening posts (default: "20:00")
- `LLM_ENABLED`: Enable LLM features (default: "off")
- `OPENAI_API_KEY`: OpenAI API key for LLM
- `UNSPLASH_ACCESS_KEY`: Unsplash API key for images

---

## Quick Start Examples

### Check if everything is working:
```
status
```

### Enable auto-responses and test:
```
busy on
```

### Test travel post:
```
travel
```

### Add a user to whitelist:
```
whitelist add @username
```

### Respond to an incoming message:
1. Wait for card notification
2. Reply with `1`, `2`, or `3` to send a response
3. Or reply with `custom: Your message here` for custom text

---

For more information, see the main [README.md](README.md).
