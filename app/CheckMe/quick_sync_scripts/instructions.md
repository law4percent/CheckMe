# INSTRUCTIONS

**MacBook (Office):**
1. Save above script as: sync.sh
2. Make executable: chmod +x sync.sh
3. Run: ./sync.sh

**Windows (Home):**
1. Save above script as: sync.bat
2. Run: sync.bat

---

**Alternative: Add to package.json**

Add these scripts to your package.json:

```
"scripts": {
  "sync": "git pull origin main && npm install",
  "dev": "npx expo start",
  "dev:clear": "npx expo start --clear",
  "android": "npx expo start --android",
  "check": "node -v && npm -v && git status"
}
```

Then run: npm run sync && npm run dev