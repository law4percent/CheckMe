# 🔄 Cross-Platform Work-In-Progress (WIP) Workflow

## Scenario: Unfinished Work Between Windows and MacBook

### 📋 The Question

**What if I create a branch on Windows at home, but I can't finish the task before I need to leave? The code is incomplete and has bugs. Should I still commit it? Then when I get to the office, can I continue working on that same branch using my MacBook?**

---

## ✅ Yes, This Is Completely Normal and Safe!

This is a **very common scenario** in professional software development. Git is specifically designed to handle this workflow. Here's how to do it properly:

---

## 🎯 Best Practice Workflow

### **Step 1: At Home (Windows) - Before Leaving**

Even though your code is unfinished and buggy, you should commit and push it. Here's how:

```bash
# 1. Check current status
git status

# 2. Stage all changes
git add .

# 3. Commit with clear WIP message
git commit -m "WIP: started user profile feature - incomplete"

# 4. Push to GitHub
git push origin feature/user-profile

# Note: Replace 'feature/user-profile' with your actual branch name
```

#### **Why Commit Unfinished Work?**

✅ **Prevents data loss** - Your work is backed up on GitHub  
✅ **Enables continuation** - You can pick up where you left off on any machine  
✅ **Tracks progress** - You have a history of what you were working on  
✅ **Safe experimentation** - If something breaks, you can always revert  

---

### **Step 2: At Office (MacBook) - Next Day**

When you arrive at the office, continue your work:

```bash
# 1. Make sure you're in the project directory
cd CheckMe

# 2. Fetch all remote branches
git fetch origin

# 3. Switch to your WIP branch
git checkout feature/user-profile

# 4. Verify you're on the right branch
git branch
# Should show: * feature/user-profile

# 5. Pull latest changes (in case you pushed updates from another device)
git pull origin feature/user-profile

# 6. Continue working...
# Your code is exactly as you left it on Windows!
```

---

## 📝 WIP Commit Message Guidelines

### **Good WIP Commit Messages:**

```bash
✅ git commit -m "WIP: started authentication flow - login screen only"
✅ git commit -m "WIP: added Firebase integration - not tested yet"
✅ git commit -m "WIP: half-done profile screen - missing validation"
✅ git commit -m "WIP: refactoring auth service - breaking changes"
```

### **Why These Are Good:**

1. **"WIP:" prefix** - Immediately signals this is work-in-progress
2. **Describes what's done** - "started authentication flow"
3. **States what's missing** - "login screen only", "not tested yet"
4. **Honest about status** - "breaking changes", "missing validation"

### **Bad Commit Messages (Avoid):**

```bash
❌ git commit -m "update"
❌ git commit -m "fix"
❌ git commit -m "changes"
❌ git commit -m "asdfasdf"
```

---

## 🌿 Branch Naming Strategy for WIP

### **Option 1: Regular Feature Branch**

```bash
git checkout -b feature/user-profile
```

**Use when:**
- You plan to finish it soon
- It's a normal feature in progress
- You'll merge to main when done

### **Option 2: WIP Prefix Branch**

```bash
git checkout -b wip/user-profile-experiment
```

**Use when:**
- Highly experimental code
- Might be abandoned
- Major refactoring that might break things
- Long-term work (days/weeks)

### **Option 3: Personal Branch**

```bash
git checkout -b lawrence/profile-feature
```

**Use when:**
- Multiple developers working on same codebase
- Want to keep your experiments separate
- Team convention uses name prefixes

---

## 🔒 Security Considerations

### **⚠️ NEVER Commit Secrets in WIP Branches**

Even in WIP commits, **never include:**

```bash
❌ .env file with real credentials
❌ API keys
❌ Passwords
❌ Private tokens
❌ google-services.json with production keys
```

### **✅ Safe to Commit:**

```bash
✅ .env.example (template without real values)
✅ Source code files
✅ Configuration files
✅ Test data
✅ Documentation
```

---

## 🔄 Complete Cross-Platform WIP Workflow

### **Scenario Timeline:**

#### **Day 1 - Evening at Home (Windows)**

```bash
# 9:00 PM - Start new feature
git checkout -b feature/user-settings
# ... coding for 2 hours ...

# 11:00 PM - Need to sleep, but not finished
git add .
git commit -m "WIP: started user settings screen - form validation incomplete"
git push origin feature/user-settings

# Go to bed 😴
```

#### **Day 2 - Morning at Office (MacBook)**

```bash
# 9:00 AM - Arrive at office
cd CheckMe
git fetch origin
git checkout feature/user-settings
git pull origin feature/user-settings

# Continue working...
# ... coding for 3 hours ...

# 12:00 PM - Feature complete!
git add .
git commit -m "feat: completed user settings screen with validation"
git push origin feature/user-settings

# Create Pull Request on GitHub
# Merge to main after review ✅
```

---

## 🎯 Advanced Tips

### **1. Stash vs Commit**

**Use Stash (Temporary, Local Only):**
```bash
# Quick save without commit
git stash save "WIP: half-done feature"

# On another machine - WON'T WORK!
# Stash is local only ❌
```

**Use Commit (Permanent, Can Push):**
```bash
# Save with commit
git commit -m "WIP: half-done feature"
git push origin branch-name

# On another machine - WORKS! ✅
```

**Recommendation:** Always **commit and push** for cross-machine work. Use stash only for quick temporary saves on the same machine.

### **2. Amending WIP Commits**

If you want to clean up WIP commits before merging:

