# 🎭 Ansible Playbooks for Telegram Bot

Ansible playbooks for automating Docker and Neo4j setup.

## Requirements

Install Ansible:

```bash

# macOS
brew install ansible

# Or via pip
pip install ansible
```

## Playbooks

### 1. Install Docker Compose

**Option A: Standalone download (recommended, no sudo required):**
```bash
ansible-playbook ansible/install-docker-compose.yml
```

**Option B: Install via Homebrew:**
```bash
brew install docker-compose
```

**Option C: Use Docker Compose plugin (Docker Desktop):**
```bash

# Docker Desktop includes the docker compose plugin
docker compose -f docker/neo4j/docker-compose.neo4j.yml up -d
```

**Note:** Modern Docker Desktop versions include `docker compose` (without dash) as a plugin. If you have Docker Desktop, prefer `docker compose` instead of `docker-compose`.

### 2. Run Neo4j

**Important:** First install Docker Desktop and docker-compose!

```bash

# Start Neo4j (requires Docker and docker-compose)
ansible-playbook ansible/playbook.yml
```

Or with a custom password:

```bash
ansible-playbook ansible/playbook.yml -e "neo4j_password=my_secure_password"
```

## Usage

### Quick start

**Step 1: Install Docker Desktop (if needed)**
```bash

# Recommended to install manually (once per machine):
brew install --cask docker
open -a Docker

# Or download from the website:
# https://www.docker.com/products/docker-desktop
```

**Step 2: Install docker-compose (if needed)**
```bash
ansible-playbook ansible/install-docker-compose.yml
```

**Step 3: Start Neo4j**
```bash

# Via Ansible
ansible-playbook ansible/playbook.yml

# Or directly via helper script
./docker/neo4j/run-neo4j.sh up -d
```

### Alternative: without Ansible

If you already have Docker Desktop:
```bash

# Use docker compose plugin
docker compose -f docker/neo4j/docker-compose.neo4j.yml up -d

# Or docker-compose standalone
docker-compose -f docker/neo4j/docker-compose.neo4j.yml up -d
```

## Troubleshooting

### Error: Homebrew directories are not writable

If you see an error like "directories are not writable":

```bash

# Fix manually (requires sudo)
sudo chown -R $(whoami) /opt/homebrew
chmod u+w /opt/homebrew

# Or use standalone installation (no Homebrew required)
ansible-playbook ansible/install-docker-compose.yml
```

### Ansible is not installed

```bash

# macOS
brew install ansible

# Linux
sudo apt-get install ansible  # Ubuntu/Debian
sudo yum install ansible      # CentOS/RHEL

# pip
pip install ansible
```

### Docker is not installed or not running

```bash

# Install and start Docker Desktop (manually, once per machine)
brew install --cask docker
open -a Docker

# Or download installer from the website:
# https://www.docker.com/products/docker-desktop
```

If Docker Desktop is already installed but not running:

```bash

# Start Docker Desktop manually
open -a Docker

# Wait until it starts (30–60 seconds)
# Check: docker ps
```

### Permission errors

If sudo rights are required:

```bash
ansible-playbook ansible/playbook.yml --ask-become-pass
```

### Check Neo4j status

```bash

# After running the playbook
docker compose -f docker/neo4j/docker-compose.neo4j.yml ps

# Or if you use standalone
docker-compose -f docker/neo4j/docker-compose.neo4j.yml ps
```

## Structure

```
ansible/
├── .gitignore
├── README.md
├── install-docker-compose.yml
└── playbook.yml
```

## Execution order

1. **Check what you already have:**
   - Start Docker Desktop: `open -a Docker`
   - Check: `docker ps`, `docker compose version` (or `docker-compose --version`)

2. **Install Docker Desktop (if needed):**
   ```bash
   brew install --cask docker
   open -a Docker
   ```

3. **Install docker-compose (if needed):**
   ```bash
   ansible-playbook ansible/install-docker-compose.yml
   ```

4. **Start Neo4j:**
   ```bash
   ansible-playbook ansible/playbook.yml
   ```

## Variables

You can override via the `-e` parameter:

```bash

# Change Docker Compose version
ansible-playbook ansible/install-docker-compose.yml -e "docker_compose_version=2.23.0"

# Change Neo4j password
ansible-playbook ansible/playbook.yml -e "neo4j_password=my_password"
```

## Notes

- `playbook.yml` **does not install** Docker – install Docker Desktop first
- If Docker Desktop is already installed, the playbook will simply use it
- The playbook automatically creates `docker/docker-compose.neo4j.yml` if it does not exist
- Neo4j data is stored in Docker volumes
- Use `install-docker-compose.yml` for docker-compose installation (no sudo required)
