// src/services/inviteCodeService.ts
import { ref, set, get, query, orderByChild, equalTo } from 'firebase/database';
import { database } from '../config/firebase';

export interface InviteCode {
  code: string;
  teacherId: string;
  subjectId: string;
  sectionId: string;
  subjectName: string;
  teacherName: string;
  sectionName: string;
  year: string;
  createdAt: number;
  expiresAt?: number;
}

/**
 * Generate a unique invite code
 */
const generateCode = (): string => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code = '';
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
};

/**
 * Create and store an invite code for a subject
 */
export const createInviteCode = async (
  teacherId: string,
  subjectId: string,
  sectionId: string,
  subjectName: string,
  teacherName: string,
  sectionName: string,
  year: string
): Promise<string> => {
  try {
    let code = generateCode();
    let isUnique = false;
    let attempts = 0;
    const maxAttempts = 10;

    // Ensure the code is unique
    while (!isUnique && attempts < maxAttempts) {
      const existingCode = await getInviteCodeByCode(code);
      if (!existingCode) {
        isUnique = true;
      } else {
        code = generateCode();
        attempts++;
      }
    }

    if (!isUnique) {
      throw new Error('Failed to generate unique invite code. Please try again.');
    }

    const inviteCode: InviteCode = {
      code,
      teacherId,
      subjectId,
      sectionId,
      subjectName,
      teacherName,
      sectionName,
      year,
      createdAt: Date.now()
    };

    // Store the invite code
    const inviteCodeRef = ref(database, `inviteCodes/${code}`);
    await set(inviteCodeRef, inviteCode);

    console.log('✅ [createInviteCode] Invite code created:', code);
    return code;
  } catch (error: any) {
    console.error('❌ [createInviteCode] Error:', error);
    throw new Error(error.message || 'Failed to create invite code');
  }
};

/**
 * Get invite code by code string
 */
export const getInviteCodeByCode = async (code: string): Promise<InviteCode | null> => {
  try {
    const inviteCodeRef = ref(database, `inviteCodes/${code}`);
    const snapshot = await get(inviteCodeRef);

    if (!snapshot.exists()) {
      return null;
    }

    const inviteCode = snapshot.val() as InviteCode;

    // Check if code is expired (if expiresAt is set)
    if (inviteCode.expiresAt && inviteCode.expiresAt < Date.now()) {
      return null;
    }

    return inviteCode;
  } catch (error: any) {
    console.error('❌ [getInviteCodeByCode] Error:', error);
    throw new Error(error.message || 'Failed to fetch invite code');
  }
};

/**
 * Get all invite codes for a subject
 */
export const getSubjectInviteCodes = async (
  teacherId: string,
  subjectId: string
): Promise<InviteCode[]> => {
  try {
    const inviteCodesRef = ref(database, 'inviteCodes');
    const snapshot = await get(inviteCodesRef);

    if (!snapshot.exists()) {
      return [];
    }

    const allCodes = snapshot.val();
    const subjectCodes: InviteCode[] = [];

    Object.values(allCodes).forEach((code: any) => {
      if (code.teacherId === teacherId && code.subjectId === subjectId) {
        // Filter out expired codes
        if (!code.expiresAt || code.expiresAt > Date.now()) {
          subjectCodes.push(code as InviteCode);
        }
      }
    });

    return subjectCodes.sort((a, b) => b.createdAt - a.createdAt);
  } catch (error: any) {
    console.error('❌ [getSubjectInviteCodes] Error:', error);
    throw new Error(error.message || 'Failed to fetch subject invite codes');
  }
};

/**
 * Validate an invite code
 */
export const validateInviteCode = async (code: string): Promise<{
  valid: boolean;
  inviteCode?: InviteCode;
  error?: string;
}> => {
  try {
    const inviteCode = await getInviteCodeByCode(code);

    if (!inviteCode) {
      return {
        valid: false,
        error: 'Invalid or expired invite code'
      };
    }

    return {
      valid: true,
      inviteCode
    };
  } catch (error: any) {
    return {
      valid: false,
      error: error.message || 'Failed to validate invite code'
    };
  }
};