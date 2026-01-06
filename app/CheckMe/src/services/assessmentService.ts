// src/services/assessmentService.ts

export interface Assessment {
  assessmentUid: string;
  assessmentName: string;
  assessmentType: 'quiz' | 'exam';
  subjectId: string;
  subjectName: string;
  sectionId: string;
  sectionName: string;
  year: string;
  teacherId: string;
  createdAt: number;
  status: 'active' | 'completed';
}

const FIREBASE_URL = 'https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app';
const FIXED_ASSESSMENT_UID = 'QWER1234'; // Fixed for testing

/**
 * Create a new assessment
 * For testing: Only one assessment can be created with fixed UID QWER1234
 */
export const createAssessment = async (
  teacherId: string,
  assessmentName: string,
  assessmentType: 'quiz' | 'exam',
  subjectId: string,
  subjectName: string,
  sectionId: string,
  sectionName: string,
  year: string
): Promise<Assessment> => {
  try {
    console.log('📝 [AssessmentService] Creating assessment...');
    console.log('  - teacherId:', teacherId);
    console.log('  - sectionId:', sectionId);
    console.log('  - subjectId:', subjectId);
    console.log('  - assessmentName:', assessmentName);
    console.log('  - assessmentType:', assessmentType);
    console.log('  - assessmentUid:', FIXED_ASSESSMENT_UID);

    // Check if assessment already exists
    const checkUrl = `${FIREBASE_URL}/assessments/${teacherId}/${sectionId}/${subjectId}/${FIXED_ASSESSMENT_UID}.json`;
    const checkResponse = await fetch(checkUrl);
    const existingData = await checkResponse.json();

    if (existingData) {
      throw new Error('Assessment already exists. Only one test assessment can be created with UID QWER1234');
    }

    // Create assessment object (matching your RTDB structure)
    const assessmentData = {
      assessmentUid: FIXED_ASSESSMENT_UID,
      assessmentName,
      assessmentType,
      createdAt: Date.now()
    };

    // Save to Firebase at correct path: /assessments/{teacherId}/{sectionId}/{subjectId}/{assessmentUid}
    const url = `${FIREBASE_URL}/assessments/${teacherId}/${sectionId}/${subjectId}/${FIXED_ASSESSMENT_UID}.json`;
    
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(assessmentData)
    });

    if (!response.ok) {
      throw new Error(`Failed to create assessment: ${response.statusText}`);
    }

    // Return full assessment object
    const assessment: Assessment = {
      ...assessmentData,
      subjectId,
      subjectName,
      sectionId,
      sectionName,
      year,
      teacherId,
      status: 'active'
    };

    console.log('✅ [AssessmentService] Assessment created successfully');
    console.log('  - Path:', `/assessments/${teacherId}/${sectionId}/${subjectId}/${FIXED_ASSESSMENT_UID}`);

    return assessment;

  } catch (error: any) {
    console.error('❌ [AssessmentService] Error creating assessment:', error);
    throw error;
  }
};

/**
 * Get assessment details for a specific subject
 * Fetches from /assessments/{teacherId}/{sectionId}/{subjectId}/{assessmentUid}
 */
export const getAssessment = async (
  teacherId: string,
  sectionId: string,
  subjectId: string,
  assessmentUid: string = FIXED_ASSESSMENT_UID
): Promise<Assessment | null> => {
  try {
    console.log('📋 [AssessmentService] Fetching assessment...');
    console.log('  - teacherId:', teacherId);
    console.log('  - sectionId:', sectionId);
    console.log('  - subjectId:', subjectId);
    console.log('  - assessmentUid:', assessmentUid);

    const url = `${FIREBASE_URL}/assessments/${teacherId}/${sectionId}/${subjectId}/${assessmentUid}.json`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      console.log('❌ [AssessmentService] Failed to fetch assessment:', response.statusText);
      return null;
    }

    const data = await response.json();
    
    // If data is null or doesn't have required fields, return null
    if (!data || !data.assessmentUid) {
      console.log('📋 [AssessmentService] No assessment found or invalid data');
      return null;
    }

    // Get additional data from subjects to complete the Assessment object
    const subjectUrl = `${FIREBASE_URL}/subjects/${teacherId}/${sectionId}/${subjectId}.json`;
    const subjectResponse = await fetch(subjectUrl);
    const subjectData = await subjectResponse.json();

    const assessment: Assessment = {
      assessmentUid: data.assessmentUid,
      assessmentName: data.assessmentName,
      assessmentType: data.assessmentType || 'quiz',
      subjectId: subjectId,
      subjectName: subjectData?.subjectName || 'Unknown Subject',
      sectionId: sectionId,
      sectionName: subjectData?.sectionName || 'Unknown Section',
      year: subjectData?.year || 'Unknown',
      teacherId: teacherId,
      createdAt: data.createdAt,
      status: 'active'
    };

    console.log('✅ [AssessmentService] Assessment found:', assessment.assessmentUid);
    return assessment;

  } catch (error: any) {
    console.error('❌ [AssessmentService] Error fetching assessment:', error);
    return null;
  }
};

/**
 * Delete assessment (for testing - to reset)
 */
export const deleteAssessment = async (
  teacherId: string,
  sectionId: string,
  subjectId: string,
  assessmentUid: string = FIXED_ASSESSMENT_UID
): Promise<void> => {
  try {
    console.log('🗑️ [AssessmentService] Deleting assessment...');
    
    // Delete from assessments node
    const assessmentUrl = `${FIREBASE_URL}/assessments/${teacherId}/${sectionId}/${subjectId}/${assessmentUid}.json`;
    const assessmentResponse = await fetch(assessmentUrl, {
      method: 'DELETE'
    });

    if (!assessmentResponse.ok) {
      throw new Error(`Failed to delete assessment: ${assessmentResponse.statusText}`);
    }

    // Also delete from assessmentScoresAndImages if exists
    const scoresUrl = `${FIREBASE_URL}/assessmentScoresAndImages/${teacherId}/${assessmentUid}.json`;
    await fetch(scoresUrl, {
      method: 'DELETE'
    });

    console.log('✅ [AssessmentService] Assessment deleted successfully');

  } catch (error: any) {
    console.error('❌ [AssessmentService] Error deleting assessment:', error);
    throw error;
  }
};

/**
 * Get all student scores for an assessment
 */
export const getAssessmentScores = async (
  teacherId: string,
  assessmentUid: string = FIXED_ASSESSMENT_UID
): Promise<any> => {
  try {
    const url = `${FIREBASE_URL}/assessmentScoresAndImages/${teacherId}/${assessmentUid}.json`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch scores: ${response.statusText}`);
    }

    const data = await response.json();
    
    if (!data) {
      return {};
    }

    // Return all student scores (each key is a studentId)
    return data;

  } catch (error: any) {
    console.error('❌ [AssessmentService] Error fetching scores:', error);
    return {};
  }
};