#!/bin/bash
# Deploy script for building and pushing Docker images to Docker Hub
# Manages tags to keep maximum of 20 tags in the repository

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
SERVICE="${SERVICE:-}"
MAX_TAGS=20

# Function to print colored messages
log_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶${NC} $1"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Load environment variables from .env file
load_env() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        log_info "Loading environment variables from $env_file"
        set -a
        source "$env_file"
        set +a
    else
        log_warning "Environment file $env_file not found, skipping..."
    fi
}

# Check required environment variables
check_required_vars() {
    local missing_vars=()
    
    if [ -z "${DOCKER_REGISTRY:-}" ]; then
        missing_vars+=("DOCKER_REGISTRY")
    fi
    if [ -z "${DOCKERHUB_NAMESPACE:-}" ]; then
        missing_vars+=("DOCKERHUB_NAMESPACE")
    fi
    if [ -z "${DOCKERHUB_REPOSITORY:-}" ]; then
        missing_vars+=("DOCKERHUB_REPOSITORY")
    fi
    if [ -z "${DOCKERHUB_USERNAME:-}" ]; then
        missing_vars+=("DOCKERHUB_USERNAME")
    fi
    if [ -z "${DOCKERHUB_TOKEN:-}" ]; then
        missing_vars+=("DOCKERHUB_TOKEN")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Please set these variables in your .env file or export them in your shell."
        exit 1
    fi
}

# Determine image tag
determine_tag() {
    # Try to get tag from git describe
    if command -v git &> /dev/null && [ -d "$PROJECT_ROOT/.git" ]; then
        cd "$PROJECT_ROOT"
        local git_tag=$(git describe --tags --exact-match 2>/dev/null || git describe --tags 2>/dev/null || echo "")
        if [ -n "$git_tag" ]; then
            echo "$git_tag"
            return
        fi
        
        # Fallback to date + short sha
        local short_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        local date_str=$(date +%Y%m%d)
        echo "${date_str}-${short_sha}"
        return
    fi
    
    # Fallback to date + random string if git is not available
    local date_str=$(date +%Y%m%d)
    local random_str=$(openssl rand -hex 4 2>/dev/null || echo "manual")
    echo "${date_str}-${random_str}"
}

# Login to Docker Hub
docker_login() {
    log_step "Logging in to Docker Hub"
    
    if echo "$DOCKERHUB_TOKEN" | docker login "$DOCKER_REGISTRY" --username "$DOCKERHUB_USERNAME" --password-stdin; then
        log_success "Successfully logged in to Docker Hub"
    else
        log_error "Failed to login to Docker Hub"
        exit 1
    fi
}

# Get Docker Hub API token
get_dockerhub_api_token() {
    log_info "Getting Docker Hub API token"
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$DOCKERHUB_USERNAME\", \"password\": \"$DOCKERHUB_TOKEN\"}" \
        "https://hub.docker.com/v2/users/login/")
    
    local token=$(echo "$response" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$token" ]; then
        log_error "Failed to get Docker Hub API token"
        exit 1
    fi
    
    echo "$token"
}

# List all tags from Docker Hub
list_dockerhub_tags() {
    local api_token="$1"
    local page=1
    local page_size=100
    local all_tags=""
    
    while true; do
        local response=$(curl -s -X GET \
            -H "Authorization: JWT $api_token" \
            "https://hub.docker.com/v2/repositories/${DOCKERHUB_NAMESPACE}/${DOCKERHUB_REPOSITORY}/tags/?page=$page&page_size=$page_size")
        
        local tags=$(echo "$response" | grep -o '"name":"[^"]*' | cut -d'"' -f4)
        
        if [ -z "$tags" ]; then
            break
        fi
        
        if [ -z "$all_tags" ]; then
            all_tags="$tags"
        else
            all_tags="$all_tags"$'\n'"$tags"
        fi
        
        # Check if there are more pages
        local next=$(echo "$response" | grep -o '"next":"[^"]*' | cut -d'"' -f4)
        if [ -z "$next" ]; then
            break
        fi
        
        page=$((page + 1))
    done
    
    echo "$all_tags"
}

# Get tag creation date from Docker Hub
get_tag_date() {
    local api_token="$1"
    local tag="$2"
    
    local response=$(curl -s -X GET \
        -H "Authorization: JWT $api_token" \
        "https://hub.docker.com/v2/repositories/${DOCKERHUB_NAMESPACE}/${DOCKERHUB_REPOSITORY}/tags/${tag}/")
    
    # Extract last_updated timestamp (ISO 8601 format)
    local last_updated=$(echo "$response" | grep -o '"last_updated":"[^"]*' | cut -d'"' -f4)
    
    if [ -n "$last_updated" ]; then
        # Convert ISO 8601 to Unix timestamp for sorting
        # Handle format: 2026-01-27T10:30:45.123456Z or 2026-01-27T10:30:45Z
        local iso_date="${last_updated%%Z*}"  # Remove Z suffix
        iso_date="${iso_date%%.*}"  # Remove fractional seconds
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS - date command with -j flag
            date -j -f "%Y-%m-%dT%H:%M:%S" "$iso_date" "+%s" 2>/dev/null || echo "0"
        else
            # Linux - date command with -d flag
            date -d "$last_updated" "+%s" 2>/dev/null || echo "0"
        fi
    else
        echo "0"
    fi
}

