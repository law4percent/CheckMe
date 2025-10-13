// src/services/sectionService.ts
import { ref, set, get, update, remove, push } from 'firebase/database';
import { database } from '../config/firebase';

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

/**
 * Create a new section
 */
export const createSection = async (data: CreateSectionData): Promise<Section> => {
  try {
    const sectionsRef = ref(database, `sections/${data.teacherId}`);
    const newSectionRef = push(sectionsRef);
    
    const section: Section = {
      id: newSectionRef.key!,
      year: data.year.trim(),
      sectionName: data.sectionName.trim(),
      subjectCount: 0,
      teacherId: data.teacherId,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    await set(newSectionRef, section);
    return section;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to create section');
  }
};

/**
 * Get all sections for a teacher
 */
export const getTeacherSections = async (teacherId: string): Promise<Section[]> => {
  try {
    const sectionsRef = ref(database, `sections/${teacherId}`);
    const snapshot = await get(sectionsRef);
    
    if (!snapshot.exists()) {
      return [];
    }

    const sectionsData = snapshot.val();
    const sections: Section[] = Object.values(sectionsData);
    
    // Sort by createdAt (newest first)
    return sections.sort((a, b) => b.createdAt - a.createdAt);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch sections');
  }
};

/**
 * Get a single section by ID
 */
export const getSectionById = async (
  teacherId: string,
  sectionId: string
): Promise<Section | null> => {
  try {
    const sectionRef = ref(database, `sections/${teacherId}/${sectionId}`);
    const snapshot = await get(sectionRef);
    
    if (!snapshot.exists()) {
      return null;
    }

    return snapshot.val() as Section;
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch section');
  }
};

/**
 * Update a section
 */
export const updateSection = async (
  teacherId: string,
  sectionId: string,
  data: UpdateSectionData
): Promise<void> => {
  try {
    const sectionRef = ref(database, `sections/${teacherId}/${sectionId}`);
    
    const updates: any = {
      ...data,
      updatedAt: Date.now()
    };

    // Trim strings if they exist
    if (updates.year) updates.year = updates.year.trim();
    if (updates.sectionName) updates.sectionName = updates.sectionName.trim();

    await update(sectionRef, updates);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to update section');
  }
};

/**
 * Delete a section and all its associated subjects (cascade delete)
 */
export const deleteSection = async (
  teacherId: string,
  sectionId: string
): Promise<void> => {
  try {
    // First, delete all subjects associated with this section
    const subjectsRef = ref(database, `subjects/${teacherId}/${sectionId}`);
    await remove(subjectsRef);
    
    // Then, delete the section itself
    const sectionRef = ref(database, `sections/${teacherId}/${sectionId}`);
    await remove(sectionRef);
  } catch (error: any) {
    throw new Error(error.message || 'Failed to delete section');
  }
};

/**
 * Update subject count for a section
 */
export const updateSectionSubjectCount = async (
  teacherId: string,
  sectionId: string,
  count: number
): Promise<void> => {
  try {
    const sectionRef = ref(database, `sections/${teacherId}/${sectionId}`);
    await update(sectionRef, {
      subjectCount: count,
      updatedAt: Date.now()
    });
  } catch (error: any) {
    throw new Error(error.message || 'Failed to update subject count');
  }
};