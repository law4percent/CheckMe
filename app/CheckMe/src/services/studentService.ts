// src/services/studentService.ts
import { ref, get, query, orderByChild, equalTo } from 'firebase/database';
import { database } from '../config/firebase';

export interface StudentSearchResult {
  uid: string;
  firstName: string;
  lastName: string;
  fullName: string;
  email: string;
  studentId: string;
  username: string;
}

/**
 * Search for a student by email
 */
export const searchStudentByEmail = async (email: string): Promise<StudentSearchResult | null> => {
  try {
    console.log('🔍 [searchStudentByEmail] Searching for:', email);
    
    const searchEmail = email.toLowerCase().trim();
    const studentsRef = ref(database, 'users/students');
    const snapshot = await get(studentsRef);
    
    if (!snapshot.exists()) {
      console.log('  - No students found in database');
      return null;
    }
    
    const studentsData = snapshot.val();
    
    // Iterate through all students to find matching email
    for (const [uid, studentData] of Object.entries(studentsData)) {
      const student = studentData as any;
      
      if (student.email && student.email.toLowerCase() === searchEmail) {
        console.log('✅ [searchStudentByEmail] Student found:', student.fullName);
        
        return {
          uid: uid,
          firstName: student.firstName,
          lastName: student.lastName,
          fullName: student.fullName,
          email: student.email,
          studentId: student.studentId,
          username: student.username
        };
      }
    }
    
    console.log('  - No student found with email:', email);
    return null;
  } catch (error: any) {
    console.error('❌ [searchStudentByEmail] Error:', error);
    throw new Error(error.message || 'Failed to search for student');
  }
};

/**
 * Send direct invitation to a student (auto-approved)
 */
export const sendDirectInvite = async (
  teacherId: string,
  subjectId: string,
  studentUid: string,
  studentName: string,
  studentEmail: string
): Promise<void> => {
  try {
    console.log('📧 [sendDirectInvite] Sending invite (auto-approved)');
    console.log('  - Teacher ID:', teacherId);
    console.log('  - Subject ID:', subjectId);
    console.log('  - Student UID:', studentUid);
    
    const { ref, set } = require('firebase/database');
    const { database } = require('../config/firebase');
    const { Enrollment } = require('./enrollmentService');
    
    // Create enrollment directly with approved status
    const enrollmentRef = ref(database, `enrollments/${teacherId}/${subjectId}/${studentUid}`);
    
    const enrollment = {
      studentId: studentUid,
      subjectId: subjectId,
      status: 'approved',
      joinedAt: Date.now(),
      approvedAt: Date.now(),
      studentName: studentName,
      studentEmail: studentEmail
    };

    await set(enrollmentRef, enrollment);
    
    console.log('✅ [sendDirectInvite] Student auto-approved and enrolled');
  } catch (error: any) {
    console.error('❌ [sendDirectInvite] Error:', error);
    throw new Error(error.message || 'Failed to send invitation');
  }
};