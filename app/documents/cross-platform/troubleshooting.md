# 🔧 Cross-Platform Troubleshooting Guide
## MacBook ↔️ Windows Issues & Solutions

This guide covers common issues when developing CheckMe across Mac and Windows.

---

## 🚨 Critical Issues

### **1. Different Behavior on Mac vs Windows**

**Symptoms:**
- App works on MacBook but fails on Windows (or vice versa)
- Unexpected errors after switching machines
- "Module not found" errors

**Root Causes:**
- Different Node.js versions
- Different npm versions
- Stale `node_modules/`
- Missing dependencies

**Solution:**

```bash
# On BOTH machines, run these commands:

# 1. Check Node version
node -v
# MUST be exactly v22.20.0 on both!

# 2. If wrong version:
# Mac:
nvm use

# Windows:
nvm use 22.20.0

# 3. Clean everything
rm -rf node_modules  # Mac
rmdir /s node_modules  # Windows (PowerShell)

npm cache clean --force
npx expo start --clear

# 4. Fresh install
npm install

# 5. Test
npm run check
```

**Prevention:**
- Always use `.nvmrc` file
- Commit `package-lock.json` to Git
- Run `npm install` after every `git pull`

---

### **2. Line Ending Hell (CRLF vs LF)**

**Symptoms:**
- Git shows changes even though you didn't edit
- Warnings: "CRLF will be replaced by LF"
- Files appear modified after switching machines
- Bash scripts fail on Windows

**Root Cause:**
- Mac uses LF (Line Feed: `\n`)
- Windows uses CRLF (Carriage Return + Line Feed: `\r\n`)
- Git converts automatically, but inconsistently

**Solution:**

```bash
# Step 1: Configure Git properly

# On Mac:
git config --global core.autocrlf input
git config --global core.eol lf

# On Windows:
git config --global core.autocrlf true
git config --global core.eol lf

# Step 2: Verify .gitattributes exists
# (Already provided in artifacts)

# Step 3: Normalize repository
git add --renormalize .
git commit -m "chore: normalize line endings"

# Step 4: Fresh checkout
git rm -rf --cached .
git reset --hard HEAD
```

**Prevention:**
- Use `.gitattributes` file (already provided)
- Configure Git correctly on both machines
- Use modern code editors (VSCode auto-detects)

---

### **3. Environment Variables Not Loading**

**Symptoms:**
- Firebase connection fails
- "Missing required environment variable" error
- Works on one machine, fails on other

**Root Causes:**
- `.env` file missing on new machine
- Wrong file name (e.g., `.env.txt` instead of `.env`)
- Variables not prefixed with `EXPO_PUBLIC_`
- Expo cache not cleared after changing `.env`

**Solution:**

```bash
# 1. Verify .env file exists
# Mac:
ls -la | grep .env

# Windows:
dir /a | findstr .env

# 2. Check file contents
# Mac:
cat .env

# Windows:
type .env

# 3. Verify all variables start with EXPO_PUBLIC_
# Example:
# EXPO_PUBLIC_FIREBASE_API_KEY=...  ✅
# FIREBASE_API_KEY=...              ❌ (won't work!)

# 4. Clear Expo cache and restart
npx expo start --clear

# 5. If still not working, try:
rm -rf .expo  # Mac
rmdir /s .expo  # Windows
npx expo start --clear
```

**Prevention:**
- Keep `.env` synced manually (use password manager)
- Never commit `.env` to Git
- Always prefix with `EXPO_PUBLIC_`
- Clear cache after changing environment variables

---

### **4. Android Emulator Issues (Windows Only)**

**Symptoms:**
- Emulator extremely slow
- "Unable to connect to emulator"
- Expo doesn't detect emulator
- App crashes on emulator

**Solutions:**

**A. Emulator Not Starting:**
```bash
# Open Android Studio
# Tools → Device Manager
# Click Play button on your AVD

# Or from command line:
cd C:\Users\YourName\AppData\Local\Android\Sdk\emulator
emulator -list-avds
emulator -avd Pixel_5_API_33
```

**B. Emulator Too Slow:**
```bash
# In Android Studio:
# Tools → AVD Manager → Edit AVD
# Graphics: Hardware - GLES 2.0
# RAM: 4096 MB (or more)
# Enable: Use Host GPU
# Enable: Multi-Core CPU (4 cores)
```

