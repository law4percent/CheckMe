# 🖥️ Cross-Platform Development Guide
## MacBook (Office) ↔️ Windows PC (Home)

This guide ensures smooth development of CheckMe across your MacBook and Windows PC without compatibility issues.

---

## ✅ Why This Works (No Docker Needed)

### **Expo Abstracts Platform Differences**
- JavaScript runs the same everywhere
- Expo CLI is cross-platform
- Android builds work identically on Mac/Windows
- Metro bundler handles compilation

### **Single Target Platform (Android)**
- No iOS-specific code
- No Xcode dependency
- Android Studio works on both systems
- Expo Go app works the same

---

## 🔧 Initial Setup (Do Once on Each Machine)

### **1. Install Node.js (Same Version on Both)**

**MacBook (Office):**
```bash
# Install nvm (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install Node.js LTS
nvm install 22.20.0
nvm use 22.20.0
nvm alias default 22.20.0

# Verify
node -v  # Should show 22.20.0
npm -v
```

**Windows PC (Home):**
```bash
# Download and install nvm-windows from:
# https://github.com/coreybutler/nvm-windows/releases

# In PowerShell or Command Prompt:
nvm install 22.20.0
nvm use 22.20.0

# Verify
node -v  # Should show v22.20.0
npm -v
```

**Why NVM?**
- Easy to switch Node versions
- Ensures both machines use identical version
- Project has `.nvmrc` file for auto-detection

### **2. Install Git**

**MacBook:**
```bash
# Git usually pre-installed, verify:
git --version

# If not installed:
brew install git
```

**Windows:**
```bash
# Download from: https://git-scm.com/download/win
# During installation, select:
# - "Checkout as-is, commit Unix-style line endings"
# - "Use Git from the Windows Command Prompt"
```

### **2. Install Git**

**MacBook:**
```bash
# Git usually pre-installed, verify:
git --version

# If not installed:
brew install git
```

**Windows:**
```bash
# Download from: https://git-scm.com/download/win
# During installation, select:
# - "Checkout as-is, commit Unix-style line endings"
# - "Use Git from the Windows Command Prompt"
```

### **3. Configure Git (Same on Both)**

```bash
git config --global user.name "Your Name"
git config --global user.email "lawrence7roble@gmail.com"

# Line ending handling (CRITICAL for cross-platform)
git config --global core.autocrlf input   # On Mac
git config --global core.autocrlf true    # On Windows
```

### **4. Set Up SSH for GitHub (Recommended)**

Using SSH is more convenient than HTTPS as you won't need to enter credentials every time you push.

#### **Generate SSH Key (Do Once on Each Machine)**

**MacBook (Office):**
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "lawrence7roble@gmail.com"
# Press Enter for all prompts (use defaults)

# Start SSH agent
eval "$(ssh-agent -s)"

# Add key to agent
ssh-add ~/.ssh/id_ed25519

# Copy public key
cat ~/.ssh/id_ed25519.pub
# Copy the entire output
```

**Windows PC (Home):**

**Using Git Bash:**
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "lawrence7roble@gmail.com"
# Press Enter for all prompts

# Start SSH agent
eval "$(ssh-agent -s)"

# Add key to agent
ssh-add ~/.ssh/id_ed25519

# Copy public key
cat ~/.ssh/id_ed25519.pub
```

**Using PowerShell:**
```powershell
# Generate SSH key
ssh-keygen -t ed25519 -C "lawrence7roble@gmail.com"
# Press Enter for all prompts

# Start SSH agent
Start-Service ssh-agent

# Add key to agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519

# Copy public key
type $env:USERPROFILE\.ssh\id_ed25519.pub
```

#### **Add SSH Key to GitHub (Do for Each Machine)**

1. Go to GitHub: https://github.com/settings/keys
2. Click **New SSH key**
3. Add titles:
   - "MacBook Office" (for work machine)
   - "Windows PC Home" (for home machine)
4. Paste the public key (from previous step)
5. Click **Add SSH key**

#### **Configure Repository to Use SSH**

```bash
# Clone with SSH (new repository)
git clone git@github.com:law4percent/CheckMe.git

# Or update existing repository
cd CheckMe
git remote set-url origin git@github.com:law4percent/CheckMe.git

# Test connection
ssh -T git@github.com
# Should say: "Hi law4percent! You've successfully authenticated..."
```

#### **Benefits of SSH**

✅ No password prompts when pushing
✅ More secure than HTTPS
✅ Faster authentication
✅ Works seamlessly on both Mac and Windows

### **5. Install Android Studio (Only on Windows)**

