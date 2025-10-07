#!/bin/bash

# Redis Setup Script for AvitoManagement
# Скрипт установки Redis для AvitoManagement

echo "🚀 Setting up Redis for AvitoManagement..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️ Running as root. This is not recommended for production."
fi

# Detect OS and install Redis
if command -v apt-get &> /dev/null; then
    echo "📦 Detected Debian/Ubuntu system"
    sudo apt update
    sudo apt install -y redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    echo "✅ Redis installed and started on Debian/Ubuntu"
    
elif command -v yum &> /dev/null; then
    echo "📦 Detected CentOS/RHEL system"
    sudo yum install -y redis
    sudo systemctl start redis
    sudo systemctl enable redis
    echo "✅ Redis installed and started on CentOS/RHEL"
    
elif command -v dnf &> /dev/null; then
    echo "📦 Detected Fedora system"
    sudo dnf install -y redis
    sudo systemctl start redis
    sudo systemctl enable redis
    echo "✅ Redis installed and started on Fedora"
    
elif command -v brew &> /dev/null; then
    echo "📦 Detected macOS system"
    brew install redis
    brew services start redis
    echo "✅ Redis installed and started on macOS"
    
else
    echo "❌ Unsupported operating system. Please install Redis manually."
    echo "Visit: https://redis.io/download"
    exit 1
fi

# Test Redis connection
echo "🔍 Testing Redis connection..."
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is running and responding"
else
    echo "❌ Redis is not responding. Please check the installation."
    exit 1
fi

# Configure Redis for production (optional)
echo "⚙️ Configuring Redis for production..."

# Create Redis configuration backup
if [ -f /etc/redis/redis.conf ]; then
    sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup
    echo "📋 Created backup of Redis configuration"
fi

# Basic security settings
echo "🔒 Applying basic security settings..."

# Set a password (optional - uncomment if needed)
# REDIS_PASSWORD=$(openssl rand -base64 32)
# echo "requirepass $REDIS_PASSWORD" | sudo tee -a /etc/redis/redis.conf
# echo "🔑 Redis password set: $REDIS_PASSWORD"

# Bind to localhost only (security)
sudo sed -i 's/^bind 127.0.0.1 ::1/bind 127.0.0.1/' /etc/redis/redis.conf

# Disable dangerous commands
echo "rename-command FLUSHDB \"\"" | sudo tee -a /etc/redis/redis.conf
echo "rename-command FLUSHALL \"\"" | sudo tee -a /etc/redis/redis.conf
echo "rename-command DEBUG \"\"" | sudo tee -a /etc/redis/redis.conf

# Restart Redis to apply changes
sudo systemctl restart redis-server 2>/dev/null || sudo systemctl restart redis 2>/dev/null

echo "🔄 Redis restarted with new configuration"

# Test final connection
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is working correctly after configuration"
else
    echo "❌ Redis failed after configuration. Restoring backup..."
    sudo cp /etc/redis/redis.conf.backup /etc/redis/redis.conf
    sudo systemctl restart redis-server 2>/dev/null || sudo systemctl restart redis 2>/dev/null
fi

# Show Redis status
echo "📊 Redis Status:"
sudo systemctl status redis-server 2>/dev/null || sudo systemctl status redis 2>/dev/null | head -10

echo ""
echo "🎉 Redis setup completed!"
echo ""
echo "📝 Next steps:"
echo "1. Start your AvitoManagement server: cd server && python main.py"
echo "2. Check Redis info via API: GET /api/redis/info"
echo "3. Monitor Redis: redis-cli monitor"
echo ""
echo "🔧 Redis configuration file: /etc/redis/redis.conf"
echo "📋 Redis log file: /var/log/redis/redis-server.log"
echo ""
echo "⚠️ For production, consider:"
echo "- Setting up Redis authentication"
echo "- Configuring Redis persistence"
echo "- Setting up Redis monitoring"
echo "- Configuring firewall rules"
