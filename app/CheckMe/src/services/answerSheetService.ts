// src/services/answerSheetService.ts
import { ref, get, set, update, remove } from 'firebase/database';
import { database } from '../config/firebase';
import { AnswerSheetResult, QuestionBreakdown } from '../types';

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

/**
 * Build a name-lookup map from /enrollments/{teacherUid}/{subjectUid}/
 *
 * Shape: { [schoolId]: studentName }
 *
 * schoolId comes from enrollment.schoolId which is written at join time
 * by reading /users/students/{uid}/studentId (the school-provided number,
 * e.g. "4201400"). This matches the key used in /answer_sheets/.
 *
 * Enrollments created before this field was added will not have schoolId
 * and will continue to show "Unknown Student" until the student re-enrolls
 * or the field is backfilled.
 */
const buildStudentNameMap = async (
  teacherUid: string,
  subjectUid: string
): Promise<Record<string, string>> => {
  try {
    const snapshot = await get(
      ref(database, `enrollments/${teacherUid}/${subjectUid}`)
    );
    if (!snapshot.exists()) return {};

    const data = snapshot.val() as Record<string, any>;
    const map: Record<string, string> = {};

    Object.values(data).forEach((enrollment: any) => {
      if (enrollment?.schoolId && enrollment?.studentName) {
        // schoolId is stored as string — normalize to string in case saved as number
        map[String(enrollment.schoolId)] = enrollment.studentName;
      }
    });

    return map;
  } catch {
    return {};
  }
};

/**
 * Parse image_urls from Firebase — handles both array and object formats.
 * Raspi may save as object { "0": url, "1": url } or as array.
 */
const parseImageUrls = (raw: any): string[] => {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.filter(Boolean);
  if (typeof raw === 'object') {
    return Object.keys(raw)
      .sort((a, b) => Number(a) - Number(b))
      .map(k => raw[k])
      .filter(Boolean);
  }
  return [];
};

/**
 * Parse breakdown from Firebase.
 * Returns sorted Q1, Q2, ... Qn record.
 */
const parseBreakdown = (raw: any): Record<string, QuestionBreakdown> => {
  if (!raw || typeof raw !== 'object') return {};
  return raw as Record<string, QuestionBreakdown>;
};

// ─────────────────────────────────────────────
// Service Functions
// ─────────────────────────────────────────────

/**
 * Load all student results for an assessment.
 *
 * Reads: /answer_sheets/{teacherUid}/{assessmentUid}/
 * Cross-refs: /enrollments/{teacherUid}/{subjectUid}/ for name matching
 *
 * Returns array sorted by total_score descending.
 */
export const getAnswerSheets = async (
  teacherUid: string,
  assessmentUid: string,
  subjectUid: string
): Promise<AnswerSheetResult[]> => {
  if (!teacherUid || !assessmentUid) return [];

  const [sheetsSnapshot, nameMap] = await Promise.all([
    get(ref(database, `answer_sheets/${teacherUid}/${assessmentUid}`)),
    buildStudentNameMap(teacherUid, subjectUid),
  ]);

  if (!sheetsSnapshot.exists()) return [];

  const raw = sheetsSnapshot.val() as Record<string, any>;

  const results: AnswerSheetResult[] = Object.entries(raw).map(
    ([studentId, data]) => ({
      studentId,
      assessment_uid: data.assessment_uid ?? assessmentUid,
      total_score: data.total_score ?? 0,
      total_questions: data.total_questions ?? 0,
      is_final_score: data.is_final_score ?? true,
      breakdown: parseBreakdown(data.breakdown),
      image_urls: parseImageUrls(data.image_urls),
      image_public_ids: parseImageUrls(data.image_public_ids),
      checked_by: data.checked_by ?? '',
      checked_at: data.checked_at ?? 0,
      updated_at: data.updated_at ?? 0,
      section_uid: data.section_uid ?? '',
      subject_uid: data.subject_uid ?? '',
      matchedStudentName: nameMap[studentId] ?? null,
    })
  );

  // Sort: highest score first; pending (is_final_score=false) shown after scored
  results.sort((a, b) => {
    const pctA = a.total_questions > 0 ? a.total_score / a.total_questions : 0;
    const pctB = b.total_questions > 0 ? b.total_score / b.total_questions : 0;
    return pctB - pctA;
  });

  return results;
};

