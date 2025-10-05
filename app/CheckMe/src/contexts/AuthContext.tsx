// src/contexts/AuthContext.tsx
import React, { createContext, useState, useEffect, useContext } from 'react';
import { onAuthStateChanged, User as FirebaseUser } from 'firebase/auth';
import { auth } from '../config/firebase';
import { 
  createTeacherAccount, 
  signInTeacher, 
  signOutUser, 
  getTeacherProfile 
} from '../services/authService';
import { 
  AuthContextType, 
  TeacherSignUpData, 
  TeacherLoginData, 
  UserProfile 
} from '../types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // Listen for auth state changes
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
      if (firebaseUser) {
        try {
          // Fetch user profile from database
          const profile = await getTeacherProfile(firebaseUser.uid);
          setUser(profile);
        } catch (error) {
          console.error('Error fetching user profile:', error);
          setUser(null);
        }
      } else {
        setUser(null);
      }
      setLoading(false);
    });

    // Cleanup subscription
    return () => unsubscribe();
  }, []);

  const signUp = async (data: TeacherSignUpData): Promise<void> => {
    try {
      setLoading(true);
      await createTeacherAccount(data);
      // User will be automatically signed out after registration
      await signOutUser();
    } catch (error: any) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (data: TeacherLoginData): Promise<void> => {
    try {
      setLoading(true);
      await signInTeacher(data);
      // onAuthStateChanged will automatically update the user state
    } catch (error: any) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async (): Promise<void> => {
    try {
      setLoading(true);
      await signOutUser();
    } catch (error: any) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    signUp,
    signIn,
    signOut
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};