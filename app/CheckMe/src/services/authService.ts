// src/services/authService.ts
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  User
} from 'firebase/auth';
import { ref, set, get, update } from 'firebase/database';
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

/**
 * Creates a new teacher account
 */
export const createTeacherAccount = async (data: TeacherSignUpData): Promise<User> => {
  // Validate Gmail address
  if (!isGmailAddress(data.email)) {
    throw new Error('Only Gmail addresses are allowed for registration');
  }

  try {
    // Create Firebase Auth user
    const userCredential = await createUserWithEmailAndPassword(
      auth,
      data.email,
      data.password
    );

    const user = userCredential.user;

    // Create teacher profile in Realtime Database
    const teacherProfile: Omit<TeacherProfile, 'uid'> = {
      fullName: data.fullName.trim(),
      email: data.email.toLowerCase().trim(),
      username: data.username.trim(),
      employeeId: data.employeeId.trim(),
      createdAt: Date.now(),
      role: 'teacher'
    };

    // Save to database
    await set(ref(database, `users/teachers/${user.uid}`), {
      ...teacherProfile,
      uid: user.uid
    });

    return user;
  } catch (error: any) {
    // Handle Firebase Auth errors
    if (error.code === 'auth/email-already-in-use') {
      throw new Error('This email is already registered');
    } else if (error.code === 'auth/invalid-email') {
      throw new Error('Invalid email address');
    } else if (error.code === 'auth/weak-password') {
      throw new Error('Password is too weak');
    } else {
      throw new Error(error.message || 'Failed to create account');
    }
  }
};

/**
 * Creates a new student account
 */
export const createStudentAccount = async (data: StudentSignUpData): Promise<User> => {
  // Validate Gmail address
  if (!isGmailAddress(data.email)) {
    throw new Error('Only Gmail addresses are allowed for registration');
  }

  try {
    // Create Firebase Auth user
    const userCredential = await createUserWithEmailAndPassword(
      auth,
      data.email,
      data.password
    );

    const user = userCredential.user;
    const fullName = `${data.firstName.trim()} ${data.lastName.trim()}`;

    // Create student profile in Realtime Database
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

    // Save to database
    await set(ref(database, `users/students/${user.uid}`), {
      ...studentProfile,
      uid: user.uid
    });

    return user;
  } catch (error: any) {
    // Handle Firebase Auth errors
    if (error.code === 'auth/email-already-in-use') {
      throw new Error('This email is already registered');
    } else if (error.code === 'auth/invalid-email') {
      throw new Error('Invalid email address');
    } else if (error.code === 'auth/weak-password') {
      throw new Error('Password is too weak');
    } else {
      throw new Error(error.message || 'Failed to create account');
    }
  }
};

/**
 * Signs in a teacher user
 */
export const signInTeacher = async (data: TeacherLoginData): Promise<User> => {
  try {
    const userCredential = await signInWithEmailAndPassword(
      auth,
      data.email,
      data.password
    );

    return userCredential.user;
  } catch (error: any) {
    // Handle Firebase Auth errors
    if (error.code === 'auth/user-not-found') {
      throw new Error('No account found with this email');
    } else if (error.code === 'auth/wrong-password') {
      throw new Error('Incorrect password');
    } else if (error.code === 'auth/invalid-email') {
      throw new Error('Invalid email address');
    } else if (error.code === 'auth/too-many-requests') {
      throw new Error('Too many failed attempts. Please try again later');
    } else {
      throw new Error(error.message || 'Failed to sign in');
    }
  }
};

/**
 * Signs out the current user
 */
export const signOutUser = async (): Promise<void> => {
  try {
    await firebaseSignOut(auth);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to sign out');
  }
};

/**
 * Fetches teacher profile from database
 */
export const getTeacherProfile = async (uid: string): Promise<TeacherProfile | null> => {
  try {
    const snapshot = await get(ref(database, `users/teachers/${uid}`));
    
    if (snapshot.exists()) {
      return snapshot.val() as TeacherProfile;
    }
    
    return null;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch profile');
  }
};

/**
 * Fetches student profile from database
 */
export const getStudentProfile = async (uid: string): Promise<StudentProfile | null> => {
  try {
    const snapshot = await get(ref(database, `users/students/${uid}`));
    
    if (snapshot.exists()) {
      return snapshot.val() as StudentProfile;
    }
    
    return null;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch profile');
  }
};

/**
 * Fetches user profile (teacher or student) from database
 */
export const getUserProfile = async (uid: string): Promise<UserProfile | null> => {
  try {
    // Try teacher first
    const teacherProfile = await getTeacherProfile(uid);
    if (teacherProfile) return teacherProfile;
    
    // Try student
    const studentProfile = await getStudentProfile(uid);
    if (studentProfile) return studentProfile;
    
    return null;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch profile');
  }
};

/**
 * Update teacher profile
 */
export const updateTeacherProfile = async (
  teacherId: string,
  data: {
    fullName?: string;
    username?: string;
    employeeId?: string;
  }
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