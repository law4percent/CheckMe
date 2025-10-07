// src/types/index.ts

export interface Section {
  id: string;
  year: string;
  sectionName: string;
  subjectCount: number;
  teacherId: string;
  createdAt: number;
  updatedAt: number;
}

export interface CreateSectionData {
  year: string;
  sectionName: string;
  teacherId: string;
}

export interface UpdateSectionData {
  year?: string;
  sectionName?: string;
}

export interface UpdateTeacherProfileData {
  fullName?: string;
  username?: string;
  employeeId?: string;
}

export interface TeacherSignUpData {
  fullName: string;
  email: string;
  password: string;
  username: string;
  employeeId: string;
}

export interface TeacherLoginData {
  email: string;
  password: string;
}

export interface TeacherProfile {
  uid: string;
  fullName: string;
  email: string;
  username: string;
  employeeId: string;
  createdAt: number;
  role: 'teacher';
}

export interface StudentProfile {
  uid: string;
  fullName: string;
  email: string;
  username: string;
  studentId: string;
  createdAt: number;
  role: 'student';
}

export type UserProfile = TeacherProfile | StudentProfile;

export type PortalType = 'teacher' | 'student';

export interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  signUp: (data: TeacherSignUpData) => Promise<void>;
  signIn: (data: TeacherLoginData) => Promise<void>;
  signOut: () => Promise<void>;
}

// Navigation types
export type RootStackParamList = {
  ChoosePortal: undefined;
  TeacherLogin: undefined;
  TeacherRegister: undefined;
  TeacherDashboard: undefined;
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}