**C. Expo Not Detecting Emulator:**
```bash
# Make sure emulator is running first
# Then start Expo:
npx expo start

# Press 'a' to open on Android
# If doesn't work, try:
npx expo start --android

# Or use tunnel mode:
npx expo start --tunnel
```

**D. Metro Bundler Connection Issues:**
```bash
# Check if port 8081 is blocked
# Windows:
netstat -ano | findstr :8081

# If blocked, kill process:
taskkill /PID <PID_NUMBER> /F

# Then restart:
npx expo start --clear
```

**Prevention:**
- Allocate enough RAM to emulator
- Close other heavy applications
- Use hardware acceleration
- Consider using physical device instead

---

### **5. Physical Phone Not Connecting (MacBook)**

**Symptoms:**
- QR code scan fails
- "Unable to connect to device"
- Expo Go shows "Could not load"

**Solutions:**

**A. Same WiFi Network:**
```bash
# Make sure MacBook and phone are on SAME WiFi
# Not just same network name, but same actual network
# (Some offices have multiple VLANs)

# Verify IP addresses:
# Mac:
ifconfig | grep inet

# Phone:
# Settings → WiFi → Tap network name → View IP

# IPs should be in same subnet (e.g., 192.168.1.x)
```

**B. Use Tunnel Mode:**
```bash
# Slower, but works through internet:
npx expo start --tunnel

# Scan QR code with Expo Go
```

**C. Firewall Issues:**
```bash
# Mac may be blocking connections
# System Preferences → Security & Privacy → Firewall
# Ensure "Node" or "Expo" is allowed

# Or temporarily disable:
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

# Re-enable after testing:
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
```

**D. Use USB Connection (Alternative):**
```bash
# Enable USB debugging on phone
# Connect via USB
# Run:
npx expo start --localhost

# App will load via USB
```

**Prevention:**
- Stay on same WiFi network
- Use tunnel mode if WiFi issues persist
- Consider using Android emulator on Mac too

---

### **6. Git Pull Conflicts**

**Symptoms:**
- "Merge conflict" after `git pull`
- Can't pull latest changes
- Files show <<<< HEAD markers

**Solutions:**

**A. Simple Conflict Resolution:**
```bash
# 1. See what files conflict
git status

# 2. Open conflicted file
# Look for markers:
# <<<<<<< HEAD
# Your changes
# =======
# Their changes
# >>>>>>> branch

# 3. Edit file, remove markers, keep desired code

# 4. Mark as resolved
git add <filename>
git commit -m "fix: resolve merge conflict"
```

**B. Abort and Start Fresh:**
```bash
# If too complex, discard your changes:
git merge --abort
git reset --hard HEAD

# Or stash your changes:
git stash
git pull origin main
git stash pop  # Apply your changes back
```

**C. Avoid Conflicts (Best Practice):**
```bash
# Before starting work:
git pull origin main

# Before ending work:
git add .
git commit -m "feat: your changes"
git pull origin main  # Pull again before pushing
git push origin main

# If conflicts, resolve immediately
```

**Prevention:**
- Always pull before starting work
- Commit frequently
- Push after every work session
- Use feature branches for big changes

---

### **7. Package Installation Failures**

**Symptoms:**
- `npm install` fails
- "Cannot resolve dependency"
- "Peer dependency" errors
- Different packages on Mac vs Windows

**Solutions:**

**A. Clear Everything:**
```bash
# 1. Delete node_modules
rm -rf node_modules  # Mac
rmdir /s node_modules  # Windows

# 2. Delete package-lock.json
rm package-lock.json  # Mac
del package-lock.json  # Windows

# 3. Clear npm cache
npm cache clean --force

# 4. Fresh install
npm install

# 5. Commit new package-lock.json
git add package-lock.json
git commit -m "chore: update dependencies"
git push
```

**B. Use npm ci (Cleaner Install):**
```bash
# Instead of npm install, use:
npm ci

# This installs exact versions from package-lock.json
# Faster and more reliable for consistent installs
```

**C. Fix Peer Dependency Issues:**
```bash
# If specific package fails:
npm install --legacy-peer-deps

# Or force install:
npm install --force

# Then test thoroughly
```

**Prevention:**
- Always commit `package-lock.json`
- Use `npm ci` instead of `npm install` for clean installs
- Keep npm updated: `npm install -g npm@latest`

---

### **8. TypeScript Errors After Switching**

