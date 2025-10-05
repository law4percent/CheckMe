# Firebase Auth Persistence in Expo Go - Complete Solution

## The Problem

When using Firebase v12+ with Expo Go, you encounter two related issues:

1. **TypeScript Error:**
   ```
   Module '"firebase/auth"' has no exported member 'getReactNativePersistence'
   ```

2. **Runtime Warning:**
   ```
   @firebase/auth: Auth (12.3.0): You are initializing Firebase Auth for React Native 
   without providing AsyncStorage. Auth state will default to memory persistence and 
   will not persist between sessions.
   ```

**Root Cause:** Firebase v12+ doesn't properly export `getReactNativePersistence` in its type definitions for React Native environments, even though it's needed for AsyncStorage persistence.

---

## The Solution

Create a custom implementation of `getReactNativePersistence` that provides proper TypeScript types and wraps AsyncStorage correctly.

---

## Implementation Steps

### Step 1: Create Type Definitions File

**File:** `src/lib/reactNativeAsyncStorageTypes.ts`

```typescript
// src/lib/reactNativeAsyncStorageTypes.ts

// Define the base Persistence interface to match Firebase auth expectations
export interface Persistence {
  readonly type: "SESSION" | "LOCAL" | "NONE";
}

export const enum PersistenceType {
  SESSION = 'SESSION',
  LOCAL = 'LOCAL', 
  NONE = 'NONE'
}

export type PersistedBlob = Record<string, unknown>;
export type PersistenceValue = PersistedBlob | string;
export const STORAGE_AVAILABLE_KEY = '__sak';

export interface StorageEventListener {
  (value: PersistenceValue | null): void;
}

export interface PersistenceInternal extends Persistence {
  type: PersistenceType;
  _isAvailable(): Promise<boolean>;
  _set(key: string, value: PersistenceValue): Promise<void>;
  _get<T extends PersistenceValue>(key: string): Promise<T | null>;
  _remove(key: string): Promise<void>;
  _addListener(key: string, listener: StorageEventListener): void;
  _removeListener(key: string, listener: StorageEventListener): void;
  _shouldAllowMigration?: boolean;
}
```

