# ===========================================
# sync.sh (For MacBook - Office)
# ===========================================
#!/bin/bash

echo "🐣 Syncing CheckMe (MacBook)..."
echo ""

# Use correct Node version
echo "📦 Checking Node version..."
nvm use
echo ""

# Pull latest changes
echo "⬇️  Pulling latest changes..."
git pull origin main
echo ""

# Install/update dependencies
echo "🔧 Installing dependencies..."
npm install
echo ""

# Show status
echo "📊 Git status:"
git status --short
echo ""

echo "✅ Ready to develop on MacBook!"
echo "🚀 Starting Expo..."
echo "📱 Scan QR code with your Android phone (Expo Go app)"
echo ""

npx expo start