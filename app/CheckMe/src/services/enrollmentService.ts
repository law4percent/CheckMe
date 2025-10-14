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
export const createEnrollment = async (data: CreateEnrollmentData & { teacherId: string }): Promise<Enrollment> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${data.teacherId}/${data.subjectId}/${data.studentId}`);
    
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
export const getSubjectEnrollments = async (teacherId: string, subjectId: string): Promise<Enrollment[]> => {
  try {
    const path = `enrollments/${teacherId}/${subjectId}`;
    console.log('📚 [getSubjectEnrollments] Fetching enrollments');
    console.log('  - Path:', path);
    console.log('  - TeacherId:', teacherId);
    console.log('  - SubjectId:', subjectId);
    
    const enrollmentsRef = ref(database, path);
    const snapshot = await get(enrollmentsRef);
    
    console.log('  - Snapshot exists:', snapshot.exists());
    
    if (!snapshot.exists()) {
      console.log('  - No enrollments found');
      return [];
    }

    const enrollmentsData = snapshot.val();
    const enrollments: Enrollment[] = Object.values(enrollmentsData);
    
    console.log('  - Enrollments count:', enrollments.length);
    
    // Sort by joinedAt (newest first)
    return enrollments.sort((a, b) => b.joinedAt - a.joinedAt);
  } catch (error: any) {
    console.error('❌ [getSubjectEnrollments] Error:', error);
    console.error('  - Error code:', error.code);
    console.error('  - Error message:', error.message);
    throw new Error(error.message || 'Failed to fetch enrollments');
  }
};

/**
 * Get pending enrollments for a subject
 */
export const getPendingEnrollments = async (teacherId: string, subjectId: string): Promise<Enrollment[]> => {
  try {
    const enrollments = await getSubjectEnrollments(teacherId, subjectId);
    return enrollments.filter(e => e.status === 'pending');
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch pending enrollments');
  }
};

/**
 * Approve an enrollment
 */
export const approveEnrollment = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    const path = `enrollments/${teacherId}/${subjectId}/${studentId}`;
    console.log('✅ [approveEnrollment] Approving enrollment');
    console.log('  - Path:', path);
    console.log('  - TeacherId:', teacherId);
    console.log('  - SubjectId:', subjectId);
    console.log('  - StudentId:', studentId);
    
    const enrollmentRef = ref(database, path);
    await update(enrollmentRef, {
      status: 'approved',
      approvedAt: Date.now()
    });
    
    console.log('  - Approval successful');
  } catch (error: any) {
    console.error('❌ [approveEnrollment] Error:', error);
    console.error('  - Error code:', error.code);
    console.error('  - Error message:', error.message);
    throw new Error(error.message || 'Failed to approve enrollment');
  }
};

/**
 * Reject an enrollment
 */
export const rejectEnrollment = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    const path = `enrollments/${teacherId}/${subjectId}/${studentId}`;
    console.log('❌ [rejectEnrollment] Rejecting enrollment');
    console.log('  - Path:', path);
    console.log('  - TeacherId:', teacherId);
    console.log('  - SubjectId:', subjectId);
    console.log('  - StudentId:', studentId);
    
    const enrollmentRef = ref(database, path);
    await update(enrollmentRef, {
      status: 'rejected',
      rejectedAt: Date.now()
    });
    
    console.log('  - Rejection successful');
  } catch (error: any) {
    console.error('❌ [rejectEnrollment] Error:', error);
    console.error('  - Error code:', error.code);
    console.error('  - Error message:', error.message);
    throw new Error(error.message || 'Failed to reject enrollment');
  }
};

/**
 * Remove an enrollment
 */
export const removeEnrollment = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${teacherId}/${subjectId}/${studentId}`);
    await remove(enrollmentRef);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to remove enrollment');
  }
};

/**
 * Check if student is enrolled in subject
 */
export const isStudentEnrolled = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<boolean> => {
  try {
    const enrollmentRef = ref(database, `enrollments/${teacherId}/${subjectId}/${studentId}`);
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