**Important Notes:**
- Remove `"COOKIE"` from the type definition (Firebase React Native doesn't support it)
- This matches Firebase's internal Persistence interface

---

### Step 2: Create Persistence Implementation

**File:** `src/lib/reactNativeAsyncStorage.ts`

```typescript
// src/lib/reactNativeAsyncStorage.ts

// Define ReactNativeAsyncStorage interface locally
export interface ReactNativeAsyncStorage {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

import {
  Persistence,
  PersistenceInternal,
  PersistenceType,
  PersistenceValue,
  STORAGE_AVAILABLE_KEY,
  StorageEventListener
} from './reactNativeAsyncStorageTypes';

export function getReactNativePersistence(
  storage: ReactNativeAsyncStorage
): Persistence {
  return class implements PersistenceInternal {
    static type: 'LOCAL' = 'LOCAL';
    readonly type: PersistenceType = PersistenceType.LOCAL;

    async _isAvailable(): Promise<boolean> {
      try {
        if (!storage) return false;
        await storage.setItem(STORAGE_AVAILABLE_KEY, '1');
        await storage.removeItem(STORAGE_AVAILABLE_KEY);
        return true;
      } catch {
        return false;
      }
    }

    _set(key: string, value: PersistenceValue): Promise<void> {
      return storage.setItem(key, JSON.stringify(value));
    }

    async _get<T extends PersistenceValue>(key: string): Promise<T | null> {
      const json = await storage.getItem(key);
      return json ? JSON.parse(json) : null;
    }

    _remove(key: string): Promise<void> {
      return storage.removeItem(key);
    }

    _addListener(_key: string, _listener: StorageEventListener): void {
      // Listeners not supported for React Native storage
    }

    _removeListener(_key: string, _listener: StorageEventListener): void {
      // Listeners not supported for React Native storage  
    }
  };
}
```

---

### Step 3: Update Firebase Configuration

**File:** `src/config/firebase.config.ts`

```typescript
// src/config/firebase.config.ts
import { initializeApp } from 'firebase/app';
import { initializeAuth } from 'firebase/auth';
import { getDatabase } from 'firebase/database';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getReactNativePersistence } from '../lib/reactNativeAsyncStorage';

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  databaseURL: process.env.EXPO_PUBLIC_FIREBASE_DATABASE_URL,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

// Validate configuration
const requiredEnvVars = [
  'EXPO_PUBLIC_FIREBASE_API_KEY',
  'EXPO_PUBLIC_FIREBASE_PROJECT_ID',
  'EXPO_PUBLIC_FIREBASE_DATABASE_URL',
];

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
}

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth with AsyncStorage persistence (custom implementation)
const auth = initializeAuth(app, {
  persistence: getReactNativePersistence(AsyncStorage)
});

// Initialize Realtime Database
const database = getDatabase(app);

export { auth, database };
export default app;
```

---

### Step 4: Verify Dependencies

```bash
# Ensure you have the correct packages
npm install firebase
npx expo install @react-native-async-storage/async-storage

# Clear cache and restart
npx expo start -c
```

---

## Project Structure

After implementation, your project should have:

```
CheckMe/
├── src/
│   ├── lib/                                    ⭐ NEW
│   │   ├── reactNativeAsyncStorageTypes.ts    ⭐ Type definitions
│   │   └── reactNativeAsyncStorage.ts         ⭐ Implementation
│   ├── config/
│   │   ├── firebase.config.ts                  ✏️ Updated
│   │   └── theme.ts
│   ├── types/
│   ├── services/
│   │   └── authService.ts                      (uses Firebase JS SDK)
│   ├── components/
│   ├── screens/
│   └── navigation/
│       └── Navigation.tsx                       (uses Firebase JS SDK)
├── .env
├── App.tsx
└── package.json
```

---

## Results

After implementing this solution:

### Before
- TypeScript errors on `getReactNativePersistence`
- Firebase warning about AsyncStorage
- Users logged out after closing app
- Must use `@react-native-firebase` (no Expo Go support)

### After
- No TypeScript errors
- No Firebase warnings
- Users stay logged in between sessions
- Works perfectly with Expo Go
- Cross-platform compatible (Mac & Windows)

---

## Testing

1. **Login** to your app
2. **Close the app** completely (swipe away from recent apps)
3. **Reopen the app**
4. **Verify** you're still logged in

---

## Why This Works

1. **Firebase v12+ Issue:** The Firebase team hasn't properly exported `getReactNativePersistence` in the React Native environment's TypeScript definitions.

2. **Custom Implementation:** By creating our own implementation, we:
   - Provide correct TypeScript types
   - Wrap AsyncStorage properly
   - Match Firebase's internal Persistence interface
   - Avoid the TypeScript compilation error

3. **Expo Go Compatible:** This solution uses the Firebase JS SDK, which works with Expo Go. The `@react-native-firebase` alternative requires a custom development client.

---

## Alternative: @react-native-firebase

If you don't need Expo Go, you can use `@react-native-firebase` instead:

**Pros:**
- Built-in persistence (no custom code needed)
- Better native performance
- Automatic configuration

**Cons:**
- Cannot use Expo Go
- Requires custom development client
- More complex build process

**For Expo Go development, stick with this custom implementation.**

---

## Troubleshooting

### TypeScript still shows errors

```bash
# Clear TypeScript cache
rm -rf node_modules/.cache
npx expo start -c
```

### Warning still appears

Verify your imports:
```typescript
import { getReactNativePersistence } from '../lib/reactNativeAsyncStorage';
// NOT from 'firebase/auth' or 'firebase/auth/react-native'
```

### Persistence not working

Check that AsyncStorage is installed:
```bash
npm list @react-native-async-storage/async-storage
# Should show version 2.2.0 or higher
```

---

## Credits

This solution is based on [this Stack Overflow answer](https://stackoverflow.com/a/76943639/10500723) which addresses the Firebase v12+ TypeScript issue in React Native environments.

---

## Summary

1. **Problem:** Firebase v12+ doesn't export `getReactNativePersistence` properly for TypeScript
2. **Solution:** Create custom implementation with correct types
3. **Steps:**
   - Add `src/lib/reactNativeAsyncStorageTypes.ts`
   - Add `src/lib/reactNativeAsyncStorage.ts`
   - Update `firebase.config.ts` to use custom implementation
4. **Result:**
   - No TypeScript errors
   - Auth persists in Expo Go
   - Works cross-platform (Mac & Windows)

This is the correct approach for using Firebase Auth with persistence in Expo Go.