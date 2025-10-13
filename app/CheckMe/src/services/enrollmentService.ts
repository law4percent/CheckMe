// src/services/enrollmentService.ts
import { ref, set, get, update, remove, query, orderByChild, equalTo } from 'firebase/database';
import { database } from '../config/firebase';

export interface Enrollment {
  studentId: string;
  subjectId: string;
  status: 'pending' | 'approved' | 'rejected';
  joinedAt: number;
  approvedAt?: number;
  rejectedAt?: number;
  studentName?: string;
  studentEmail?: string;
}

export interface CreateEnrollmentData {
  studentId: string;
  subjectId: string;
  studentName: string;
  studentEmail: string;
}

/**
 * Create a new enrollment request
 */
export const createEnrollment = async (data: CreateEnrollmentData): Promise<Enrollment> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${data.subjectId}/${data.studentId}`);
    
    const enrollment: Enrollment = {
      studentId: data.studentId,
      subjectId: data.subjectId,
      status: 'pending',
      joinedAt: Date.now(),
      studentName: data.studentName,
      studentEmail: data.studentEmail
    };

    await set(enrollmentRef, enrollment);
    return enrollment;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to create enrollment');
  }
};

/**
 * Get all enrollments for a subject
 */
export const getSubjectEnrollments = async (subjectId: string): Promise<Enrollment[]> => {
  try {
    const enrollmentsRef = ref(database, `enrollments/${subjectId}`);
    const snapshot = await get(enrollmentsRef);
    
    if (!snapshot.exists()) {
      return [];
    }

    const enrollmentsData = snapshot.val();
    const enrollments: Enrollment[] = Object.values(enrollmentsData);
    
    // Sort by joinedAt (newest first)
    return enrollments.sort((a, b) => b.joinedAt - a.joinedAt);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch enrollments');
  }
};

/**
 * Get pending enrollments for a subject
 */
export const getPendingEnrollments = async (subjectId: string): Promise<Enrollment[]> => {
  try {
    const enrollments = await getSubjectEnrollments(subjectId);
    return enrollments.filter(e => e.status === 'pending');
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch pending enrollments');
  }
};

/**
 * Approve an enrollment
 */
export const approveEnrollment = async (
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${subjectId}/${studentId}`);
    await update(enrollmentRef, {
      status: 'approved',
      approvedAt: Date.now()
    });
  } catch (error: any) {
    throw new Error(error.message || 'Failed to approve enrollment');
  }
};

/**
 * Reject an enrollment
 */
export const rejectEnrollment = async (
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${subjectId}/${studentId}`);
    await update(enrollmentRef, {
      status: 'rejected',
      rejectedAt: Date.now()
    });
  } catch (error: any) {
    throw new Error(error.message || 'Failed to reject enrollment');
  }
};

/**
 * Remove an enrollment
 */
export const removeEnrollment = async (
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${subjectId}/${studentId}`);
    await remove(enrollmentRef);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to remove enrollment');
  }
};

/**
 * Check if student is enrolled in subject
 */
export const isStudentEnrolled = async (
  subjectId: string,
  studentId: string
): Promise<boolean> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${subjectId}/${studentId}`);
    const snapshot = await get(enrollmentRef);
    
    if (!snapshot.exists()) {
      return false;
    }

    const enrollment = snapshot.val() as Enrollment;
    return enrollment.status === 'approved';
  } catch (error: any) {
    throw new Error(error.message || 'Failed to check enrollment status');
  }
};