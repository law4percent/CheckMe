// src/services/subjectService.ts
import { ref, set, get, update, remove, push } from 'firebase/database';
import { database } from '../config/firebase';

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

export interface CreateSubjectData {
  year: string;
  subjectName: string;
  teacherId: string;
  sectionId: string;
}

export interface UpdateSubjectData {
  year?: string;
  subjectName?: string;
}

/**
 * Generate a unique subject code
 */
const generateSubjectCode = (teacherUsername: string, sectionName: string): string => {
  const randomString = Math.random().toString(36).substring(2, 6).toUpperCase();
  const shortSection = sectionName.substring(0, 4).toUpperCase();
  return `${teacherUsername}-${shortSection}-${randomString}`;
};

/**
 * Create a new subject
 */
export const createSubject = async (data: CreateSubjectData & { teacherUsername?: string; sectionName?: string }): Promise<Subject> => {
  try {
    const path = `subjects/${data.teacherId}/${data.sectionId}`;
    console.log('📚 [createSubject] Creating subject');
    console.log('  - Path:', path);
    console.log('  - Data:', data);
    
    const subjectsRef = ref(database, path);
    const newSubjectRef = push(subjectsRef);
    
    console.log('  - New subject key:', newSubjectRef.key);
    
    // Generate subject code if teacher username and section name are provided
    const subjectCode = data.teacherUsername && data.sectionName
      ? generateSubjectCode(data.teacherUsername, data.sectionName)
      : null; // Changed from undefined to null to avoid Firebase error
    
    console.log('  - Generated subject code:', subjectCode);
    
    const subject: Subject = {
      id: newSubjectRef.key!,
      year: data.year.trim(),
      subjectName: data.subjectName.trim(),
      ...(subjectCode && { subjectCode }), // Only include subjectCode if it's not null
      studentCount: 0,
      teacherId: data.teacherId,
      sectionId: data.sectionId,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    console.log('  - Subject object:', subject);
    console.log('  - Writing to Firebase...');
    
    await set(newSubjectRef, subject);
    
    console.log('✅ [createSubject] Subject created successfully');
    return subject;
  } catch (error: any) {
    console.error('❌ [createSubject] Error:', error);
    console.error('  - Error code:', error.code);
    console.error('  - Error message:', error.message);
    console.error('  - Full error:', error);
    throw new Error(error.message || 'Failed to create subject');
  }
};

/**
 * Get all subjects for a section
 */
export const getSectionSubjects = async (
  teacherId: string,
  sectionId: string
): Promise<Subject[]> => {
  try {
    const subjectsRef = ref(database, `subjects/${teacherId}/${sectionId}`);
    const snapshot = await get(subjectsRef);
    
    if (!snapshot.exists()) {
      return [];
    }

    const subjectsData = snapshot.val();
    const subjects: Subject[] = Object.values(subjectsData);
    
    // Sort by createdAt (newest first)
    return subjects.sort((a, b) => b.createdAt - a.createdAt);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch subjects');
  }
};

/**
 * Get a single subject by ID
 */
export const getSubjectById = async (
  teacherId: string,
  sectionId: string,
  subjectId: string
): Promise<Subject | null> => {
  try {
    const subjectRef = ref(database, `subjects/${teacherId}/${sectionId}/${subjectId}`);
    const snapshot = await get(subjectRef);
    
    if (!snapshot.exists()) {
      return null;
    }

    return snapshot.val() as Subject;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch subject');
  }
};

/**
 * Update a subject
 */
export const updateSubject = async (
  teacherId: string,
  sectionId: string,
  subjectId: string,
  data: UpdateSubjectData
): Promise<void> => {
  try {
    const subjectRef = ref(database, `subjects/${teacherId}/${sectionId}/${subjectId}`);
    
    const updates: any = {
      ...data,
      updatedAt: Date.now()
    };

    // Trim strings if they exist
    if (updates.year) updates.year = updates.year.trim();
    if (updates.subjectName) updates.subjectName = updates.subjectName.trim();

    await update(subjectRef, updates);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to update subject');
  }
};

/**
 * Delete a subject
 */
export const deleteSubject = async (
  teacherId: string,
  sectionId: string,
  subjectId: string
): Promise<void> => {
  try {
    const subjectRef = ref(database, `subjects/${teacherId}/${sectionId}/${subjectId}`);
    await remove(subjectRef);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to delete subject');
  }
};

/**
 * Update student count for a subject
 */
export const updateSubjectStudentCount = async (
  teacherId: string,
  sectionId: string,
  subjectId: string,
  count: number
): Promise<void> => {
  try {
    const subjectRef = ref(database, `subjects/${teacherId}/${sectionId}/${subjectId}`);
    await update(subjectRef, {
      studentCount: count,
      updatedAt: Date.now()
    });
  } catch (error: any) {
    throw new Error(error.message || 'Failed to update student count');
  }
};