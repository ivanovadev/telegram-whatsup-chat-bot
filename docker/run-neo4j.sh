#!/bin/bash
# Скрипт для запуску Neo4j через Docker Compose

# Перейти в директорію скрипта
cd "$(dirname "$0")"

# Знайти docker-compose або docker compose
if command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
    # Docker compose plugin (найкращий варіант)
    DOCKER_COMPOSE="docker"
    COMPOSE_ARGS=("compose" "-f" "docker-compose.neo4j.yml")
    COMPOSE_TYPE="plugin"
elif command -v docker-compose &> /dev/null; then
    # Standalone docker-compose в PATH
    DOCKER_COMPOSE="docker-compose"
    COMPOSE_ARGS=("-f" "docker-compose.neo4j.yml")
    COMPOSE_TYPE="standalone"
elif [ -f "$HOME/.local/bin/docker-compose" ]; then
    # Перевірити чи це справді standalone або це викликає docker compose
    if "$HOME/.local/bin/docker-compose" --version 2>&1 | grep -q "Docker Compose version"; then
        # Standalone в ~/.local/bin
        DOCKER_COMPOSE="$HOME/.local/bin/docker-compose"
        COMPOSE_ARGS=("-f" "docker-compose.neo4j.yml")
        COMPOSE_TYPE="standalone"
    else
        # Це викликає docker compose plugin
        DOCKER_COMPOSE="docker"
        COMPOSE_ARGS=("compose" "-f" "docker-compose.neo4j.yml")
        COMPOSE_TYPE="plugin"
    fi
else
    echo "❌ docker-compose не знайдено!"
    echo ""
    echo "💡 Встановіть docker-compose:"
    echo "   ansible-playbook ansible/install-docker-compose.yml"
    echo ""
    echo "Або встановіть Docker Desktop (включає docker compose plugin)"
    exit 1
fi

# Виконати команду
echo "🚀 Запуск Neo4j..."
echo "Використовується: $DOCKER_COMPOSE ${COMPOSE_ARGS[*]} ($COMPOSE_TYPE)"
echo ""

exec "$DOCKER_COMPOSE" "${COMPOSE_ARGS[@]}" "$@"
