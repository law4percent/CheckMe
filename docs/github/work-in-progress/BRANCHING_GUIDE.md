# 🔄 Creating and Switching Branches Between Windows and MacBook

## Overview

This guide shows you how to create a branch on Windows (Home) and continue working on it using your MacBook (Office), or vice versa.

---

## 1️⃣ On Windows (Home PC)

### **Step 1: Navigate to Project Folder**

```bash
cd C:\Users\Lawrence\Desktop\CheckMe\app\CheckMe
```

### **Step 2: Ensure Main Branch is Up-to-Date**

Before creating a new branch, make sure you have the latest code:

```bash
# Switch to main branch
git checkout main

# Pull latest changes from GitHub
git pull origin main
```

**Why?** This ensures your new branch starts from the latest codebase.

### **Step 3: Create a New Branch**

```bash
# Create and switch to new branch in one command
git checkout -b feature-login

# Alternative: Create branch with more descriptive name
git checkout -b feature/user-login
```

**Branch Naming Examples:**
- `feature-login` - Simple feature
- `feature/user-authentication` - Complex feature
- `bugfix/login-error` - Bug fix
- `wip/experimental-ui` - Experimental work

### **Step 4: Work on Your Changes**

Make your code changes, even if incomplete. It's okay!

```bash
# Check what files changed
git status

# Example output:
# modified: src/screens/LoginScreen.tsx
# new file: src/components/LoginForm.tsx
```

### **Step 5: Stage and Commit Your Work**

```bash
# Stage all changes
git add .

# Commit with clear message
git commit -m "WIP: started login feature - form layout only"
```

**More WIP Commit Examples:**
```bash
git commit -m "WIP: added login form - validation incomplete"
git commit -m "WIP: implementing Firebase auth - not tested"
git commit -m "WIP: half-done login screen - missing error handling"
```

### **Step 6: Push Branch to GitHub**

```bash
# Push your branch to GitHub
git push origin feature-login

# If this is the first push of this branch, you might see:
# "The upstream branch 'feature-login' doesn't exist"
# Git will suggest a command - just follow it, or use:
git push --set-upstream origin feature-login
```

**What Happens:**
- Your branch is now on GitHub
- Your work is backed up
- You can access it from any machine

✅ **Your work is now safely stored on GitHub!**

---

## 2️⃣ On MacBook (Office PC)

### **Option A: If Project Already Exists on MacBook**

#### **Step 1: Navigate to Project**

```bash
cd ~/Projects/CheckMe
# Or wherever you cloned the project
```

#### **Step 2: Fetch All Branches**

```bash
# Download info about all branches from GitHub
git fetch origin

# View all available branches
git branch -a
```

**Expected Output:**
```
* main
  remotes/origin/main
  remotes/origin/feature-login  ← Your branch from Windows!
```

#### **Step 3: Checkout Your Branch**

```bash
# Switch to the branch you created on Windows
git checkout feature-login
```

**Alternative:**
```bash
# If the branch doesn't exist locally yet
git checkout -b feature-login origin/feature-login
```

#### **Step 4: Continue Working**

Your code is exactly as you left it on Windows! Continue working:

```bash
# Check current status
git status

# Make changes...
# Edit files, add features, fix bugs

# Stage changes
git add .

# Commit
git commit -m "feat: completed login form with validation"

# Push to GitHub
git push origin feature-login
```

---

### **Option B: If Project Doesn't Exist on MacBook**

#### **Step 1: Clone Repository**

```bash
# Clone using SSH (recommended)
git clone git@github.com:law4percent/CheckMe.git
cd CheckMe

# Or clone using HTTPS
git clone https://github.com/law4percent/CheckMe.git
cd CheckMe
```

#### **Step 2: Fetch and Checkout Branch**

```bash
# Fetch all branches
git fetch origin

# Checkout your branch
git checkout feature-login

# Verify you're on the right branch
git branch
# Output: * feature-login
```

#### **Step 3: Install Dependencies**

```bash
# Use correct Node version
nvm use

# Install dependencies
npm install

# Start working!
```

---

## 🔄 Complete Workflow Example

### **Scenario: Building Login Feature**

#### **Day 1 - Evening at Home (Windows)**

```bash
# 8:00 PM - Start new feature
cd C:\Users\Lawrence\Desktop\CheckMe\app\CheckMe
git checkout main
git pull origin main
git checkout -b feature/user-login

# Work for 2 hours...
# Create LoginScreen.tsx, add form fields

# 10:00 PM - Time to sleep
git add .
git commit -m "WIP: created login screen with email/password fields"
git push origin feature/user-login

# ✅ Work saved to GitHub
```

#### **Day 2 - Morning at Office (MacBook)**

```bash
# 9:00 AM - Arrive at office
cd ~/Projects/CheckMe
git fetch origin
git checkout feature/user-login
git pull origin feature/user-login

# Verify Node version
nvm use
node -v  # Should be v22.20.0

# Update dependencies if needed
npm install

# Continue working...
# Add validation, connect to Firebase

# 12:00 PM - Feature complete!
git add .
git commit -m "feat: completed login with Firebase authentication"
git push origin feature/user-login

# Create Pull Request on GitHub
# Review and merge to main ✅
```

#### **Day 2 - Evening at Home (Windows)**

```bash
# Pull latest changes (including your merged feature)
git checkout main
git pull origin main

# Start new feature
git checkout -b feature/user-profile
# ... continue cycle
```

