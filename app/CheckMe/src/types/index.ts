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

export interface StudentSignUpData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  username: string;
  studentId: string;
}

export interface TeacherLoginData {
  email: string;
  password: string;
}

export interface StudentLoginData {
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
  firstName: string;
  lastName: string;
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
  signUp: (data: TeacherSignUpData | StudentSignUpData) => Promise<void>;
  signIn: (data: TeacherLoginData | StudentLoginData) => Promise<void>;
  signOut: () => Promise<void>;
}

// Subject interface
export interface Subject {
  id: string;
  year: string;
  subjectName: string;
  subjectCode?: string;
  studentCount: number;
  teacherId: string;
  sectionId: string;
  createdAt: number;
  updatedAt: number;
}

/**
 * Assessment interface — matches /assessments/{teacherId}/{assessmentUid}/
 *
 * RTDB schema:
 *   assessmentName : string
 *   assessmentType : 'quiz' | 'exam'
 *   created_at     : number
 *   section_uid    : string
 *   subject_uid    : string
 */
export interface Assessment {
  assessmentUid: string;       // the RTDB key e.g. "QWER1234"
  assessmentName: string;
  assessmentType: 'quiz' | 'exam';
  sectionUid: string;          // maps to section_uid in RTDB
  subjectUid: string;          // maps to subject_uid in RTDB
  teacherId: string;
  createdAt: number;           // maps to created_at in RTDB
}

// Navigation types
export type RootStackParamList = {
  ViewScores: {
    assessmentUid: string;
    assessmentName?: string;
  };
  ChoosePortal: undefined;
  TeacherLogin: undefined;
  TeacherRegister: undefined;
  TeacherDashboard: undefined;
  TeacherSectionDashboard: {
    section: Section;
  };
  TeacherSubjectDashboard: {
    subject: Subject;
    section: Section;
  };
  TeacherAssessmentScoreTable: {
    assessment: Assessment;
    subject: Subject;
    section: Section;
  };
  StudentLogin: undefined;
  StudentRegister: undefined;
  StudentDashboard: undefined;
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}