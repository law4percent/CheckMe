// src/services/assessmentService.ts
import { ref, set, get, remove } from 'firebase/database';
import { database } from '../config/firebase';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface Assessment {
  assessmentUid: string;
  assessmentName: string;
  assessmentType: 'quiz' | 'exam';
  sectionUid: string;
  subjectUid: string;
  teacherId: string;
  createdAt: number;
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

/**
 * Generates a random 8-character alphanumeric UID e.g. "QWER1234"
 * Uses uppercase letters + digits only (no ambiguous chars like 0/O, 1/I)
 */
const generateAssessmentUid = (): string => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let result = '';
  for (let i = 0; i < 8; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
};

// ─────────────────────────────────────────────
// Service Functions
// ─────────────────────────────────────────────

/**
 * Create a new assessment.
 *
 * Writes to: /assessments/{teacherId}/{assessmentUid}/
 *   - created_at   : number (timestamp)
 *   - section_uid  : string
 *   - subject_uid  : string
 *
 * Also stores display metadata (name, type) alongside so the app
 * can render the assessment card without extra lookups.
 *
 * Returns the full Assessment object on success.
 */
export const createAssessment = async (
  teacherId: string,
  assessmentName: string,
  assessmentType: 'quiz' | 'exam',
  sectionUid: string,
  subjectUid: string
): Promise<Assessment> => {
  if (!teacherId) throw new Error('teacherId is required');
  if (!assessmentName.trim()) throw new Error('assessmentName is required');
  if (!sectionUid) throw new Error('sectionUid is required');
  if (!subjectUid) throw new Error('subjectUid is required');

  const assessmentUid = generateAssessmentUid();
  const createdAt = Date.now();

  const data = {
    assessmentName: assessmentName.trim(),
    assessmentType,
    created_at: createdAt,
    section_uid: sectionUid,
    subject_uid: subjectUid,
  };

  await set(
    ref(database, `assessments/${teacherId}/${assessmentUid}`),
    data
  );

  return {
    assessmentUid,
    assessmentName: assessmentName.trim(),
    assessmentType,
    sectionUid,
    subjectUid,
    teacherId,
    createdAt,
  };
};

/**
 * Get all assessments for a teacher, optionally filtered by subjectUid.
 *
 * Reads from: /assessments/{teacherId}/
 *
 * Returns array of Assessment objects.
 */
export const getAssessments = async (
  teacherId: string,
  subjectUid?: string
): Promise<Assessment[]> => {
  if (!teacherId) throw new Error('teacherId is required');

  const snapshot = await get(ref(database, `assessments/${teacherId}`));

  if (!snapshot.exists()) return [];

  const raw = snapshot.val() as Record<string, any>;

  const assessments: Assessment[] = Object.entries(raw).map(([uid, data]) => ({
    assessmentUid: uid,
    assessmentName: data.assessmentName ?? '',
    assessmentType: data.assessmentType ?? 'quiz',
    sectionUid: data.section_uid ?? '',
    subjectUid: data.subject_uid ?? '',
    teacherId,
    createdAt: data.created_at ?? 0,
  }));

  if (subjectUid) {
    return assessments.filter(a => a.subjectUid === subjectUid);
  }

  return assessments;
};

/**
 * Get a single assessment by UID.
 *
 * Reads from: /assessments/{teacherId}/{assessmentUid}
 *
 * Returns Assessment or null if not found.
 */
export const getAssessment = async (
  teacherId: string,
  assessmentUid: string
): Promise<Assessment | null> => {
  if (!teacherId || !assessmentUid) return null;

  const snapshot = await get(
    ref(database, `assessments/${teacherId}/${assessmentUid}`)
  );

  if (!snapshot.exists()) return null;

  const data = snapshot.val();

  return {
    assessmentUid,
    assessmentName: data.assessmentName ?? '',
    assessmentType: data.assessmentType ?? 'quiz',
    sectionUid: data.section_uid ?? '',
    subjectUid: data.subject_uid ?? '',
    teacherId,
    createdAt: data.created_at ?? 0,
  };
};

/**
 * Delete an assessment.
 *
 * Deletes: /assessments/{teacherId}/{assessmentUid}
 */
export const deleteAssessment = async (
  teacherId: string,
  assessmentUid: string
): Promise<void> => {
  if (!teacherId || !assessmentUid) throw new Error('teacherId and assessmentUid are required');

  // Cascade delete: assessment record + answer key + all answer sheets
  await Promise.all([
    remove(ref(database, `assessments/${teacherId}/${assessmentUid}`)),
    remove(ref(database, `answer_keys/${teacherId}/${assessmentUid}`)),
    remove(ref(database, `answer_sheets/${teacherId}/${assessmentUid}`)),
  ]);
};