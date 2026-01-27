# 🐳 Docker Setup for Neo4j

This folder contains all files related to Docker and Neo4j.

## Files

- `docker-compose.neo4j.yml` – main Docker Compose configuration for Neo4j
- `docker-compose.yml` – simple fallback variant
- `setup-docker-compose.sh` – helper script to quickly ensure docker-compose is available
- `run-neo4j.sh` – helper script to start/stop Neo4j with the right docker-compose command

## Quick start

### Option 1: Using the helper script (recommended)

```bash
# Start Neo4j
./docker/run-neo4j.sh up -d

# Check status
./docker/run-neo4j.sh ps

# View logs
./docker/run-neo4j.sh logs -f

# Stop
./docker/run-neo4j.sh down
```

### Option 2: Direct docker-compose / docker compose commands

```bash
# If docker-compose is in PATH
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Or if you have the docker compose plugin
docker compose -f docker/docker-compose.neo4j.yml up -d

# Or using a full path to standalone docker-compose
~/.local/bin/docker-compose -f docker/docker-compose.neo4j.yml up -d
```

For more details, see inline comments inside `docker-compose.neo4j.yml` and `run-neo4j.sh`.
