#!/bin/bash
# Helper script to start Neo4j via Docker Compose (neo4j subfolder)

# Go to script directory (docker/neo4j)
cd "$(dirname "$0")"

# Detect docker-compose or docker compose
if command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
    # Docker compose plugin (best option)
    DOCKER_COMPOSE="docker"
    COMPOSE_ARGS=("compose" "-f" "docker-compose.neo4j.yml")
    COMPOSE_TYPE="plugin"
elif command -v docker-compose &> /dev/null; then
    # Standalone docker-compose in PATH
    DOCKER_COMPOSE="docker-compose"
    COMPOSE_ARGS=("-f" "docker-compose.neo4j.yml")
    COMPOSE_TYPE="standalone"
elif [ -f "$HOME/.local/bin/docker-compose" ]; then
    # Check if this is truly standalone or just calling docker compose
    if "$HOME/.local/bin/docker-compose" --version 2>&1 | grep -q "Docker Compose version"; then
        # Standalone in ~/.local/bin
        DOCKER_COMPOSE="$HOME/.local/bin/docker-compose"
        COMPOSE_ARGS=("-f" "docker-compose.neo4j.yml")
        COMPOSE_TYPE="standalone"
    else
        # This invokes docker compose plugin
        DOCKER_COMPOSE="docker"
        COMPOSE_ARGS=("compose" "-f" "docker-compose.neo4j.yml")
        COMPOSE_TYPE="plugin"
    fi
else
    echo "❌ docker-compose not found!"
    echo ""
    echo "💡 Install docker-compose:"
    echo "   ansible-playbook ansible/install-docker-compose.yml"
    echo ""
    echo "Or install Docker Desktop (includes docker compose plugin)"
    exit 1
fi

# Execute command (default: up -d)
CMD_ARGS=("$@")
if [ ${#CMD_ARGS[@]} -eq 0 ]; then
    CMD_ARGS=("up" "-d")
fi

echo "🚀 Starting Neo4j..."
echo "Using: $DOCKER_COMPOSE ${COMPOSE_ARGS[*]} ${CMD_ARGS[*]} ($COMPOSE_TYPE)"
echo ""

exec "$DOCKER_COMPOSE" "${COMPOSE_ARGS[@]}" "${CMD_ARGS[@]}"

