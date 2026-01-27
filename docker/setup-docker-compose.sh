#!/bin/bash
# Quick setup script for docker-compose

echo "🔧 Setting up docker-compose..."

# Add ~/.local/bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "📝 Adding ~/.local/bin to PATH..."
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    echo "✅ Added to ~/.zshrc"
    
    # Also add to .bashrc for compatibility
    if [ -f ~/.bashrc ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        echo "✅ Added to ~/.bashrc"
    fi
    
    echo ""
    echo "💡 To apply changes, run:"
    echo "   source ~/.zshrc"
    echo ""
    echo "Or restart your terminal."
else
    echo "✅ ~/.local/bin is already in PATH"
fi

# Check if docker-compose exists
if [ -f "$HOME/.local/bin/docker-compose" ]; then
    echo "✅ docker-compose found at: $HOME/.local/bin/docker-compose"
    echo ""
    echo "📋 Current PATH status:"
    echo "$PATH" | tr ':' '\n' | grep -E "(local|docker)" || echo "   (not in current session)"
    echo ""
    echo "💡 You can use:"
    echo "   $HOME/.local/bin/docker-compose --version"
    echo ""
    echo "Or after reloading shell:"
    echo "   docker-compose --version"
else
    echo "⚠️  docker-compose not found at ~/.local/bin/docker-compose"
    echo "   Run: ansible-playbook ansible/install-docker-compose.yml"
fi

# Check if Docker is installed
if command -v docker &> /dev/null; then
    echo "✅ Docker is installed"
    if docker ps &> /dev/null; then
        echo "✅ Docker is running"
    else
        echo "⚠️  Docker is not running. Please start Docker Desktop."
    fi
else
    echo "⚠️  Docker is not installed or not in PATH"
    echo "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
fi
