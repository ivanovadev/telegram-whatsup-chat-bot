# Docker Deployment Script

This directory contains the deployment script for building and pushing Docker images to Docker Hub.

## Overview

The `deploy.sh` script automates the process of:
1. Building Docker images from the project root
2. Managing Docker Hub tags (keeps maximum of 20 tags)
3. Pushing images to Docker Hub

## Prerequisites

- Docker installed and running
- Docker Hub account credentials configured in `.env` files
- Git repository (for tag generation, optional)

## Environment Variables

The script requires the following environment variables (can be set in `.env` files):

- `DOCKER_REGISTRY` - Docker registry URL (default: `docker.io`)
- `DOCKERHUB_NAMESPACE` - Your Docker Hub namespace/username
- `DOCKERHUB_REPOSITORY` - Repository name (e.g., `telegram-whatsup-chat-bot`, `auto-reply-service`)
- `DOCKERHUB_USERNAME` - Docker Hub username
- `DOCKERHUB_TOKEN` - Docker Hub access token (not password)

### Getting Docker Hub Token

1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Give it a name and permissions (read & write)
4. Copy the token and use it as `DOCKERHUB_TOKEN`

## Usage

### Basic Usage (Root Project)

Deploy the main project image:

```bash
cd /path/to/telegram-whatsup-chat-bot
./deploy/deploy.sh
```

This will:
- Load environment variables from `.env` in the project root
- Build an image tagged with git tag or date+sha
- Push to `docker.io/<namespace>/telegram-whatsup-chat-bot:<tag>`

### Service-Specific Deployment

Deploy a specific service:

```bash
export SERVICE=auto-reply-service
./deploy/deploy.sh
```

This will:
- Load environment variables from both root `.env` and `auto-reply-service/.env`
- Use `DOCKERHUB_REPOSITORY` from the service `.env` file
- Build and push the service-specific image

### Examples

**Deploy auto-reply-service:**
```bash
export SERVICE=auto-reply-service
./deploy/deploy.sh
```

**Deploy group-posts-service:**
```bash
export SERVICE=group-posts-service
./deploy/deploy.sh
```

**Deploy channel-posts-service:**
```bash
export SERVICE=channel-posts-service
./deploy/deploy.sh
```

## Tag Management

The script automatically manages Docker Hub tags:
- **Maximum tags**: 20 (configurable via `MAX_TAGS` variable)
- **Tag selection**: Oldest tags are deleted first
- **Tag format**:
  - Git tags: Uses `git describe --tags` if available
  - Fallback: `YYYYMMDD-<short-sha>` format
  - Manual: `YYYYMMDD-<random>` if git is unavailable

## Tag Generation Logic

1. **Git tag**: If a git tag exists, use it directly
2. **Git describe**: If no exact tag, use `git describe --tags`
3. **Date + SHA**: Format: `YYYYMMDD-<short-sha>` (e.g., `20260127-a1b2c3d`)
4. **Date + random**: If git unavailable, use `YYYYMMDD-<random-hex>`

## Configuration Files

### Root `.env`
```bash
DOCKER_REGISTRY=docker.io
DOCKERHUB_NAMESPACE=your_namespace
DOCKERHUB_REPOSITORY=telegram-whatsup-chat-bot
DOCKERHUB_USERNAME=your_username
DOCKERHUB_TOKEN=your_token
```

### Service `.env` (e.g., `auto-reply-service/.env`)
```bash
DOCKER_REGISTRY=docker.io
DOCKERHUB_NAMESPACE=your_namespace
DOCKERHUB_REPOSITORY=auto-reply-service
DOCKERHUB_USERNAME=your_username
DOCKERHUB_TOKEN=your_token
```

## Dockerfile Requirement

The script expects a `Dockerfile` in the project root. If you don't have one, create it before running the deployment script.

Example minimal Dockerfile:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Copy application code
COPY . .

# Set entrypoint (adjust based on your needs)
CMD ["python", "-m", "app.main"]
```

## Troubleshooting

### "Missing required environment variables"
- Ensure your `.env` file contains all required variables
- Check that the `.env` file is in the correct location (root or service directory)

### "Failed to login to Docker Hub"
- Verify your `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` are correct
- Ensure you're using an access token, not your password
- Check that the token has read/write permissions

### "Dockerfile not found"
- Create a `Dockerfile` in the project root
- Ensure the script is run from the project root or adjust paths

### "Failed to get Docker Hub API token"
- Check your internet connection
- Verify Docker Hub credentials are correct
- Ensure the token hasn't expired

## Script Features

- ✅ Automatic tag management (max 20 tags)
- ✅ Git-based tag generation
- ✅ Fallback tag generation
- ✅ Colored output for better readability
- ✅ Comprehensive error handling
- ✅ Environment variable validation
- ✅ Service-specific deployments

## Notes

- The script uses Docker Hub API v2 for tag management
- Tags are sorted by creation date (oldest first) for deletion
- The script will not delete the tag being pushed
- All operations are logged with clear status messages
