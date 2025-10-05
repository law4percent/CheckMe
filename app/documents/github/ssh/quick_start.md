# 🚀 CheckMe - Quick Start Guide

## ⚡ Fast Setup (5 Minutes)

### 0️⃣ Set Up SSH (First Time Only - Highly Recommended)

**Why SSH?** No password prompts when pushing code!

**MacBook:**
```bash
ssh-keygen -t ed25519 -C "lawrence7roble@gmail.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub  # Copy this
```

**Windows:**
```bash
ssh-keygen -t ed25519 -C "lawrence7roble@gmail.com"
eval "$(ssh-agent -s)"  # Git Bash
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub  # Copy this
```

**Add to GitHub:**
1. Go to: https://github.com/settings/keys
2. Click "New SSH key"
3. Title: "MacBook Office" or "Windows PC Home"
4. Paste key → Add

**Test:**
```bash
ssh -T git@github.com
# Should say: "Hi law4percent! ..."
```

See **SSH Setup Guide** for detailed instructions.

### 1️⃣ Create Project

```bash
# Using SSH (recommended):
git clone git@github.com:law4percent/CheckMe.git
cd CheckMe

# Or using HTTPS:
# git clone https://github.com/law4percent/CheckMe.git
# cd CheckMe
```

### 2️⃣ Install Dependencies
```bash
npm install firebase @react-navigation/native @react-navigation/drawer @react-navigation/native-stack @react-native-async-storage/async-storage

npx expo install react-native-gesture-handler react-native-reanimated react-native-screens react-native-safe-area-context
```

### 3️⃣ Create Files
Copy all artifacts to your project:

**Root Directory:**
- `.env` ✅ (Credentials already filled!)
- `.env.example`
- `.gitignore`
- `google-services.json` ✅ (Pre-configured!)
- `env.d.ts`
- `app.json` ✅ (Package name set!)
- `App.tsx`
- `babel.config.js` (update with Reanimated plugin)

**Create `src/` folders:**
```bash
mkdir -p src/config src/types src/services src/components src/screens src/navigation
```

**Add source files to `src/`:**
- `config/firebase.config.ts` ✅ (Reads from .env!)
- `config/theme.ts`
- `types/types.ts`
- `services/authService.ts`
- `components/CustomDrawer.tsx`
- `screens/SignUpScreen.tsx`
- `screens/LoginScreen.tsx`
- `screens/DashboardScreen.tsx`
- `navigation/Navigation.tsx`

