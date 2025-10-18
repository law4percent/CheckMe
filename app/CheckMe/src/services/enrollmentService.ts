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

/**
 * Join a subject using an invite code
 */
export const joinSubjectWithCode = async (
  code: string,
  studentId: string,
  studentName: string,
  studentEmail: string
): Promise<{ success: boolean; message: string }> => {
  try {
    // Validate the invite code
    const { validateInviteCode } = require('./inviteCodeService');
    const validation = await validateInviteCode(code);
    
    if (!validation.valid || !validation.inviteCode) {
      return {
        success: false,
        message: validation.error || 'Invalid invite code'
      };
    }
    
    const inviteCode = validation.inviteCode;
    
    // Check if student is already enrolled
    const alreadyEnrolled = await isStudentEnrolled(
      inviteCode.teacherId,
      inviteCode.subjectId,
      studentId
    );
    
    if (alreadyEnrolled) {
      return {
        success: false,
        message: 'You are already enrolled in this subject'
      };
    }
    
    // Check if there's a pending enrollment
    const enrollmentRef = ref(database, `enrollments/${inviteCode.teacherId}/${inviteCode.subjectId}/${studentId}`);
    const snapshot = await get(enrollmentRef);
    
    if (snapshot.exists()) {
      const enrollment = snapshot.val() as Enrollment;
      if (enrollment.status === 'pending') {
        return {
          success: false,
          message: 'Your enrollment request is pending approval'
        };
      } else if (enrollment.status === 'rejected') {
        // Allow re-enrollment if previously rejected
        await createEnrollment({
          studentId,
          subjectId: inviteCode.subjectId,
          studentName,
          studentEmail,
          teacherId: inviteCode.teacherId
        });
        return {
          success: true,
          message: 'Enrollment request submitted successfully!'
        };
      }
    }
    
    // Create enrollment
    await createEnrollment({
      studentId,
      subjectId: inviteCode.subjectId,
      studentName,
      studentEmail,
      teacherId: inviteCode.teacherId
    });
    
    return {
      success: true,
      message: 'Enrollment request submitted successfully!'
    };
  } catch (error: any) {
    console.error('❌ [joinSubjectWithCode] Error:', error);
    throw new Error(error.message || 'Failed to join subject');
  }
};

/**
 * Get student enrollments across all subjects with full details
 */
export const getStudentEnrollments = async (studentId: string): Promise<Array<Enrollment & {
  teacherName: string;
  sectionName: string;
  year: string;
  subjectName: string;
  subjectCode: string;
}>> => {
  try {
    const enrollmentsRef = ref(database, 'enrollments');
    const snapshot = await get(enrollmentsRef);
    
    if (!snapshot.exists()) {
      return [];
    }
    
    const allEnrollments: Array<Enrollment & {
      teacherName: string;
      sectionName: string;
      year: string;
      subjectName: string;
      subjectCode: string;
    }> = [];
    
    const enrollmentsData = snapshot.val();
    
    // Get all invite codes to find subject details
    const inviteCodesRef = ref(database, 'inviteCodes');
    const inviteCodesSnapshot = await get(inviteCodesRef);
    const inviteCodes = inviteCodesSnapshot.exists() ? inviteCodesSnapshot.val() : {};
    
    // Create a map of subjectId to subject details
    const subjectDetailsMap: { [key: string]: any } = {};
    Object.values(inviteCodes).forEach((inviteCode: any) => {
      if (!subjectDetailsMap[inviteCode.subjectId]) {
        subjectDetailsMap[inviteCode.subjectId] = {
          subjectName: inviteCode.subjectName,
          teacherName: inviteCode.teacherName,
          sectionName: inviteCode.sectionName,
          year: inviteCode.year,
          subjectCode: inviteCode.code
        };
      }
    });
    
    // Iterate through all teachers
    Object.keys(enrollmentsData).forEach((teacherId) => {
      const teacherEnrollments = enrollmentsData[teacherId];
      
      // Iterate through all subjects
      Object.keys(teacherEnrollments).forEach((subjectId) => {
        const subjectEnrollments = teacherEnrollments[subjectId];
        
        // Check if student is enrolled in this subject
        if (subjectEnrollments[studentId]) {
          const enrollment = subjectEnrollments[studentId] as Enrollment;
          
          // Only include approved enrollments
          if (enrollment.status === 'approved') {
            const subjectDetails = subjectDetailsMap[subjectId] || {
              subjectName: 'Unknown Subject',
              teacherName: 'Unknown Teacher',
              sectionName: 'Unknown Section',
              year: '',
              subjectCode: ''
            };
            
            allEnrollments.push({
              ...enrollment,
              teacherName: subjectDetails.teacherName,
              sectionName: subjectDetails.sectionName,
              year: subjectDetails.year,
              subjectName: subjectDetails.subjectName,
              subjectCode: subjectDetails.subjectCode
            });
          }
        }
      });
    });
    
    return allEnrollments.sort((a, b) => b.joinedAt - a.joinedAt);
  } catch (error: any) {
    console.error('❌ [getStudentEnrollments] Error:', error);
    throw new Error(error.message || 'Failed to fetch student enrollments');
  }
};