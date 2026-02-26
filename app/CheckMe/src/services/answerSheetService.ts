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

// ─────────────────────────────────────────────
// Answer Key monitoring & editing
// ─────────────────────────────────────────────

export interface AnswerKeyEntry {
  assessmentUid: string;
  assessmentName: string;       // from /assessments/ — "Unidentified" if no match
  totalQuestions: number;
  answers: Record<string, string>;    // { Q1: "A", Q2: "TRUE", ... }
  imageUrls: string[];
  createdAt: number;
  updatedAt: number;
  sectionUid: string;
  subjectUid: string;
  hasAnswerKey: true;
}

export interface AssessmentWithoutKey {
  assessmentUid: string;
  assessmentName: string;
  hasAnswerKey: false;
}

export type AnswerKeyListItem = AnswerKeyEntry | AssessmentWithoutKey;

/**
 * Loads all assessments for a subject and joins with /answer_keys/.
 * Returns a list where each item is either an AnswerKeyEntry (key exists)
 * or AssessmentWithoutKey (not yet scanned).
 */
export const getAnswerKeysForSubject = async (
  teacherUid: string,
  subjectUid: string
): Promise<AnswerKeyListItem[]> => {
  try {
    // Load assessments for this subject
    const assessmentsSnap = await get(ref(database, `assessments/${teacherUid}`));
    const assessments: Record<string, string> = {}; // uid → name
    if (assessmentsSnap.exists()) {
      const data = assessmentsSnap.val() as Record<string, any>;
      Object.entries(data).forEach(([uid, a]) => {
        if (a?.subjectUid === subjectUid || a?.subject_uid === subjectUid) {
          assessments[uid] = a?.assessmentName ?? a?.assessment_name ?? 'Unidentified';
        }
      });
    }

    // Load all answer keys for teacher
    const keysSnap = await get(ref(database, `answer_keys/${teacherUid}`));
    const keyMap: Record<string, any> = keysSnap.exists() ? keysSnap.val() : {};

    // Build result list — assessments for this subject only
    const result: AnswerKeyListItem[] = [];

    for (const [uid, name] of Object.entries(assessments)) {
      if (keyMap[uid]) {
        const k = keyMap[uid];
        const rawAnswers = k.answer_key ?? k.answers ?? {};
        // Sort answers numerically Q1, Q2 … Q10
        const sorted: Record<string, string> = {};
        Object.keys(rawAnswers)
          .sort((a, b) => parseInt(a.replace(/\D/g, '')) - parseInt(b.replace(/\D/g, '')))
          .forEach(q => { sorted[q] = rawAnswers[q]; });

        result.push({
          hasAnswerKey: true,
          assessmentUid: uid,
          assessmentName: name,
          totalQuestions: k.total_questions ?? Object.keys(rawAnswers).length,
          answers: sorted,
          imageUrls: parseImageUrls(k.image_urls),
          createdAt: k.created_at ?? 0,
          updatedAt: k.updated_at ?? 0,
          sectionUid: k.section_uid ?? '',
          subjectUid: k.subject_uid ?? subjectUid,
        });
      } else {
        result.push({ hasAnswerKey: false, assessmentUid: uid, assessmentName: name });
      }
    }

    // Sort: keyed first (by updatedAt desc), then unkeyed
    result.sort((a, b) => {
      if (a.hasAnswerKey && b.hasAnswerKey) return b.updatedAt - a.updatedAt;
      if (a.hasAnswerKey) return -1;
      if (b.hasAnswerKey) return 1;
      return 0;
    });

    return result;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to load answer keys');
  }
};

/**
 * Update a single question's correct answer in /answer_keys/.
 */
export const updateAnswerKeyAnswer = async (
  teacherUid: string,
  assessmentUid: string,
  questionKey: string,   // e.g. "Q3"
  newAnswer: string
): Promise<void> => {
  await update(
    ref(database, `answer_keys/${teacherUid}/${assessmentUid}/answer_key`),
    { [questionKey]: newAnswer, }
  );
  await update(
    ref(database, `answer_keys/${teacherUid}/${assessmentUid}`),
    { updated_at: Date.now() }
  );
};

/**
 * Delete an entire answer key.
 */
export const deleteAnswerKey = async (
  teacherUid: string,
  assessmentUid: string
): Promise<void> => {
  await remove(ref(database, `answer_keys/${teacherUid}/${assessmentUid}`));
};

/**
 * Re-scores all answer sheets for an assessment using an updated answer key.
 * Reads every sheet under /answer_sheets/{teacherUid}/{assessmentUid}/,
 * recomputes breakdown + total_score + is_final_score, and writes back.
 */