/**
 * Get a single student's answer sheet.
 *
 * Reads: /answer_sheets/{teacherUid}/{assessmentUid}/{studentId}/
 */
export const getAnswerSheet = async (
  teacherUid: string,
  assessmentUid: string,
  studentId: string
): Promise<AnswerSheetResult | null> => {
  const snapshot = await get(
    ref(database, `answer_sheets/${teacherUid}/${assessmentUid}/${studentId}`)
  );
  if (!snapshot.exists()) return null;

  const data = snapshot.val();

  return {
    studentId,
    assessment_uid: data.assessment_uid ?? assessmentUid,
    total_score: data.total_score ?? 0,
    total_questions: data.total_questions ?? 0,
    is_final_score: data.is_final_score ?? true,
    breakdown: parseBreakdown(data.breakdown),
    image_urls: parseImageUrls(data.image_urls),
    image_public_ids: parseImageUrls(data.image_public_ids),
    checked_by: data.checked_by ?? '',
    checked_at: data.checked_at ?? 0,
    updated_at: data.updated_at ?? 0,
    section_uid: data.section_uid ?? '',
    subject_uid: data.subject_uid ?? '',
    matchedStudentName: null,
  };
};

/**
 * Update total_score (and mark updated_at) for a student's answer sheet.
 * Called when teacher manually edits a score in ViewScoresScreen.
 *
 * Updates: /answer_sheets/{teacherUid}/{assessmentUid}/{studentId}/
 *   - total_score
 *   - updated_at
 */
export const updateAnswerSheetScore = async (
  teacherUid: string,
  assessmentUid: string,
  studentId: string,
  newScore: number
): Promise<void> => {
  await update(
    ref(database, `answer_sheets/${teacherUid}/${assessmentUid}/${studentId}`),
    {
      total_score: newScore,
      updated_at: Date.now(),
    }
  );
};

// ─────────────────────────────────────────────
// Student ID validation
// ─────────────────────────────────────────────

export interface StudentIdValidation {
  exists: boolean;          // found in /users/students/ by schoolId
  enrolled: boolean;        // has approved enrollment in this subject
  studentName: string | null;
  firebaseUid: string | null;
}

/**
 * Validates a school ID (e.g. "4201400") against registered students
 * and checks enrollment in the given subject.
 *
 * 1. Scans /users/students/ for a matching studentId field
 * 2. If found, checks /enrollments/{teacherUid}/{subjectUid}/ for approved status
 */
export const validateStudentId = async (
  schoolId: string,
  teacherUid: string,
  subjectUid: string
): Promise<StudentIdValidation> => {
  const result: StudentIdValidation = {
    exists: false,
    enrolled: false,
    studentName: null,
    firebaseUid: null,
  };

  try {
    // Step 1: Find student by school ID
    const studentsSnap = await get(ref(database, 'users/students'));
    if (!studentsSnap.exists()) return result;

    const students = studentsSnap.val() as Record<string, any>;
    let matchedUid: string | null = null;
    let matchedName: string | null = null;

    for (const [uid, data] of Object.entries(students)) {
      if (data?.studentId != null && String(data.studentId) === String(schoolId).trim()) {
        matchedUid = uid;
        matchedName = data.fullName ?? `${data.firstName ?? ''} ${data.lastName ?? ''}`.trim() ?? null;
        break;
      }
    }

    if (!matchedUid) return result;

    result.exists = true;
    result.firebaseUid = matchedUid;
    result.studentName = matchedName;

    // Step 2: Check enrollment
    const enrollmentSnap = await get(
      ref(database, `enrollments/${teacherUid}/${subjectUid}/${matchedUid}`)
    );

    if (enrollmentSnap.exists()) {
      const enrollment = enrollmentSnap.val();
      result.enrolled = enrollment?.status === 'approved';
    }

    return result;
  } catch {
    return result;
  }
};