**Windows PC (Home):**
1. Download from: https://developer.android.com/studio
2. Install Android Studio
3. Open Android Studio → More Actions → SDK Manager
4. Install:
   - Android SDK Platform 33 (or latest)
   - Android SDK Build-Tools
   - Android Emulator
5. Create an AVD (Android Virtual Device):
   - Tools → Device Manager → Create Device
   - Select Pixel 5 or similar
   - Choose system image (e.g., Android 13)

**MacBook (Office):**
- Not needed! You'll use your physical Android phone

### **5. Install Expo Go (On Android Phone)**

**On Your Android Phone (For Office Use):**
1. Open Google Play Store
2. Search "Expo Go"
3. Install app
4. Open it once to ensure it works

---

## 📂 Project Setup (First Time)

### **On MacBook (Office) - First Setup**

```bash
# Clone your repository (using SSH)
git clone git@github.com:law4percent/CheckMe.git
cd CheckMe

# Use correct Node version (reads from .nvmrc)
nvm use

# Install dependencies
npm install

# Copy environment file
cp .env.example .env
# Edit .env with your Firebase credentials

# Start Expo
npx expo start

# Scan QR code with Expo Go app on your phone
```

### **On Windows PC (Home) - First Setup**

```bash
# Clone your repository (using SSH)
git clone git@github.com:law4percent/CheckMe.git
cd CheckMe

# Use correct Node version
nvm use 22.20.0

# Install dependencies
npm install

# Copy environment file (if not in Git)
copy .env.example .env
# Edit .env with your Firebase credentials

# Start Expo
npx expo start

# Press 'a' to open in Android emulator
```

**Note**: If you already cloned with HTTPS, update the remote:
```bash
git remote set-url origin git@github.com:law4percent/CheckMe.git
```

---

## 🔄 Daily Workflow

### **Starting Work on MacBook (Office)**

```bash
cd CheckMe

# Make sure you're on correct Node version
nvm use

# Pull latest changes from home
git pull origin main

# Install any new dependencies
npm install

# Start development
npx expo start

# Scan QR code with phone
```

### **Starting Work on Windows PC (Home)**

```bash
cd CheckMe

# Make sure you're on correct Node version
nvm use 22.20.0

# Pull latest changes from office
git pull origin main

# Install any new dependencies
npm install

# Start Android emulator (open Android Studio first)
# Or use: npx expo start --android

# Start development
npx expo start

# Press 'a' for Android emulator
```

### **Ending Work Session (Either Machine)**

```bash
# Stage changes
git add .

# Commit with meaningful message
git commit -m "feat: add user profile screen"

# Push to GitHub
git push origin main

# Or push to feature branch
git push origin feature/user-profile
```

---

## 🎯 Best Practices

### **1. Always Commit package-lock.json**

**Why?** Ensures exact same dependency versions on both machines.

```bash
# Make sure package-lock.json is NOT in .gitignore
# Commit it every time dependencies change
git add package-lock.json
git commit -m "chore: update dependencies"
```

### **2. Use nvm to Switch Node Versions**

```bash
# The .nvmrc file tells nvm which version to use
# On Mac:
nvm use

# On Windows:
nvm use 22.20.0
```

### **3. Clean Install When Switching Machines**

If you get weird errors after pulling changes:

```bash
# Delete node_modules
rm -rf node_modules  # Mac
# or
rmdir /s node_modules  # Windows

# Clean npm cache
npm cache clean --force

# Fresh install
npm install

# Clear Expo cache
npx expo start --clear
```

### **4. Never Commit These Files**

Your `.gitignore` is configured to exclude:
- `node_modules/`
- `.env` (secrets)
- `.expo/` (cache)
- `.DS_Store` (Mac)
- `Thumbs.db` (Windows)
- `android/` and `ios/` (generated folders)

### **5. Handle Line Endings Properly**

**Already configured via `.gitattributes`:**
- Source files (`.js`, `.ts`, `.tsx`) → LF (Unix style)
- Config files → LF
- Windows scripts (`.bat`, `.cmd`) → CRLF

Git will auto-convert based on your system.

### **6. Use Consistent Scripts**

In `package.json`, these scripts work on both platforms:

```json
{
  "scripts": {
    "start": "npx expo start",
    "android": "npx expo start --android",
    "ios": "npx expo start --ios",
    "web": "npx expo start --web",
    "clear": "npx expo start --clear"
  }
}
```

---

## 🐛 Common Issues & Solutions

### **Issue: Different Node Versions**

**Symptoms:**
- "Module not found" errors
- Unexpected behavior after switching machines

**Solution:**
```bash
# Check version
node -v

# Should be v22.20.0 on both machines
# If not:
nvm use 22.20.0  # Windows
nvm use          # Mac (reads .nvmrc)
```

