@echo off
echo 🐣 Syncing CheckMe (Windows)...
echo.

REM Use correct Node version
echo 📦 Checking Node version...
nvm use 22.20.0
echo.

REM Pull latest changes
echo ⬇️  Pulling latest changes...
git pull origin main
echo.

REM Install/update dependencies
echo 🔧 Installing dependencies...
npm install
echo.

REM Show status
echo 📊 Git status:
git status --short
echo.

echo ✅ Ready to develop on Windows!
echo 🚀 Starting Expo...
echo 🖥️  Press 'a' to open Android Emulator
echo.

npx expo start