// ─────────────────────────────────────────────
// Reassign answer sheet to a different student ID
// ─────────────────────────────────────────────

/**
 * Moves an answer sheet from one student ID key to another.
 *
 * RTDB operation:
 *   1. Read full document at /answer_sheets/{teacherUid}/{assessmentUid}/{oldStudentId}
 *   2. Write it to /answer_sheets/{teacherUid}/{assessmentUid}/{newStudentId}
 *      with student_id field updated to newStudentId
 *   3. Delete the old key
 *
 * Throws if old key does not exist or new key already has data.
 */
export const reassignAnswerSheet = async (
  teacherUid: string,
  assessmentUid: string,
  oldStudentId: string,
  newStudentId: string
): Promise<void> => {
  if (oldStudentId === newStudentId) return;

  const oldRef = ref(database, `answer_sheets/${teacherUid}/${assessmentUid}/${oldStudentId}`);
  const newRef = ref(database, `answer_sheets/${teacherUid}/${assessmentUid}/${newStudentId}`);

  // Check old record exists
  const oldSnap = await get(oldRef);
  if (!oldSnap.exists()) {
    throw new Error(`No answer sheet found for student ID "${oldStudentId}"`);
  }

  // Check new key is not already taken
  const newSnap = await get(newRef);
  if (newSnap.exists()) {
    throw new Error(
      `Student ID "${newStudentId}" already has an answer sheet for this assessment. ` +
      `Delete it first before reassigning.`
    );
  }

  const data = oldSnap.val();

  // Write to new key with updated student_id field
  await set(newRef, {
    ...data,
    student_id: newStudentId,
    updated_at: Date.now(),
  });

  // Delete old key
  await remove(oldRef);
};

// ─────────────────────────────────────────────
// Reassign answer key to a different assessment UID
// ─────────────────────────────────────────────

/**
 * Moves an answer key from one assessment UID key to another.
 *
 * RTDB operation:
 *   1. Read full document at /answer_keys/{teacherUid}/{oldAssessmentUid}
 *   2. Check /answer_keys/{teacherUid}/{newAssessmentUid} does NOT exist — block if taken
 *   3. Write to new key with assessment_uid field updated
 *   4. Delete old key
 *
 * Answer sheets under the old UID are NOT moved — teacher decides what to do with them.
 * Throws if old key does not exist or new UID is already taken.
 */
export const reassignAnswerKey = async (
  teacherUid: string,
  oldAssessmentUid: string,
  newAssessmentUid: string
): Promise<void> => {
  if (oldAssessmentUid === newAssessmentUid) return;

  const oldRef = ref(database, `answer_keys/${teacherUid}/${oldAssessmentUid}`);
  const newRef = ref(database, `answer_keys/${teacherUid}/${newAssessmentUid}`);

  // Check old key exists
  const oldSnap = await get(oldRef);
  if (!oldSnap.exists()) {
    throw new Error(`No answer key found for assessment UID "${oldAssessmentUid}"`);
  }

  // Block if new UID already taken
  const newSnap = await get(newRef);
  if (newSnap.exists()) {
    throw new Error(
      `Assessment UID "${newAssessmentUid}" already has an answer key. ` +
      `Choose a different UID.`
    );
  }

  const data = oldSnap.val();

  // Write to new key with updated assessment_uid field
  await set(newRef, {
    ...data,
    assessment_uid: newAssessmentUid,
    updated_at: Date.now(),
  });

  // Delete old key
  await remove(oldRef);
};