---

## ✅ Important Notes

### **1. Always Push Before Switching Machines**

```bash
# Before leaving home/office:
git add .
git commit -m "WIP: [what you did]"
git push origin [branch-name]

# Verify push succeeded:
git status
# Should say: "Your branch is up to date with 'origin/branch-name'"
```

### **2. Always Pull When Starting Work**

```bash
# When arriving at other location:
git fetch origin
git checkout [branch-name]
git pull origin [branch-name]

# This ensures you have the latest code
```

### **3. Use WIP Commits for Incomplete Work**

**Good WIP commits:**
```bash
✅ "WIP: started profile screen - layout only"
✅ "WIP: added validation - needs testing"
✅ "WIP: half-done Firebase integration"
```

**Bad commits (avoid):**
```bash
❌ "update"
❌ "changes"
❌ "fix"
```

### **4. Never Commit Secrets**

**❌ Never commit:**
- `.env` with real credentials
- API keys
- Passwords
- `google-services.json` with production keys

**✅ Safe to commit:**
- `.env.example` (template)
- Source code
- Config files
- Documentation

### **5. Keep Node Versions Consistent**

```bash
# On both machines:
node -v
# Should show: v22.20.0

# If different, switch:
nvm use  # Reads from .nvmrc
```

---

## 🎯 Quick Reference Commands

### **Starting Work (Either Machine)**

```bash
# Update main
git checkout main
git pull origin main

# Create new branch
git checkout -b feature/my-feature

# Or switch to existing branch
git checkout feature/my-feature
git pull origin feature/my-feature
```

### **Saving Work (Either Machine)**

```bash
# Stage all changes
git add .

# Commit with message
git commit -m "WIP: description of work"

# Push to GitHub
git push origin feature/my-feature
```

### **Switching Machines**

```bash
# On new machine:
git fetch origin
git checkout feature/my-feature
git pull origin feature/my-feature
nvm use
npm install
```

---

## 🐛 Troubleshooting

### **Issue 1: Branch Doesn't Exist on Other Machine**

**Problem:**
```bash
git checkout feature-login
# error: pathspec 'feature-login' did not match any file(s) known to git
```

**Solution:**
```bash
# Make sure you fetched from GitHub
git fetch origin

# Then checkout
git checkout feature-login

# Or explicitly:
git checkout -b feature-login origin/feature-login
```

---

### **Issue 2: Forgot to Push on Previous Machine**

**Problem:** Branch exists on Windows but not on GitHub. Can't access from MacBook.

**Solution:**
```bash
# Unfortunately, can't recover unless you pushed
# Go back to Windows and push:
git push origin feature-login

# Prevention: Always push before leaving!
```

---

### **Issue 3: Changes Conflict Between Machines**

**Problem:** Made changes on both machines without pulling first.

**Solution:**
```bash
# Try to pull
git pull origin feature-login

# If conflicts occur:
# 1. Git will mark conflicted files
# 2. Open files and resolve conflicts
# 3. Look for markers:
#    <<<<<<< HEAD
#    Your changes
#    =======
#    Other changes
#    >>>>>>>

# 4. Edit to keep correct code
# 5. Stage resolved files
git add .

# 6. Commit merge
git commit -m "fix: resolved merge conflicts"

# 7. Push
git push origin feature-login
```

---

### **Issue 4: Different Results on Different Machines**

**Problem:** Code works on Windows but breaks on Mac (or vice versa).

**Possible Causes:**
1. Different Node versions
2. Different dependencies
3. Different environment variables

**Solution:**
```bash
# Check Node version (must match)
node -v  # Should be v22.20.0 on both

# If different:
nvm use

# Check dependencies
npm list --depth=0

# If outdated:
rm -rf node_modules
npm install

# Check environment variables
cat .env  # Mac
type .env  # Windows
```

---

## 📊 Workflow Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    GitHub Repository                     │
│                  (Remote/Cloud Storage)                  │
└──────────────────────────────────────────────────────────┘
            ▲                                ▲
            │                                │
            │ git push                       │ git push
            │                                │
            │                                │
   ┌────────┴────────┐              ┌────────┴────────┐
   │  Windows (Home) │              │ MacBook (Office)│
   │                 │              │                 │
   │  feature-login  │◄────────────►│  feature-login  │
   │                 │  git pull    │                 │
   └─────────────────┘              └─────────────────┘
```

---

## ✅ Best Practices Summary

### **Before Leaving Any Machine:**

1. ✅ Commit all changes
2. ✅ Push to GitHub
3. ✅ Verify push succeeded
4. ✅ Check no uncommitted files (`git status`)

### **When Arriving at Other Machine:**

1. ✅ Fetch from GitHub (`git fetch origin`)
2. ✅ Checkout branch (`git checkout branch-name`)
3. ✅ Pull latest changes (`git pull origin branch-name`)
4. ✅ Verify Node version (`node -v`)
5. ✅ Update dependencies if needed (`npm install`)

### **General Tips:**

- 🔄 Push often (every hour or before breaks)
- 📝 Use clear commit messages
- 🌿 Work on feature branches, not `main`
- 🔒 Never commit secrets
- 🧹 Clean up WIP commits before merging

---

## 🚀 You're Ready!

You can now freely switch between your Windows PC and MacBook while working on the same features. Your work is always safe on GitHub! 🎉

**Key Takeaway:** As long as you **commit and push** before switching machines, you can pick up exactly where you left off! ✨