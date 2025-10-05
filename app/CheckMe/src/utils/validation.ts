// src/utils/validation.ts

/**
 * Validates if the email is a Gmail address
 * @param email - Email address to validate
 * @returns true if email ends with @gmail.com, false otherwise
 */
export const isGmailAddress = (email: string): boolean => {
  const trimmedEmail = email.trim().toLowerCase();
  return trimmedEmail.endsWith('@gmail.com');
};

/**
 * Validates email format
 * @param email - Email address to validate
 * @returns true if email format is valid
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validates password strength
 * @param password - Password to validate
 * @returns Object with isValid boolean and error message if invalid
 */
export const validatePassword = (password: string): { isValid: boolean; message?: string } => {
  if (password.length < 6) {
    return { isValid: false, message: 'Password must be at least 6 characters long' };
  }
  return { isValid: true };
};

/**
 * Validates username format
 * @param username - Username to validate
 * @returns Object with isValid boolean and error message if invalid
 */
export const validateUsername = (username: string): { isValid: boolean; message?: string } => {
  if (username.length < 3) {
    return { isValid: false, message: 'Username must be at least 3 characters long' };
  }
  
  if (username.length > 20) {
    return { isValid: false, message: 'Username must be no more than 20 characters' };
  }
  
  const usernameRegex = /^[a-zA-Z0-9_]+$/;
  if (!usernameRegex.test(username)) {
    return { isValid: false, message: 'Username can only contain letters, numbers, and underscores' };
  }
  
  return { isValid: true };
};

/**
 * Validates employee ID format
 * @param employeeId - Employee ID to validate
 * @returns Object with isValid boolean and error message if invalid
 */
export const validateEmployeeId = (employeeId: string): { isValid: boolean; message?: string } => {
  if (employeeId.trim().length === 0) {
    return { isValid: false, message: 'Employee ID is required' };
  }
  
  if (employeeId.length < 3) {
    return { isValid: false, message: 'Employee ID must be at least 3 characters long' };
  }
  
  return { isValid: true };
};