**Symptoms:**
- Red squiggly lines everywhere
- "Cannot find module" errors
- Types not recognized

**Solutions:**

```bash
# 1. Restart TypeScript server in VSCode
# Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
# "TypeScript: Restart TS Server"

# 2. Delete TypeScript cache
rm -rf .tsbuildinfo

# 3. Verify tsconfig.json is correct

# 4. Re-install types
npm install --save-dev @types/react @types/react-native

# 5. Run type check
npm run type-check
```

**Prevention:**
- Keep TypeScript version consistent
- Commit `tsconfig.json` to Git
- Use same editor (VSCode) on both machines

---

## 🎯 Quick Diagnostic Checklist

When something breaks after switching machines:

```bash
# Run this diagnostic script on BOTH machines:

echo "=== CheckMe Diagnostic ==="
echo ""

echo "Node.js version:"
node -v
echo "(Should be v22.20.0)"
echo ""

echo "npm version:"
npm -v
echo ""

echo "Git status:"
git status --short
echo ""

echo "Current branch:"
git branch --show-current
echo ""

echo "Environment file:"
ls -la .env 2>/dev/null || echo ".env NOT FOUND!"
echo ""

echo "Dependencies installed:"
ls node_modules 2>/dev/null && echo "✅ Yes" || echo "❌ No - Run npm install"
echo ""

echo "Expo cache:"
ls .expo 2>/dev/null && echo "✅ Cache exists" || echo "✅ Cache clean"
echo ""
```

Save as `diagnostic.sh` (Mac) or `diagnostic.bat` (Windows) and run when issues occur.

---

## 🔄 Standard Recovery Procedure

When in doubt, follow these steps in order:

```bash
# Step 1: Verify Node version
node -v  # Must be 22.20.0

# Step 2: Pull latest code
git status
git pull origin main

# Step 3: Clean install
rm -rf node_modules
npm cache clean --force
npm install

# Step 4: Clear Expo cache
npx expo start --clear

# Step 5: Test
npm run check
```

If still broken, check specific issue sections above.

---

## 📞 Emergency Recovery

**Nuclear option - complete reset:**

```bash
# WARNING: This will delete local changes!

# 1. Save your .env file somewhere safe
cp .env ~/.env_backup  # Mac
copy .env %USERPROFILE%\.env_backup  # Windows

# 2. Delete everything
rm -rf node_modules .expo .git
git clone <your-repo-url> CheckMe-fresh
cd CheckMe-fresh

# 3. Restore .env
cp ~/.env_backup .env  # Mac
copy %USERPROFILE%\.env_backup .env  # Windows

# 4. Fresh setup
nvm use
npm install
npx expo start --clear
```

Use only as last resort!

---

## 🎓 Pro Tips for Smooth Cross-Platform Development

### **1. Use Consistent Tools**

**Both Machines:**
- Same Node.js version (via `.nvmrc`)
- Same code editor (VSCode recommended)
- Same terminal (Git Bash on Windows, zsh/bash on Mac)
- Same Git config

### **2. Daily Routine**

**Start of day:**
```bash
./sync.sh  # or sync.bat
# Pulls code, installs deps, starts Expo
```

**End of day:**
```bash
git add .
git commit -m "feat: descriptive message"
git push origin main
```

### **3. Use Scripts in package.json**

```bash
npm run sync      # Pull + install
npm run check     # Verify setup
npm run dev       # Start Expo
npm run clear     # Clear cache + start
```

### **4. Keep a Changelog**

Create `DEVELOPMENT.md`:
```markdown
# Development Log

## 2025-01-15 (MacBook - Office)
- Added user profile screen
- Fixed drawer navigation bug
- Updated dependencies

## 2025-01-15 (Windows - Home)
- Continued profile screen
- Added settings page
- Ready for sprint review
```

---

## ✅ Cross-Platform Success Checklist

You know everything is working correctly when:

- [ ] Same Node.js version on both machines (`node -v`)
- [ ] Git shows no unexpected changes (`git status`)
- [ ] `npm install` runs without errors
- [ ] `.env` file exists with correct values
- [ ] Expo starts without errors (`npx expo start`)
- [ ] App runs on Android (phone OR emulator)
- [ ] Can switch machines and continue work seamlessly

---

**Remember: 99% of cross-platform issues come from version mismatches. Keep Node.js, npm, and dependencies in sync, and you'll be fine! 🎯**