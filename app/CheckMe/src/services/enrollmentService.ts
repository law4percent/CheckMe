// src/services/enrollmentService.ts
import { ref, set, get, update, remove } from 'firebase/database';
import { database } from '../config/firebase';

export interface Enrollment {
  studentId: string;   // Firebase UID (RTDB key under subject)
  schoolId?: string;   // School-provided ID e.g. "4201400" — matches answer sheet key
  subjectId: string;
  status: 'pending' | 'approved' | 'rejected';
  joinedAt: number;
  approvedAt?: number;
  rejectedAt?: number;
  studentName?: string;
  studentEmail?: string;
}

export interface CreateEnrollmentData {
  studentId: string;   // Firebase UID
  schoolId?: string;   // School ID — fetched from /users/students/{uid}/studentId
  subjectId: string;
  studentName: string;
  studentEmail: string;
}

// ─────────────────────────────────────────────
// Helper: fetch school ID from student profile
// ─────────────────────────────────────────────

/**
 * Reads /users/students/{uid}/studentId which stores the school-provided
 * numeric ID (e.g. 4201400). This is the same ID written on answer sheets.
 * Returns null if not found or not set.
 */
const fetchSchoolId = async (firebaseUid: string): Promise<string | null> => {
  try {
    const snap = await get(ref(database, `users/students/${firebaseUid}/studentId`));
    if (!snap.exists()) return null;
    const val = snap.val();
    // studentId may be stored as number or string
    return val != null ? String(val) : null;
  } catch {
    return null;
  }
};

// ─────────────────────────────────────────────
// Helper: update subject studentCount
// ─────────────────────────────────────────────

const updateSubjectStudentCount = async (teacherId: string, subjectId: string): Promise<void> => {
  try {
    const subjectsSnap = await get(ref(database, `subjects/${teacherId}`));
    if (!subjectsSnap.exists()) return;

    const sections = subjectsSnap.val();
    let foundSectionId: string | null = null;

    for (const sectionId in sections) {
      if (sections[sectionId][subjectId]) {
        foundSectionId = sectionId;
        break;
      }
    }

    if (!foundSectionId) return;

    const enrollmentsSnap = await get(ref(database, `enrollments/${teacherId}/${subjectId}`));
    let approvedCount = 0;
    if (enrollmentsSnap.exists()) {
      approvedCount = Object.values(enrollmentsSnap.val()).filter(
        (e: any) => e.status === 'approved'
      ).length;
    }

    await update(ref(database, `subjects/${teacherId}/${foundSectionId}/${subjectId}`), {
      studentCount: approvedCount,
      updatedAt: Date.now(),
    });
  } catch {
    // Non-critical — don't throw
  }
};

// ─────────────────────────────────────────────
// Service Functions
// ─────────────────────────────────────────────

/**
 * Create a new enrollment request.
 * Writes schoolId if provided so answer sheets can be matched later.
 */
export const createEnrollment = async (
  data: CreateEnrollmentData & { teacherId: string }
): Promise<Enrollment> => {
  try {
    const enrollmentRef = ref(
      database,
      `enrollments/${data.teacherId}/${data.subjectId}/${data.studentId}`
    );

    const enrollment: Enrollment = {
      studentId: data.studentId,
      subjectId: data.subjectId,
      status: 'pending',
      joinedAt: Date.now(),
      studentName: data.studentName,
      studentEmail: data.studentEmail,
      ...(data.schoolId ? { schoolId: data.schoolId } : {}),
    };

    await set(enrollmentRef, enrollment);
    return enrollment;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to create enrollment');
  }
};

/**
 * Get all enrollments for a subject.
 */
export const getSubjectEnrollments = async (
  teacherId: string,
  subjectId: string
): Promise<Enrollment[]> => {
  try {
    const snap = await get(ref(database, `enrollments/${teacherId}/${subjectId}`));
    if (!snap.exists()) return [];

    const enrollments: Enrollment[] = Object.values(snap.val());
    return enrollments.sort((a, b) => b.joinedAt - a.joinedAt);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch enrollments');
  }
};

/**
 * Get pending enrollments for a subject.
 */
export const getPendingEnrollments = async (
  teacherId: string,
  subjectId: string
): Promise<Enrollment[]> => {
  const enrollments = await getSubjectEnrollments(teacherId, subjectId);
  return enrollments.filter(e => e.status === 'pending');
};

/**
 * Approve an enrollment.
 */
export const approveEnrollment = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    await update(ref(database, `enrollments/${teacherId}/${subjectId}/${studentId}`), {
      status: 'approved',
      approvedAt: Date.now(),
    });
    await updateSubjectStudentCount(teacherId, subjectId);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to approve enrollment');
  }
};

/**
 * Reject an enrollment.
 */
