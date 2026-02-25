// src/services/answerSheetService.ts
import { ref, get, update } from 'firebase/database';
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