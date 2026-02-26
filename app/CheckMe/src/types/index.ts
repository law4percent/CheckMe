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
 * Assessment — matches /assessments/{teacherId}/{assessmentUid}/
 */
export interface Assessment {
  assessmentUid: string;
  assessmentName: string;
  assessmentType: 'quiz' | 'exam';
  sectionUid: string;
  subjectUid: string;
  teacherId: string;
  createdAt: number;
}

/**
 * Per-question breakdown entry from /answer_sheets/.../breakdown/Q{n}/
 */
export interface QuestionBreakdown {
  student_answer: string;
  correct_answer: string;
  /** true = correct, false = wrong, "pending" = essay not yet scored */
  checking_result: boolean | 'pending';
}

/**
 * A single student result from
 * /answer_sheets/{teacher_uid}/{assessment_uid}/{student_id}/
 *
 * student_id key = school ID written on the paper (e.g. "3222550")
 * matchedStudentName = resolved from /enrollments/ if school ID field exists,
 *                      null until that field is added to enrollments.
 */
export interface AnswerSheetResult {
  studentId: string;              // RTDB key = school ID from paper
  assessment_uid: string;
  total_score: number;
  total_questions: number;
  is_final_score: boolean;
  breakdown: Record<string, QuestionBreakdown>;
  image_urls: string[];
  image_public_ids: string[];
  checked_by: string;
  checked_at: number;
  updated_at: number;
  section_uid: string;
  subject_uid: string;
  /** Resolved display name — null means school ID not matched in enrollments */
  matchedStudentName: string | null;
}

export type RootStackParamList = {
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
  AnswerKeys: {
    teacherUid: string;
    subjectUid: string;
    subjectName: string;
  };
  ViewScores: {
    assessmentUid: string;
    assessmentName?: string;
    teacherUid: string;
    subjectUid: string;
  };
  TeacherAssessmentScoreTable: {
    result: AnswerSheetResult;
    assessmentName: string;
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