### 4️⃣ Configure Firebase (2 minutes)
1. Open [Firebase Console](https://console.firebase.google.com/)
2. Find project: **CheckMe-1c2df**
3. Enable **Authentication** → Email/Password
4. Create **Realtime Database** → asia-southeast1
5. Set **Database Rules** (copy from artifact)

### 5️⃣ Run App
```bash
npx expo start
```

**Press:**
- `a` = Android
- `i` = iOS
- `w` = Web
- `r` = Reload

---

## 📱 Your Firebase Details

✅ **All credentials are pre-configured in `.env`**

- **Project ID**: `CheckMe-1c2df`
- **Package Name**: `com.mr_itnology.chick_up`
- **Database**: `https://CheckMe-1c2df-default-rtdb.asia-southeast1.firebasedatabase.app`
- **Region**: Asia Southeast 1 (Singapore)

---

## 🎨 App Features

✅ **Authentication**
- Sign up with username, email, phone, password
- Login with username + password
- Auto-redirect after sign up/login
- Secure logout

✅ **Navigation**
- Left-side drawer (swipe right to open)
- Dashboard, Profile, Settings screens
- Smooth animations

✅ **Design**
- Yellow & Green theme
- Clean, modern UI
- TypeScript for safety

---

## 🔒 Security Checklist

- [ ] `.env` file created (DO NOT commit!)
- [ ] `.gitignore` includes `.env`
- [ ] Firebase Authentication enabled
- [ ] Database rules set properly
- [ ] `google-services.json` in root

---

## 🧪 Test the App

### 1. Sign Up
```
Username: testuser
Phone: +639123456789
Email: test@example.com
Password: test123456
```

### 2. Login
```
Username: testuser
Password: test123456
```

### 3. Navigate
- Swipe right from left edge → Drawer opens
- Tap menu items
- Tap Logout

---

## 📝 Common Commands

```bash
# Start development
npx expo start

# Clear cache
npx expo start --clear

# Install packages
npx expo install package-name

# Check for issues
npx expo-doctor

# Build for Android
eas build --platform android --profile preview
```

---

## 🐛 Troubleshooting

**Problem**: Firebase not connecting
- ✅ Check `.env` file exists in root
- ✅ Restart expo: `npx expo start --clear`
- ✅ Verify Firebase Authentication is enabled

**Problem**: Drawer not opening
- ✅ Ensure `react-native-gesture-handler` is imported first in `App.tsx`
- ✅ Wrapped with `<GestureHandlerRootView>`
- ✅ Restart: `npx expo start --clear`

**Problem**: Environment variables not working
- ✅ File must be named exactly `.env` (not `.env.txt`)
- ✅ Variables start with `EXPO_PUBLIC_`
- ✅ Restart Expo after changing .env
- ✅ Clear cache: `npx expo start --clear`

**Problem**: TypeScript errors
- ✅ Run `npm install` to update dependencies
- ✅ Check `env.d.ts` file exists
- ✅ Restart TypeScript server in your IDE

**Problem**: Build fails
```bash
rm -rf node_modules
npm install
npx expo start --clear
```

---

## 📂 File Checklist

Make sure you have these files:

### Root Directory
- [ ] `.env` (with your Firebase credentials)
- [ ] `.env.example`
- [ ] `.gitignore`
- [ ] `google-services.json`
- [ ] `env.d.ts`
- [ ] `App.tsx`
- [ ] `app.json`
- [ ] `babel.config.js` (with Reanimated plugin)
- [ ] `package.json`
- [ ] `tsconfig.json`

### src/config/
- [ ] `firebase.config.ts`
- [ ] `theme.ts`

### src/types/
- [ ] `types.ts`

### src/services/
- [ ] `authService.ts`

### src/components/
- [ ] `CustomDrawer.tsx`

### src/screens/
- [ ] `SignUpScreen.tsx`
- [ ] `LoginScreen.tsx`
- [ ] `DashboardScreen.tsx`

### src/navigation/
- [ ] `Navigation.tsx`

---

## 🎯 Next Development Steps

### Phase 1: Core Features ✅ (DONE)
- [x] Firebase setup
- [x] Authentication (Sign Up/Login)
- [x] Left drawer navigation
- [x] Dashboard screen

### Phase 2: User Features (Next Sprint)
- [ ] Profile screen (view/edit user data)
- [ ] Settings screen (app preferences)
- [ ] Password reset functionality
- [ ] Avatar/profile picture upload

### Phase 3: Main Features (Your App Logic)
- [ ] Add your core business features
- [ ] Data management screens
- [ ] User interactions
- [ ] Notifications

### Phase 4: Polish
- [ ] Loading states & animations
- [ ] Error handling improvements
- [ ] Offline support
- [ ] Performance optimization

---

## 💡 Pro Tips

### Development
```bash
# Use Expo Go app on your phone for quick testing
# Download from Play Store: "Expo Go"
# Scan QR code from terminal

# Or use Android emulator
npx expo start --android
```

### Environment Variables
```bash
# Access in code:
process.env.EXPO_PUBLIC_YOUR_VAR

# Must start with EXPO_PUBLIC_ to be accessible in app
# Private keys (without EXPO_PUBLIC_) only work in Node.js/server code
```

### Git Workflow
```bash
# Initialize git (if not done)
git init

# First commit
git add .
git commit -m "Initial CheckMe setup with Firebase"

# Create repository on GitHub
# Then push
git remote add origin your-repo-url
git push -u origin main
```

### Debugging
```bash
# View logs
npx expo start

# Then in terminal, press:
# j - Open debugger
# m - Toggle menu
# r - Reload
# shift+m - More tools
```

---

## 🔥 Firebase Console Quick Links

After logging into [Firebase Console](https://console.firebase.google.com/):

1. **Authentication**: Monitor users, disable accounts
2. **Realtime Database**: View/edit data in real-time
3. **Usage**: Check quota and limits
4. **Project Settings**: Get configs, manage API keys

**Your Database Structure:**
```
CheckMe-1c2df-default-rtdb
├── users/
│   └── {uid}/
│       ├── username
│       ├── email
│       ├── phoneNumber
│       ├── createdAt
│       └── updatedAt
└── usernames/
    └── {username}/
        └── email
```

---

## 🚀 Ready to Build!

Your CheckMe project is fully configured and ready to go! 🐣

**Start developing:**
```bash
npx expo start
```

**Need help?** Check the full Setup Guide artifact for detailed instructions.

**Happy coding!** 🎉