```bash
# After feature is done, squash all WIP commits
git rebase -i HEAD~5  # Last 5 commits

# In the editor, change 'pick' to 'squash' for WIP commits
# This combines them into one clean commit
```

### **3. Viewing WIP Branches**

```bash
# List all WIP branches
git branch --all | grep -i wip

# Or on Windows (PowerShell):
git branch --all | Select-String "wip"
```

---

## ✅ Checklist: Before Leaving Home/Office

### **Before Switching Machines:**

- [ ] All changes committed (`git status` shows clean)
- [ ] Branch pushed to GitHub (`git push origin branch-name`)
- [ ] Commit message includes "WIP:" if unfinished
- [ ] No secrets or `.env` files committed
- [ ] Verified push succeeded (check GitHub)

### **When Switching to Other Machine:**

- [ ] Fetched latest changes (`git fetch origin`)
- [ ] Checked out correct branch (`git checkout branch-name`)
- [ ] Pulled latest commits (`git pull origin branch-name`)
- [ ] Verified Node version matches (`node -v` → v22.20.0)
- [ ] Dependencies updated (`npm install`)

---

## 🐛 Common Issues & Solutions

### **Issue 1: Forgot to Push Before Leaving**

**Problem:** You committed on Windows but forgot to push. Now at office, branch doesn't exist on MacBook.

**Solution:**
```bash
# Can't recover unless you pushed
# Lesson: Always push before leaving!

# Prevention: Create a habit
alias gp='git push origin $(git branch --show-current)'
# Now just type: gp
```

### **Issue 2: Merge Conflicts Between Machines**

**Problem:** You worked on both machines and forgot to pull first.

**Solution:**
```bash
# Pull and resolve conflicts
git pull origin branch-name

# If conflicts:
# 1. Open conflicted files
# 2. Edit and resolve
# 3. Stage resolved files
git add .
git commit -m "fix: resolved merge conflicts"
git push origin branch-name
```

### **Issue 3: Different Node Versions**

**Problem:** Code works on Windows but breaks on Mac due to different Node versions.

**Solution:**
```bash
# On both machines:
nvm use  # Uses version from .nvmrc (22.20.0)

# Always verify before working:
node -v  # Should match on both machines
```

---

## 📊 Comparison: Different Approaches

| Approach | Pros | Cons | Recommended? |
|----------|------|------|--------------|
| **Commit WIP** | ✅ Safe, trackable, works cross-machine | ❌ Cluttered history | ✅ **Yes** |
| **Stash Only** | ✅ Clean, no commit | ❌ Local only, can't access from other machine | ❌ No |
| **Don't Save** | ✅ Clean history | ❌ Lose all work if something breaks | ❌ Never |
| **Wait Until Done** | ✅ Clean commit | ❌ Can't switch machines, risk data loss | ❌ No |

---

## 🎓 Professional Best Practices

### **What Professional Developers Do:**

1. ✅ **Commit WIP frequently** - Every 30 mins to 1 hour
2. ✅ **Push to remote often** - At least before switching machines
3. ✅ **Use descriptive messages** - Clear "WIP:" prefix
4. ✅ **Create feature branches** - Never commit WIP directly to `main`
5. ✅ **Squash before merging** - Clean up WIP commits into one final commit
6. ✅ **Code review** - Get feedback before merging to `main`

### **Example Professional Workflow:**

```bash
# Start feature
git checkout -b feature/new-dashboard

# Work for 30 mins
git add .
git commit -m "WIP: added dashboard layout"
git push origin feature/new-dashboard

# Work another hour
git add .
git commit -m "WIP: added chart components - not connected yet"
git push origin feature/new-dashboard

# Next day, feature complete
git add .
git commit -m "feat: completed interactive dashboard with charts"
git push origin feature/new-dashboard

# Squash all commits before merging
git rebase -i HEAD~3  # Combine 3 commits into 1

# Final clean commit:
# "feat: add interactive dashboard with real-time charts"
```

---

## ✅ Summary

### **Yes, It's Perfectly Okay to:**

✅ Commit unfinished/buggy code to a feature branch  
✅ Push WIP commits to GitHub  
✅ Continue work on a different machine  
✅ Have multiple WIP commits before finishing  

### **Just Remember To:**

🔒 Never commit secrets or `.env` files  
📝 Use clear "WIP:" commit messages  
🌿 Work on a feature branch, not `main`  
🔄 Always push before switching machines  
🧹 Clean up WIP commits before merging (optional)  

---

## 🚀 Your CheckMe Workflow

### **Example: Adding User Profile Feature**

**At Home (Windows):**
```bash
git checkout -b feature/user-profile
# ... code for 2 hours ...
git add .
git commit -m "WIP: started user profile - avatar upload incomplete"
git push origin feature/user-profile
```

**At Office (MacBook):**
```bash
git fetch origin
git checkout feature/user-profile
git pull origin feature/user-profile
# ... finish the feature ...
git add .
git commit -m "feat: completed user profile with avatar upload"
git push origin feature/user-profile
# Create PR and merge to main ✅
```

---

## 📞 Quick Reference Commands

### **Before Leaving (Either Machine):**
```bash
git add .
git commit -m "WIP: [description of what's done]"
git push origin [branch-name]
```

### **When Arriving (Other Machine):**
```bash
cd CheckMe
git fetch origin
git checkout [branch-name]
git pull origin [branch-name]
nvm use
npm install
```

### **When Feature Complete:**
```bash
git add .
git commit -m "feat: [complete feature description]"
git push origin [branch-name]
# Create Pull Request on GitHub
```

---

**This is the standard way developers work across multiple machines. You're doing it right! 🎉**