export const rescoreAnswerSheets = async (
  teacherUid: string,
  assessmentUid: string,
  updatedAnswerKey: Record<string, string>   // { Q1: "A", Q2: "B", ... }
): Promise<number> => {
  const sheetsSnap = await get(
    ref(database, `answer_sheets/${teacherUid}/${assessmentUid}`)
  );
  if (!sheetsSnap.exists()) return 0;

  const sheets = sheetsSnap.val() as Record<string, any>;
  let rescored = 0;

  for (const [studentId, sheet] of Object.entries(sheets)) {
    const studentAnswers: Record<string, string> = {};

    // Flatten breakdown back to student answers map
    const breakdown = sheet.breakdown ?? {};
    for (const [q, qData] of Object.entries(breakdown as Record<string, any>)) {
      studentAnswers[q] = qData?.student_answer ?? 'missing_answer';
    }

    // Recalculate
    let score = 0;
    let isFinal = true;
    const newBreakdown: Record<string, any> = {};

    for (const [q, correctAnswer] of Object.entries(updatedAnswerKey)) {
      const studentAnswer = studentAnswers[q] ?? 'missing_answer';

      if (studentAnswer === 'essay_answer') {
        isFinal = false;
        newBreakdown[q] = {
          student_answer: studentAnswer,
          correct_answer: 'will_check_by_teacher',
          checking_result: 'pending',
        };
      } else {
        const isCorrect = studentAnswer === correctAnswer;
        if (isCorrect) score++;
        newBreakdown[q] = {
          student_answer: studentAnswer,
          correct_answer: correctAnswer,
          checking_result: isCorrect,
        };
      }
    }

    await update(
      ref(database, `answer_sheets/${teacherUid}/${assessmentUid}/${studentId}`),
      {
        total_score: score,
        is_final_score: isFinal,
        breakdown: newBreakdown,
        updated_at: Date.now(),
      }
    );
    rescored++;
  }

  return rescored;
};

/**
 * Check how many answer sheets exist for an assessment.
 * Used to decide whether to show the re-score confirmation.
 */
export const getAnswerSheetCount = async (
  teacherUid: string,
  assessmentUid: string
): Promise<number> => {
  try {
    const snap = await get(ref(database, `answer_sheets/${teacherUid}/${assessmentUid}`));
    if (!snap.exists()) return 0;
    return Object.keys(snap.val()).length;
  } catch {
    return 0;
  }
};

// ─────────────────────────────────────────────
// Update individual student answer + re-score
// ─────────────────────────────────────────────

export interface StudentAnswerEdit {
  questionKey: string;          // e.g. "Q3"
  newStudentAnswer: string;     // corrected answer from teacher
  newCheckingResult: boolean | 'pending';
}

/**
 * Updates one or more student answers in a breakdown,
 * recalculates total_score and is_final_score, and writes back.
 *
 * Used by teacher to correct OCR errors or grade essays manually.
 */
export const updateStudentAnswerSheet = async (
  teacherUid: string,
  assessmentUid: string,
  studentId: string,
  edits: StudentAnswerEdit[],
  markFinal: boolean            // teacher decision: is this sheet now fully graded?
): Promise<{ newScore: number; newTotal: number }> => {
  // Read current sheet
  const snap = await get(
    ref(database, `answer_sheets/${teacherUid}/${assessmentUid}/${studentId}`)
  );
  if (!snap.exists()) throw new Error('Answer sheet not found');

  const sheet = snap.val() as any;
  const breakdown: Record<string, any> = { ...(sheet.breakdown ?? {}) };

  // Apply each edit
  for (const edit of edits) {
    if (!breakdown[edit.questionKey]) continue;
    breakdown[edit.questionKey] = {
      ...breakdown[edit.questionKey],
      student_answer: edit.newStudentAnswer,
      checking_result: edit.newCheckingResult,
    };
  }

  // Recalculate score from updated breakdown
  let newScore = 0;
  let hasPending = false;

  for (const qData of Object.values(breakdown) as any[]) {
    if (qData.checking_result === true) newScore++;
    if (qData.checking_result === 'pending') hasPending = true;
  }

  const isFinal = markFinal ? true : !hasPending;

  await update(
    ref(database, `answer_sheets/${teacherUid}/${assessmentUid}/${studentId}`),
    {
      breakdown,
      total_score: newScore,
      is_final_score: isFinal,
      updated_at: Date.now(),
    }
  );

  return { newScore, newTotal: sheet.total_questions };
};