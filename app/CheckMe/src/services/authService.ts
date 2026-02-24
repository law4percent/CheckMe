// src/services/authService.ts
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  User
} from 'firebase/auth';
import { ref, set, get, update, remove } from 'firebase/database';
import { auth, database } from '../config/firebase';
import {
  TeacherSignUpData,
  TeacherLoginData,
  TeacherProfile,
  StudentSignUpData,
  StudentLoginData,
  StudentProfile,
  UserProfile
} from '../types';
import { isGmailAddress } from '../utils/validation';

// ─────────────────────────────────────────────
// Auth: Teacher
// ─────────────────────────────────────────────

export const createTeacherAccount = async (data: TeacherSignUpData): Promise<User> => {
  if (!isGmailAddress(data.email)) {
    throw new Error('Only Gmail addresses are allowed for registration');
  }

  try {
    const userCredential = await createUserWithEmailAndPassword(auth, data.email, data.password);
    const user = userCredential.user;

    const teacherProfile: Omit<TeacherProfile, 'uid'> = {
      fullName: data.fullName.trim(),
      email: data.email.toLowerCase().trim(),
      username: data.username.trim(),
      employeeId: data.employeeId.trim(),
      createdAt: Date.now(),
      role: 'teacher'
    };

    await set(ref(database, `users/teachers/${user.uid}`), {
      ...teacherProfile,
      uid: user.uid
    });

    return user;
  } catch (error: any) {
    if (error.code === 'auth/email-already-in-use') throw new Error('This email is already registered');
    if (error.code === 'auth/invalid-email') throw new Error('Invalid email address');
    if (error.code === 'auth/weak-password') throw new Error('Password is too weak');
    throw new Error(error.message || 'Failed to create account');
  }
};

// ─────────────────────────────────────────────
// Auth: Student
// ─────────────────────────────────────────────

export const createStudentAccount = async (data: StudentSignUpData): Promise<User> => {
  if (!isGmailAddress(data.email)) {
    throw new Error('Only Gmail addresses are allowed for registration');
  }

  try {
    const userCredential = await createUserWithEmailAndPassword(auth, data.email, data.password);
    const user = userCredential.user;
    const fullName = `${data.firstName.trim()} ${data.lastName.trim()}`;

    const studentProfile: Omit<StudentProfile, 'uid'> = {
      firstName: data.firstName.trim(),
      lastName: data.lastName.trim(),
      fullName,
      email: data.email.toLowerCase().trim(),
      username: data.username.trim(),
      studentId: data.studentId.trim(),
      createdAt: Date.now(),
      role: 'student'
    };

    await set(ref(database, `users/students/${user.uid}`), {
      ...studentProfile,
      uid: user.uid
    });

    return user;
  } catch (error: any) {
    if (error.code === 'auth/email-already-in-use') throw new Error('This email is already registered');
    if (error.code === 'auth/invalid-email') throw new Error('Invalid email address');
    if (error.code === 'auth/weak-password') throw new Error('Password is too weak');
    throw new Error(error.message || 'Failed to create account');
  }
};

// ─────────────────────────────────────────────
// Auth: Sign In / Sign Out
// ─────────────────────────────────────────────

export const signInTeacher = async (data: TeacherLoginData): Promise<User> => {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, data.email, data.password);
    return userCredential.user;
  } catch (error: any) {
    if (error.code === 'auth/user-not-found') throw new Error('No account found with this email');
    if (error.code === 'auth/wrong-password') throw new Error('Incorrect password');
    if (error.code === 'auth/invalid-email') throw new Error('Invalid email address');
    if (error.code === 'auth/too-many-requests') throw new Error('Too many failed attempts. Please try again later');
    throw new Error(error.message || 'Failed to sign in');
  }
};

export const signOutUser = async (): Promise<void> => {
  try {
    await firebaseSignOut(auth);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to sign out');
  }
};

// ─────────────────────────────────────────────
// Profiles
// ─────────────────────────────────────────────

export const getTeacherProfile = async (uid: string): Promise<TeacherProfile | null> => {
  try {
    const snapshot = await get(ref(database, `users/teachers/${uid}`));
    if (snapshot.exists()) return snapshot.val() as TeacherProfile;
    return null;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch profile');
  }
};

export const getStudentProfile = async (uid: string): Promise<StudentProfile | null> => {
  try {
    const snapshot = await get(ref(database, `users/students/${uid}`));
    if (snapshot.exists()) return snapshot.val() as StudentProfile;
    return null;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch profile');
  }
};

export const getUserProfile = async (uid: string): Promise<UserProfile | null> => {
  try {
    const teacherProfile = await getTeacherProfile(uid);
    if (teacherProfile) return teacherProfile;
    const studentProfile = await getStudentProfile(uid);
    if (studentProfile) return studentProfile;
    return null;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch profile');
  }
};

export const updateTeacherProfile = async (
  teacherId: string,
  data: { fullName?: string; username?: string; employeeId?: string }
): Promise<void> => {
  try {
    const teacherRef = ref(database, `users/teachers/${teacherId}`);
    const updates: any = {};
    if (data.fullName) updates.fullName = data.fullName.trim();
    if (data.username) updates.username = data.username.trim();
    if (data.employeeId) updates.employeeId = data.employeeId.trim();
    await update(teacherRef, updates);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to update profile');
  }
};

// ─────────────────────────────────────────────
// Temp Code (Raspi Login)
// ─────────────────────────────────────────────

/**
 * Generates a random 8-digit numeric code e.g. "12345678"
 */
const generateRandomCode = (): string => {
  const min = 10000000;
  const max = 99999999;
  return String(Math.floor(Math.random() * (max - min + 1)) + min);
};

/**
 * Generate a temp code for Raspi login.
 *
 * Writes to: /users_temp_code/{code}/
 *   - uid        : string  (teacher's Firebase UID)
 *   - username   : string
 *   - created_at : number  (timestamp)
 *
 * Also schedules auto-deletion after 30 seconds.
 *
 * Returns the generated 8-digit code string.
 */
export const generateTempCode = async (
  uid: string,
  username: string
): Promise<string> => {
  if (!uid || !username) throw new Error('uid and username are required');

  const code = generateRandomCode();
  const created_at = Date.now();

  await set(ref(database, `users_temp_code/${code}`), {
    uid,
    username,
    created_at,
  });

  // Auto-delete from Firebase after 30 seconds
  setTimeout(async () => {
    try {
      await deleteTempCode(code);
    } catch {
      // Silently ignore — Raspi may have already consumed/deleted it
    }
  }, 30_000);

  return code;
};

/**
 * Delete a temp code from Firebase.
 * Called after 30s expiry or after Raspi consumes it.
 *
 * Deletes: /users_temp_code/{code}
 */
export const deleteTempCode = async (code: string): Promise<void> => {
  if (!code) return;
  await remove(ref(database, `users_temp_code/${code}`));
};