# Delete tag from Docker Hub
delete_dockerhub_tag() {
    local api_token="$1"
    local tag="$2"
    
    log_info "Deleting tag: $tag"
    
    local response=$(curl -s -w "\n%{http_code}" -X DELETE \
        -H "Authorization: JWT $api_token" \
        "https://hub.docker.com/v2/repositories/${DOCKERHUB_NAMESPACE}/${DOCKERHUB_REPOSITORY}/tags/${tag}/")
    
    local http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "204" ] || [ "$http_code" = "200" ]; then
        log_success "Deleted tag: $tag"
        return 0
    else
        log_warning "Failed to delete tag: $tag (HTTP $http_code)"
        return 1
    fi
}

# Manage tags to keep maximum of MAX_TAGS
manage_tags() {
    local api_token="$1"
    local new_tag="$2"
    
    log_step "Managing Docker Hub tags (max: $MAX_TAGS)"
    
    local all_tags=$(list_dockerhub_tags "$api_token")
    local tag_count=$(echo "$all_tags" | grep -v '^$' | wc -l | tr -d ' ')
    
    log_info "Current tag count: $tag_count"
    
    if [ "$tag_count" -lt "$MAX_TAGS" ]; then
        log_success "Tag count ($tag_count) is below maximum ($MAX_TAGS), no cleanup needed"
        return
    fi
    
    # Calculate how many tags to delete
    # We want MAX_TAGS - 1 after deletion (to leave room for the new tag)
    local tags_to_delete=$((tag_count - MAX_TAGS + 1))
    
    if [ "$tags_to_delete" -le 0 ]; then
        log_info "No tags need to be deleted"
        return
    fi
    
    log_info "Need to delete $tags_to_delete oldest tag(s)"
    
    # Get tags with their dates and sort by date (oldest first)
    local tags_with_dates=""
    while IFS= read -r tag; do
        if [ -n "$tag" ] && [ "$tag" != "$new_tag" ]; then
            local tag_date=$(get_tag_date "$api_token" "$tag")
            tags_with_dates="${tags_with_dates}${tag_date}|${tag}"$'\n'
        fi
    done <<< "$all_tags"
    
    # Sort by date (oldest first) and take the oldest tags
    local sorted_tags=$(echo "$tags_with_dates" | sort -t'|' -k1 -n | head -n "$tags_to_delete")
    
    # Delete oldest tags
    local deleted_count=0
    while IFS='|' read -r tag_date tag; do
        if [ -n "$tag" ]; then
            if delete_dockerhub_tag "$api_token" "$tag"; then
                deleted_count=$((deleted_count + 1))
            fi
        fi
    done <<< "$sorted_tags"
    
    log_success "Deleted $deleted_count tag(s)"
}

# Build Docker image
build_image() {
    local image_name="$1"
    local tag="$2"
    local full_image="${image_name}:${tag}"
    
    log_step "Building Docker image: $full_image"
    
    # Check if Dockerfile exists
    if [ ! -f "$PROJECT_ROOT/Dockerfile" ]; then
        log_error "Dockerfile not found at $PROJECT_ROOT/Dockerfile"
        log_info "Please create a Dockerfile in the project root"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    
    if docker build -t "$full_image" .; then
        log_success "Successfully built image: $full_image"
    else
        log_error "Failed to build image: $full_image"
        exit 1
    fi
}

# Push Docker image
push_image() {
    local image_name="$1"
    local tag="$2"
    local full_image="${image_name}:${tag}"
    
    log_step "Pushing Docker image: $full_image"
    
    if docker push "$full_image"; then
        log_success "Successfully pushed image: $full_image"
    else
        log_error "Failed to push image: $full_image"
        exit 1
    fi
}

# Main function
main() {
    log_step "Starting Docker deployment"
    
    # Load environment variables
    load_env "$PROJECT_ROOT/.env"
    
    # If SERVICE is specified, load service-specific .env
    if [ -n "$SERVICE" ]; then
        load_env "$PROJECT_ROOT/$SERVICE/.env"
        log_info "Using service-specific configuration: $SERVICE"
    fi
    
    # Check required variables
    check_required_vars
    
    # Determine tag
    local tag=$(determine_tag)
    log_info "Using tag: $tag"
    
    # Construct image name
    local image_name="${DOCKER_REGISTRY}/${DOCKERHUB_NAMESPACE}/${DOCKERHUB_REPOSITORY}"
    local full_image="${image_name}:${tag}"
    
    log_info "Image: $full_image"
    echo ""
    
    # Login to Docker Hub
    docker_login
    echo ""
    
    # Get API token for tag management
    local api_token=$(get_dockerhub_api_token)
    echo ""
    
    # Manage tags before pushing
    manage_tags "$api_token" "$tag"
    echo ""
    
    # Build image
    build_image "$image_name" "$tag"
    echo ""
    
    # Push image
    push_image "$image_name" "$tag"
    echo ""
    
    log_step "Deployment completed successfully"
    log_success "Image pushed: $full_image"
}

# Run main function
main