---

### **Issue: Line Ending Conflicts**

**Symptoms:**
- Git shows changes even though you didn't edit files
- "CRLF will be replaced by LF" warnings

**Solution:**
```bash
# Already handled by .gitattributes
# But if issues persist:

# On Windows:
git config --global core.autocrlf true

# On Mac:
git config --global core.autocrlf input

# Then refresh repository:
git rm -rf --cached .
git reset --hard
```

---

### **Issue: npm install Takes Forever**

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Use npm ci for faster, cleaner install
npm ci
```

---

### **Issue: Expo Go Not Connecting (MacBook)**

**Symptoms:**
- QR code scan doesn't work
- "Unable to connect" error

**Solution:**
```bash
# Make sure phone and MacBook are on same WiFi
# Try tunnel mode:
npx expo start --tunnel

# Or use LAN mode explicitly:
npx expo start --lan
```

---

### **Issue: Android Emulator Slow (Windows)**

**Solution:**
```bash
# In Android Studio:
# Tools → AVD Manager → Edit AVD
# - Enable "Hardware - GLES 2.0"
# - Increase RAM to 4GB or more
# - Enable "Use Host GPU"

# Or use your phone remotely via USB:
# 1. Enable USB debugging on phone
# 2. Connect via USB
# 3. Run: npx expo start
# 4. Press 'a' to open on connected device
```

---

## 📋 Verification Checklist

Before switching machines, verify:

- [ ] All changes committed and pushed
- [ ] `package-lock.json` committed
- [ ] `.env` file backed up (NOT in Git)
- [ ] No uncommitted changes
- [ ] Dependencies are up to date

After switching machines, verify:

- [ ] Correct Node version (`node -v`)
- [ ] Latest code pulled (`git pull`)
- [ ] Dependencies installed (`npm install`)
- [ ] `.env` file exists with correct values
- [ ] App runs without errors (`npx expo start`)

---

## 🔐 Security Notes

### **Keep .env File Synced (Securely)**

**Option 1: Manual Copy (Simple)**
- Keep `.env` in password manager
- Copy manually to new machine

**Option 2: Encrypted Git Secret (Advanced)**
```bash
# Use git-crypt or similar
# Not recommended for beginners
```

**Option 3: Cloud Storage (Careful)**
- Store in secure cloud (1Password, LastPass, etc.)
- Never in regular cloud storage!

---

## 🎓 Pro Tips

### **1. Use Feature Branches**

```bash
# Start new feature
git checkout -b feature/user-settings

# Work on it...
git add .
git commit -m "feat: add settings screen"

# Push feature branch
git push origin feature/user-settings

# Switch machines, continue working:
git checkout feature/user-settings
git pull origin feature/user-settings

# When done, merge to main
git checkout main
git merge feature/user-settings
```

### **2. Use Git Aliases for Faster Workflow**

```bash
# Add to Git config
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.pl pull
git config --global alias.ps push

# Now use short commands:
git co main
git br feature/new-thing
git ci -m "message"
git st
```

### **3. Quick Sync Script**

Create `sync.sh` (Mac) or `sync.bat` (Windows):

**Mac (sync.sh):**
```bash
#!/bin/bash
echo "Syncing CheckMe..."
nvm use
git pull origin main
npm install
echo "✅ Ready to develop!"
npx expo start
```

**Windows (sync.bat):**
```batch
@echo off
echo Syncing CheckMe...
nvm use 22.20.0
git pull origin main
npm install
echo ✅ Ready to develop!
npx expo start
```

---

## 📊 Summary Table

| Aspect | MacBook (Office) | Windows PC (Home) | Solution |
|--------|------------------|-------------------|----------|
| **Node.js** | v22.20.0 (nvm) | v22.20.0 (nvm-windows) | `.nvmrc` file |
| **Git** | Pre-installed | Git for Windows | `.gitattributes` |
| **Testing** | Phone (Expo Go) | Android Emulator | Both work identically |
| **Line Endings** | LF | CRLF | Git auto-converts |
| **Dependencies** | npm install | npm install | `package-lock.json` in Git |
| **Environment** | .env (manual) | .env (manual) | Keep synced securely |

---

## ✅ Final Checklist

You're ready for cross-platform development when:

- [x] Same Node.js version on both machines
- [x] Git configured correctly on both
- [x] `.gitignore` and `.gitattributes` in project
- [x] `.nvmrc` file in project root
- [x] `package-lock.json` committed to Git
- [x] Android testing method ready (phone + emulator)
- [x] `.env` file available on both machines
- [x] First successful sync test completed