export const rejectEnrollment = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    await update(ref(database, `enrollments/${teacherId}/${subjectId}/${studentId}`), {
      status: 'rejected',
      rejectedAt: Date.now(),
    });
    await updateSubjectStudentCount(teacherId, subjectId);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to reject enrollment');
  }
};

/**
 * Remove an enrollment.
 */
export const removeEnrollment = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<void> => {
  try {
    await remove(ref(database, `enrollments/${teacherId}/${subjectId}/${studentId}`));
    await updateSubjectStudentCount(teacherId, subjectId);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to remove enrollment');
  }
};

/**
 * Check if a student (by Firebase UID) is approved in a subject.
 */
export const isStudentEnrolled = async (
  teacherId: string,
  subjectId: string,
  studentId: string
): Promise<boolean> => {
  try {
    const snap = await get(
      ref(database, `enrollments/${teacherId}/${subjectId}/${studentId}`)
    );
    if (!snap.exists()) return false;
    return (snap.val() as Enrollment).status === 'approved';
  } catch (error: any) {
    throw new Error(error.message || 'Failed to check enrollment status');
  }
};

/**
 * Join a subject using an invite code.
 *
 * Key addition: reads schoolId from /users/students/{uid}/studentId
 * and writes it to the enrollment record so answer sheets can be matched.
 */
export const joinSubjectWithCode = async (
  code: string,
  studentUid: string,
  studentName: string,
  studentEmail: string
): Promise<{ success: boolean; message: string }> => {
  try {
    const { validateInviteCode } = require('./inviteCodeService');
    const validation = await validateInviteCode(code);

    if (!validation.valid || !validation.inviteCode) {
      return { success: false, message: validation.error || 'Invalid invite code' };
    }

    const inviteCode = validation.inviteCode;

    // Fetch school ID from student profile BEFORE writing enrollment
    const schoolId = await fetchSchoolId(studentUid);

    // Check existing enrollment
    const existingSnap = await get(
      ref(database, `enrollments/${inviteCode.teacherId}/${inviteCode.subjectId}/${studentUid}`)
    );

    if (existingSnap.exists()) {
      const existing = existingSnap.val() as Enrollment;

      if (existing.status === 'approved') {
        return { success: false, message: 'You are already enrolled in this subject' };
      }
      if (existing.status === 'pending') {
        return { success: false, message: 'Your enrollment request is pending approval' };
      }
      // Previously rejected — allow re-enrollment, also update schoolId in case it changed
    }

    await createEnrollment({
      studentId: studentUid,
      schoolId: schoolId ?? undefined,
      subjectId: inviteCode.subjectId,
      studentName,
      studentEmail,
      teacherId: inviteCode.teacherId,
    });

    return { success: true, message: 'Enrollment request submitted successfully!' };
  } catch (error: any) {
    console.error('❌ [joinSubjectWithCode] Error:', error);
    throw new Error(error.message || 'Failed to join subject');
  }
};

/**
 * Get student enrollments across all subjects with full details.
 */
export const getStudentEnrollments = async (
  studentId: string
): Promise<Array<Enrollment & {
  teacherName: string;
  sectionName: string;
  year: string;
  subjectName: string;
  subjectCode: string;
}>> => {
  try {
    const snap = await get(ref(database, 'enrollments'));
    if (!snap.exists()) return [];

    const inviteCodesSnap = await get(ref(database, 'inviteCodes'));
    const inviteCodes = inviteCodesSnap.exists() ? inviteCodesSnap.val() : {};

    const subjectDetailsMap: Record<string, any> = {};
    Object.values(inviteCodes).forEach((ic: any) => {
      if (ic?.subjectId && !subjectDetailsMap[ic.subjectId]) {
        subjectDetailsMap[ic.subjectId] = {
          subjectName: ic.subjectName,
          teacherName: ic.teacherName,
          sectionName: ic.sectionName,
          year: ic.year,
          subjectCode: ic.code,
        };
      }
    });

    const result: any[] = [];
    const allEnrollments = snap.val() as Record<string, Record<string, Record<string, any>>>;

    Object.entries(allEnrollments).forEach(([teacherId, teacherEnrollments]) => {
      Object.entries(teacherEnrollments).forEach(([subjectId, subjectEnrollments]) => {
        const enrollment = subjectEnrollments[studentId];
        if (enrollment?.status === 'approved') {
          const meta = subjectDetailsMap[subjectId] ?? {
            subjectName: 'Unknown Subject',
            teacherName: 'Unknown Teacher',
            sectionName: '',
            year: '',
            subjectCode: '',
          };
          result.push({ ...enrollment, ...meta });
        }
      });
    });

    return result.sort((a, b) => b.joinedAt - a.joinedAt);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch student enrollments');
  }
};