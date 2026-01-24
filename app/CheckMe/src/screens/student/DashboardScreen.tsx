// src/screens/student/DashboardScreen.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Modal,
  ActivityIndicator,
  RefreshControl,
  TextInput
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../contexts/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import { joinSubjectWithCode, getStudentEnrollments } from '../../services/enrollmentService';

type Props = NativeStackScreenProps<RootStackParamList, 'StudentDashboard'>;

interface EnrolledSubject {
  id: string;
  subjectName: string;
  subjectCode: string;
  teacherName: string;
  sectionName: string;
  year: string;
  teacherId: string; // Added to fetch assessments
  sectionId?: string; // Also helpful for filtering
}

interface StudentAssessment {
  assessmentUid: string;
  assessmentName: string;
  score: number;
  perfectScore: number;
  percentage: number;
  scannedAt: string;
  subjectName: string;
  teacherName: string;
  isPartialScore: boolean;
}

const StudentDashboardScreen: React.FC<Props> = ({ navigation }) => {
  const { user, signOut } = useAuth();
  
  // State
  const [enrolledSubjects, setEnrolledSubjects] = useState<EnrolledSubject[]>([]);
  const [recentAssessments, setRecentAssessments] = useState<StudentAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingAssessments, setLoadingAssessments] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [profileModalVisible, setProfileModalVisible] = useState(false);
  const [joinSubjectModalVisible, setJoinSubjectModalVisible] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [joiningSubject, setJoiningSubject] = useState(false);
  
  // Subject Scores Modal State
  const [subjectScoresModalVisible, setSubjectScoresModalVisible] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<EnrolledSubject | null>(null);
  const [subjectAssessments, setSubjectAssessments] = useState<StudentAssessment[]>([]);
  const [loadingSubjectScores, setLoadingSubjectScores] = useState(false);

  useEffect(() => {
    if (user?.uid) {
      loadStudentData();
    }
  }, [user?.uid]);

  const loadStudentData = async () => {
    await loadEnrolledSubjects();
    await loadRecentAssessments();
  };

  const loadEnrolledSubjects = async () => {
    if (!user?.uid) return;
    
    try {
      setLoading(true);
      console.log('📚 [StudentDashboard] Loading enrolled subjects...');
      
      // Fetch enrollments directly from Firebase to get teacherId
      const enrollmentsUrl = 'https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/enrollments.json';
      const response = await fetch(enrollmentsUrl);
      
      if (!response.ok) {
        throw new Error('Failed to fetch enrollments');
      }

      const enrollmentsData = await response.json();
      
      if (!enrollmentsData) {
        console.log('📚 No enrollments found');
        setEnrolledSubjects([]);
        return;
      }

      // Fetch invite codes to get subject details
      const inviteCodesUrl = 'https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/inviteCodes.json';
      const inviteCodesResponse = await fetch(inviteCodesUrl);
      const inviteCodes = inviteCodesResponse.ok ? await inviteCodesResponse.json() : {};

      // Create a map of subjectId to subject details
      const subjectDetailsMap: { [key: string]: any } = {};
      if (inviteCodes) {
        Object.values(inviteCodes).forEach((inviteCode: any) => {
          if (inviteCode && inviteCode.subjectId) {
            subjectDetailsMap[inviteCode.subjectId] = {
              subjectName: inviteCode.subjectName,
              teacherName: inviteCode.teacherName,
              sectionName: inviteCode.sectionName,
              sectionId: inviteCode.sectionId,
              year: inviteCode.year,
              subjectCode: inviteCode.code,
              teacherId: inviteCode.teacherId
            };
          }
        });
      }

      const subjects: EnrolledSubject[] = [];

      // Iterate through all teachers
      Object.keys(enrollmentsData).forEach((teacherId) => {
        const teacherEnrollments = enrollmentsData[teacherId];
        
        // Iterate through all subjects
        Object.keys(teacherEnrollments).forEach((subjectId) => {
          const subjectEnrollments = teacherEnrollments[subjectId];
          
          // Check if student is enrolled in this subject
          if (subjectEnrollments[user.uid]) {
            const enrollment = subjectEnrollments[user.uid];
            
            // Only include approved enrollments
            if (enrollment.status === 'approved') {
              const subjectDetails = subjectDetailsMap[subjectId] || {
                subjectName: 'Unknown Subject',
                teacherName: 'Unknown Teacher',
                sectionName: 'Unknown Section',
                sectionId: '',
                year: '',
                subjectCode: '',
                teacherId: teacherId // Use the key as fallback
              };
              
              subjects.push({
                id: subjectId,
                subjectName: subjectDetails.subjectName,
                subjectCode: subjectDetails.subjectCode,
                teacherName: subjectDetails.teacherName,
                sectionName: subjectDetails.sectionName,
                year: subjectDetails.year,
                teacherId: teacherId, // This is the key! Use the parent key
                sectionId: subjectDetails.sectionId
              });
            }
          }
        });
      });
      
      console.log('✅ [StudentDashboard] Loaded approved subjects:', subjects.length);
      console.log('✅ [StudentDashboard] Subjects with teacherId:', subjects);
      setEnrolledSubjects(subjects);
    } catch (error: any) {
      console.error('❌ [StudentDashboard] Error loading subjects:', error);
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadRecentAssessments = async () => {
    if (!user?.uid) return;

    try {
      setLoadingAssessments(true);
      console.log('📊 [StudentDashboard] Loading recent assessments...');
      console.log('  - studentId:', user.uid);

      const studentId = user.role === 'student' ? user.studentId : user.uid;
      
      // Fetch all teachers from enrollments to get their IDs
      const enrollmentsUrl = `https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/enrollments.json`;
      const enrollmentsResponse = await fetch(enrollmentsUrl);
      
      if (!enrollmentsResponse.ok) {
        throw new Error('Failed to fetch enrollments');
      }

      const enrollmentsData = await enrollmentsResponse.json();
      
      if (!enrollmentsData) {
        console.log('📊 [StudentDashboard] No enrollments found');
        setRecentAssessments([]);
        return;
      }

      // Find all teachers this student is enrolled with (only approved enrollments)
      const teacherIds = new Set<string>();
      const subjectMap = new Map<string, { subjectName: string, teacherName: string }>();

      Object.keys(enrollmentsData).forEach(teacherId => {
        const teacherEnrollments = enrollmentsData[teacherId];
        
        Object.keys(teacherEnrollments).forEach(subjectId => {
          const students = teacherEnrollments[subjectId];
          
          // Only include if student exists AND status is approved
          if (students[user.uid] && students[user.uid].status === 'approved') {
            teacherIds.add(teacherId);
            
            // Store subject info for later use
            const enrollment = students[user.uid];
            subjectMap.set(subjectId, {
              subjectName: enrollment.subjectName || 'Unknown Subject',
              teacherName: enrollment.teacherName || 'Unknown Teacher'
            });
          }
        });
      });

      console.log('  - Found teachers:', teacherIds.size);

      const assessments: StudentAssessment[] = [];

      // For each teacher, fetch scores for this student
      for (const teacherId of teacherIds) {
        try {
          const scoresUrl = `https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/assessmentScoresAndImages/${teacherId}.json`;
          const scoresResponse = await fetch(scoresUrl);
          
          if (!scoresResponse.ok) continue;

          const scoresData = await scoresResponse.json();
          
          if (!scoresData) continue;

          // Iterate through all assessments for this teacher
          Object.keys(scoresData).forEach(assessmentUid => {
            const assessmentScores = scoresData[assessmentUid];
            
            // Check if this student has a score for this assessment
            if (assessmentScores[studentId]) {
              const studentScore = assessmentScores[studentId];
              
              // Fetch assessment details to get the name
              fetchAssessmentDetails(teacherId, assessmentUid).then(assessmentName => {
                const percentage = Math.round((studentScore.score / studentScore.perfectScore) * 100);
                
                assessments.push({
                  assessmentUid,
                  assessmentName: assessmentName || `Assessment ${assessmentUid}`,
                  score: studentScore.score,
                  perfectScore: studentScore.perfectScore,
                  percentage,
                  scannedAt: studentScore.scannedAt,
                  subjectName: 'Subject', // Will be updated if we can map it
                  teacherName: 'Teacher', // Will be updated if we can map it
                  isPartialScore: studentScore.isPartialScore || false
                });

                // Sort by date (newest first) and update state
                assessments.sort((a, b) => {
                  const dateA = parseScannedDate(a.scannedAt);
                  const dateB = parseScannedDate(b.scannedAt);
                  return dateB.getTime() - dateA.getTime();
                });

                // Keep only recent 10 assessments
                setRecentAssessments(assessments.slice(0, 10));
              });
            }
          });
        } catch (error) {
          console.error(`❌ Error fetching scores for teacher ${teacherId}:`, error);
        }
      }

      console.log('✅ [StudentDashboard] Loaded assessments:', assessments.length);

    } catch (error: any) {
      console.error('❌ [StudentDashboard] Error loading assessments:', error);
    } finally {
      setLoadingAssessments(false);
    }
  };

  // Helper function to fetch assessment name
  const fetchAssessmentDetails = async (teacherId: string, assessmentUid: string): Promise<string> => {
    try {
      const assessmentsUrl = `https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/assessments/${teacherId}.json`;
      const response = await fetch(assessmentsUrl);
      
      if (!response.ok) return assessmentUid;

      const data = await response.json();
      
      if (!data) return assessmentUid;

      // Search through sections and subjects
      for (const sectionId of Object.keys(data)) {
        const section = data[sectionId];
        
        for (const subjectId of Object.keys(section)) {
          const subject = section[subjectId];
          
          if (subject[assessmentUid]) {
            return subject[assessmentUid].assessmentName || assessmentUid;
          }
        }
      }

      return assessmentUid;
    } catch (error) {
      console.error('Error fetching assessment details:', error);
      return assessmentUid;
    }
  };

  // Parse scannedAt date (format: "MM/DD/YYYY HH:MM:SS")
  const parseScannedDate = (scannedAt: string): Date => {
    try {
      const [datePart, timePart] = scannedAt.split(' ');
      const [month, day, year] = datePart.split('/');
      const [hour, minute, second] = timePart.split(':');
      
      return new Date(
        parseInt(year),
        parseInt(month) - 1,
        parseInt(day),
        parseInt(hour),
        parseInt(minute),
        parseInt(second)
      );
    } catch (e) {
      return new Date();
    }
  };

  const formatDate = (scannedAt: string): string => {
    try {
      const date = parseScannedDate(scannedAt);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch (e) {
      return scannedAt;
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadStudentData();
    setRefreshing(false);
  };

  const handleSignOut = async () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        {
          text: 'Cancel',
          style: 'cancel'
        },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: async () => {
            try {
              await signOut();
            } catch (error: any) {
              Alert.alert('Error', error.message);
            }
          }
        }
      ]
    );
  };

  const handleOpenProfile = () => {
    setProfileModalVisible(true);
  };

  const handleCloseProfile = () => {
    setProfileModalVisible(false);
  };

  const handleJoinSubject = () => {
    setInviteCode('');
    setJoinSubjectModalVisible(true);
  };

  const handleOpenSubjectScores = async (subject: EnrolledSubject) => {
    setSelectedSubject(subject);
    setSubjectScoresModalVisible(true);
    await loadSubjectScores(subject);
  };

  const handleCloseSubjectScores = () => {
    setSubjectScoresModalVisible(false);
    setSelectedSubject(null);
    setSubjectAssessments([]);
  };

  const loadSubjectScores = async (subject: EnrolledSubject) => {
    if (!user?.uid || !subject.teacherId) {
      console.error('❌ Missing user ID or teacher ID');
      console.log('  - User ID:', user?.uid);
      console.log('  - Teacher ID:', subject.teacherId);
      setLoadingSubjectScores(false);
      return;
    }

    try {
      setLoadingSubjectScores(true);
      console.log('📊 [StudentDashboard] Loading subject scores...');
      console.log('  - Subject:', subject.subjectName);
      console.log('  - Subject ID:', subject.id);
      console.log('  - Teacher ID:', subject.teacherId);
      console.log('  - Section ID:', subject.sectionId);

      const studentId = user.role === 'student' ? user.studentId : user.uid;
      console.log('  - Student ID:', studentId);
      
      // Fetch all assessments for this teacher
      const assessmentsUrl = `https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/assessments/${subject.teacherId}.json`;
      console.log('  - Assessments URL:', assessmentsUrl);
      
      const assessmentsResponse = await fetch(assessmentsUrl);
      
      if (!assessmentsResponse.ok) {
        console.error('❌ Failed to fetch assessments');
        throw new Error('Failed to fetch assessments');
      }

      const assessmentsData = await assessmentsResponse.json();
      
      if (!assessmentsData) {
        console.log('📊 No assessments found for this teacher');
        setSubjectAssessments([]);
        setLoadingSubjectScores(false);
        return;
      }

      console.log('📊 Assessments data structure:', Object.keys(assessmentsData));

      // Find assessments for this specific subject
      const subjectAssessmentsList: StudentAssessment[] = [];
      let assessmentsFound = 0;
      
      Object.keys(assessmentsData).forEach(sectionId => {
        const section = assessmentsData[sectionId];
        console.log(`  - Checking section: ${sectionId}`);
        
        Object.keys(section).forEach(subjectId => {
          console.log(`    - Checking subject: ${subjectId} (looking for ${subject.id})`);
          
          // Only process if this is the selected subject
          if (subjectId === subject.id) {
            console.log('    ✅ Found matching subject!');
            const subjectData = section[subjectId];
            
            Object.keys(subjectData).forEach(assessmentUid => {
              assessmentsFound++;
              const assessment = subjectData[assessmentUid];
              console.log(`      - Found assessment: ${assessment.assessmentName} (${assessmentUid})`);
              
              // Now check if student has a score for this assessment
              fetchScoreForAssessment(
                subject.teacherId,
                assessmentUid,
                studentId,
                assessment.assessmentName,
                subject.subjectName,
                subject.teacherName,
                subjectAssessmentsList
              );
            });
          }
        });
      });

      console.log(`📊 Total assessments found for subject: ${assessmentsFound}`);

      // Wait a bit for all async fetches to complete
      setTimeout(() => {
        console.log(`📊 Scores retrieved: ${subjectAssessmentsList.length}`);
        
        // Sort by date (newest first)
        subjectAssessmentsList.sort((a, b) => {
          const dateA = parseScannedDate(a.scannedAt);
          const dateB = parseScannedDate(b.scannedAt);
          return dateB.getTime() - dateA.getTime();
        });

        setSubjectAssessments(subjectAssessmentsList);
        setLoadingSubjectScores(false);
      }, 1500); // Increased timeout to allow fetches to complete

    } catch (error: any) {
      console.error('❌ [StudentDashboard] Error loading subject scores:', error);
      Alert.alert('Error', error.message || 'Failed to load subject scores');
      setLoadingSubjectScores(false);
    }
  };

  const fetchScoreForAssessment = async (
    teacherId: string,
    assessmentUid: string,
    studentId: string,
    assessmentName: string,
    subjectName: string,
    teacherName: string,
    resultArray: StudentAssessment[]
  ) => {
    try {
      const scoreUrl = `https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/assessmentScoresAndImages/${teacherId}/${assessmentUid}/${studentId}.json`;
      const scoreResponse = await fetch(scoreUrl);
      
      if (!scoreResponse.ok) return;

      const scoreData = await scoreResponse.json();
      
      if (!scoreData) return;

      const percentage = Math.round((scoreData.score / scoreData.perfectScore) * 100);
      
      resultArray.push({
        assessmentUid,
        assessmentName: assessmentName || `Assessment ${assessmentUid}`,
        score: scoreData.score,
        perfectScore: scoreData.perfectScore,
        percentage,
        scannedAt: scoreData.scannedAt,
        subjectName,
        teacherName,
        isPartialScore: scoreData.isPartialScore || false
      });
    } catch (error) {
      console.error(`Error fetching score for assessment ${assessmentUid}:`, error);
    }
  };

  const handleSubmitJoinCode = async () => {
    if (!inviteCode.trim()) {
      Alert.alert('Error', 'Please enter an invite code');
      return;
    }

    if (!user?.uid) {
      Alert.alert('Error', 'User not authenticated');
      return;
    }

    try {
      setJoiningSubject(true);

      const studentName = user.role === 'student'
        ? `${user.firstName} ${user.lastName}`
        : user.fullName || 'Student';
      const studentEmail = user.email;

      const result = await joinSubjectWithCode(
        inviteCode.trim().toUpperCase(),
        user.uid,
        studentName,
        studentEmail
      );

      setJoiningSubject(false);

      if (result.success) {
        setJoinSubjectModalVisible(false);
        Alert.alert('Success', result.message);
        // Reload subjects
        await loadStudentData();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error: any) {
      setJoiningSubject(false);
      Alert.alert('Error', error.message);
    }
  };

  const getScoreColor = (percentage: number) => {
    if (percentage >= 90) return '#22c55e'; // Green
    if (percentage >= 75) return '#3b82f6'; // Blue
    if (percentage >= 60) return '#f59e0b'; // Orange
    return '#ef4444'; // Red
  };

  const getScoreGrade = (percentage: number) => {
    if (percentage >= 90) return 'A';
    if (percentage >= 85) return 'B+';
    if (percentage >= 80) return 'B';
    if (percentage >= 75) return 'C+';
    if (percentage >= 70) return 'C';
    if (percentage >= 65) return 'D+';
    if (percentage >= 60) return 'D';
    return 'F';
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3b82f6" />
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <ScrollView 
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Welcome back,</Text>
            <TouchableOpacity onPress={handleOpenProfile} activeOpacity={0.7}>
              <Text style={styles.userName}>
                {user?.role === 'student' ? `${user.firstName} ${user.lastName}` : user?.fullName}
              </Text>
            </TouchableOpacity>
            <Text style={styles.studentId}>
              Student ID: {user?.role === 'student' ? user.studentId : 'N/A'}
            </Text>
          </View>
          <TouchableOpacity 
            style={styles.signOutButton}
            onPress={handleSignOut}
          >
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>

        {/* Join Subject Button */}
        <View style={styles.joinButtonSection}>
          <TouchableOpacity
            style={styles.joinSubjectButton}
            onPress={handleJoinSubject}
          >
            <LinearGradient
              colors={['#3b82f6', '#2563eb']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.joinButtonText}>📚 Join Subject</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* My Subjects */}
        <View style={styles.subjectsSection}>
          <Text style={styles.sectionTitle}>My Subjects</Text>
          
          {enrolledSubjects.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>📚</Text>
              <Text style={styles.emptyStateText}>No subjects enrolled</Text>
              <Text style={styles.emptyStateSubtext}>Ask your teacher for a subject code to join</Text>
            </View>
          ) : (
            enrolledSubjects.map((subject) => (
              <TouchableOpacity 
                key={subject.id} 
                style={styles.subjectCard}
                activeOpacity={0.7}
                onPress={() => handleOpenSubjectScores(subject)}
              >
                <View style={styles.subjectCardHeader}>
                  <Text style={styles.subjectName}>{subject.subjectName}</Text>
                  <Text style={styles.subjectCode}>{subject.subjectCode}</Text>
                </View>
                <Text style={styles.subjectDetails}>
                  {subject.year}-{subject.sectionName} • {subject.teacherName}
                </Text>
                <Text style={styles.tapToView}>Tap to view scores →</Text>
              </TouchableOpacity>
            ))
          )}
        </View>

        {/* Recent Assessments */}
        <View style={styles.assessmentsSection}>
          <View style={styles.assessmentsSectionHeader}>
            <Text style={styles.sectionTitle}>Recent Assessments</Text>
            {loadingAssessments && (
              <ActivityIndicator size="small" color="#3b82f6" />
            )}
          </View>
          
          {recentAssessments.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>📝</Text>
              <Text style={styles.emptyStateText}>No assessments yet</Text>
              <Text style={styles.emptyStateSubtext}>Your scores will appear here</Text>
            </View>
          ) : (
            recentAssessments.map((assessment) => (
              <View key={`${assessment.assessmentUid}-${assessment.scannedAt}`} style={styles.assessmentCard}>
                <View style={styles.assessmentHeader}>
                  <View style={styles.assessmentInfo}>
                    <Text style={styles.assessmentName}>{assessment.assessmentName}</Text>
                    <Text style={styles.assessmentMeta}>
                      {formatDate(assessment.scannedAt)}
                    </Text>
                    {assessment.isPartialScore && (
                      <View style={styles.editedBadge}>
                        <Text style={styles.editedBadgeText}>✏️ Edited</Text>
                      </View>
                    )}
                  </View>

                  <View style={styles.scoreDisplay}>
                    <Text 
                      style={[
                        styles.scorePercentage,
                        { color: getScoreColor(assessment.percentage) }
                      ]}
                    >
                      {assessment.percentage}%
                    </Text>
                    <Text 
                      style={[
                        styles.scoreGrade,
                        { color: getScoreColor(assessment.percentage) }
                      ]}
                    >
                      {getScoreGrade(assessment.percentage)}
                    </Text>
                  </View>
                </View>

                <View style={styles.assessmentStats}>
                  <Text style={styles.assessmentStatsText}>
                    {assessment.score}/{assessment.perfectScore} correct
                  </Text>
                </View>

                {/* Progress Bar */}
                <View style={styles.progressBarContainer}>
                  <View 
                    style={[
                      styles.progressBar,
                      { 
                        width: `${assessment.percentage}%`,
                        backgroundColor: getScoreColor(assessment.percentage)
                      }
                    ]}
                  />
                </View>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      {/* Profile Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={profileModalVisible}
        onRequestClose={handleCloseProfile}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Profile Information</Text>
              <TouchableOpacity 
                style={styles.iconButton}
                onPress={handleCloseProfile}
              >
                <Text style={styles.iconButtonText}>✕ Close</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>First Name</Text>
                <Text style={styles.modalValue}>
                  {user?.role === 'student' ? user.firstName : '-'}
                </Text>
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Last Name</Text>
                <Text style={styles.modalValue}>
                  {user?.role === 'student' ? user.lastName : '-'}
                </Text>
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Email</Text>
                <Text style={[styles.modalValue, styles.readOnlyValue]}>
                  {user?.email}
                </Text>
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Username</Text>
                <Text style={styles.modalValue}>{user?.username}</Text>
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Student ID</Text>
                <Text style={styles.modalValue}>
                  {user?.role === 'student' ? user.studentId : 'N/A'}
                </Text>
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Role</Text>
                <Text style={[styles.modalValue, styles.readOnlyValue]}>
                  {user?.role}
                </Text>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Join Subject Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={joinSubjectModalVisible}
        onRequestClose={() => setJoinSubjectModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Join Subject</Text>
              <TouchableOpacity
                style={styles.iconButton}
                onPress={() => setJoinSubjectModalVisible(false)}
              >
                <Text style={styles.iconButtonText}>✕ Close</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.modalBody}>
              <Text style={styles.joinModalDescription}>
                Enter the invite code provided by your teacher to join their subject.
              </Text>

              <Text style={styles.inputLabel}>Invite Code</Text>
              <TextInput
                style={styles.codeInput}
                placeholder="Enter 6-digit code"
                placeholderTextColor="#94a3b8"
                value={inviteCode}
                onChangeText={(text) => setInviteCode(text.toUpperCase())}
                autoCapitalize="characters"
                maxLength={6}
                editable={!joiningSubject}
              />

              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleSubmitJoinCode}
                disabled={joiningSubject}
              >
                <LinearGradient
                  colors={['#22c55e', '#16a34a']}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.gradientButton}
                >
                  {joiningSubject ? (
                    <ActivityIndicator color="#ffffff" />
                  ) : (
                    <Text style={styles.submitButtonText}>Join Subject</Text>
                  )}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Subject Scores Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={subjectScoresModalVisible}
        onRequestClose={handleCloseSubjectScores}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, styles.scoresModalContent]}>
            <View style={styles.modalHeader}>
              <View style={styles.modalTitleContainer}>
                <Text style={styles.modalTitle}>
                  {selectedSubject?.subjectName || 'Subject Scores'}
                </Text>
                {selectedSubject && (
                  <Text style={styles.modalSubtitle}>
                    {selectedSubject.year}-{selectedSubject.sectionName} • {selectedSubject.teacherName}
                  </Text>
                )}
              </View>
              <TouchableOpacity
                style={styles.iconButton}
                onPress={handleCloseSubjectScores}
              >
                <Text style={styles.iconButtonText}>✕ Close</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              {loadingSubjectScores ? (
                <View style={styles.loadingContainer}>
                  <ActivityIndicator size="large" color="#3b82f6" />
                  <Text style={styles.loadingText}>Loading scores...</Text>
                </View>
              ) : subjectAssessments.length === 0 ? (
                <View style={styles.emptyState}>
                  <Text style={styles.emptyStateIcon}>📝</Text>
                  <Text style={styles.emptyStateText}>No assessments yet</Text>
                  <Text style={styles.emptyStateSubtext}>
                    Your scores for this subject will appear here
                  </Text>
                </View>
              ) : (
                <>
                  {/* Statistics */}
                  <View style={styles.statsRow}>
                    <View style={styles.statCard}>
                      <Text style={styles.statValue}>{subjectAssessments.length}</Text>
                      <Text style={styles.statLabel}>Assessments</Text>
                    </View>
                    <View style={styles.statCard}>
                      <Text style={styles.statValue}>
                        {(subjectAssessments.reduce((sum, a) => sum + a.percentage, 0) / subjectAssessments.length).toFixed(1)}%
                      </Text>
                      <Text style={styles.statLabel}>Average</Text>
                    </View>
                    <View style={styles.statCard}>
                      <Text style={styles.statValue}>
                        {Math.max(...subjectAssessments.map(a => a.percentage))}%
                      </Text>
                      <Text style={styles.statLabel}>Highest</Text>
                    </View>
                  </View>

                  {/* Assessment List */}
                  {subjectAssessments.map((assessment, index) => (
                    <View key={`${assessment.assessmentUid}-${index}`} style={styles.assessmentCard}>
                      <View style={styles.assessmentHeader}>
                        <View style={styles.assessmentInfo}>
                          <Text style={styles.assessmentName}>{assessment.assessmentName}</Text>
                          <Text style={styles.assessmentMeta}>
                            {formatDate(assessment.scannedAt)}
                          </Text>
                          {assessment.isPartialScore && (
                            <View style={styles.editedBadge}>
                              <Text style={styles.editedBadgeText}>✏️ Edited</Text>
                            </View>
                          )}
                        </View>

                        <View style={styles.scoreDisplay}>
                          <Text 
                            style={[
                              styles.scorePercentage,
                              { color: getScoreColor(assessment.percentage) }
                            ]}
                          >
                            {assessment.percentage}%
                          </Text>
                          <Text 
                            style={[
                              styles.scoreGrade,
                              { color: getScoreColor(assessment.percentage) }
                            ]}
                          >
                            {getScoreGrade(assessment.percentage)}
                          </Text>
                        </View>
                      </View>

                      <View style={styles.assessmentStats}>
                        <Text style={styles.assessmentStatsText}>
                          {assessment.score}/{assessment.perfectScore} correct
                        </Text>
                      </View>

                      {/* Progress Bar */}
                      <View style={styles.progressBarContainer}>
                        <View 
                          style={[
                            styles.progressBar,
                            { 
                              width: `${assessment.percentage}%`,
                              backgroundColor: getScoreColor(assessment.percentage)
                            }
                          ]}
                        />
                      </View>
                    </View>
                  ))}
                </>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  scrollView: {
    flex: 1
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center'
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#64748b'
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 20,
    backgroundColor: '#171443',
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060'
  },
  greeting: {
    fontSize: 16,
    color: '#cdd5df'
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginTop: 4,
    textDecorationLine: 'underline'
  },
  studentId: {
    fontSize: 14,
    color: '#cdd5df',
    marginTop: 2
  },
  signOutButton: {
    backgroundColor: '#fee2e2',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8
  },
  signOutText: {
    color: '#dc2626',
    fontWeight: '600',
    fontSize: 14
  },
  joinButtonSection: {
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 12
  },
  joinSubjectButton: {
    borderRadius: 12,
    overflow: 'hidden'
  },
  gradientButton: {
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center'
  },
  joinButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff'
  },
  subjectsSection: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 12
  },
  assessmentsSection: {
    paddingHorizontal: 24,
    paddingBottom: 24
  },
  assessmentsSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1e293b'
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
    backgroundColor: '#ffffff',
    borderRadius: 12
  },
  emptyStateIcon: {
    fontSize: 48,
    marginBottom: 16
  },
  emptyStateText: {
    fontSize: 18,
    color: '#64748b',
    fontWeight: '600',
    marginBottom: 8
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#94a3b8'
  },
  subjectCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2
  },
  subjectCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8
  },
  subjectName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
    flex: 1
  },
  subjectCode: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3b82f6',
    fontFamily: 'monospace',
    backgroundColor: '#dbeafe',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6
  },
  subjectDetails: {
    fontSize: 14,
    color: '#64748b'
  },
  tapToView: {
    fontSize: 12,
    color: '#3b82f6',
    marginTop: 8,
    fontWeight: '600'
  },
  assessmentCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2
  },
  assessmentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8
  },
  assessmentInfo: {
    flex: 1,
    marginRight: 12
  },
  assessmentName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4
  },
  assessmentMeta: {
    fontSize: 13,
    color: '#64748b'
  },
  editedBadge: {
    backgroundColor: '#fef3c7',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    alignSelf: 'flex-start',
    marginTop: 4
  },
  editedBadgeText: {
    fontSize: 11,
    color: '#92400e',
    fontWeight: '600'
  },
  scoreDisplay: {
    alignItems: 'flex-end'
  },
  scorePercentage: {
    fontSize: 24,
    fontWeight: 'bold'
  },
  scoreGrade: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: 2
  },
  assessmentStats: {
    marginBottom: 8
  },
  assessmentStatsText: {
    fontSize: 14,
    color: '#64748b'
  },
  progressBarContainer: {
    height: 6,
    backgroundColor: '#e2e8f0',
    borderRadius: 3,
    overflow: 'hidden'
  },
  progressBar: {
    height: '100%',
    borderRadius: 3
  },
  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderRadius: 20,
    width: '100%',
    maxWidth: 500,
    maxHeight: '80%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 10
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0'
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1e293b'
  },
  iconButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: '#f1f5f9'
  },
  iconButtonText: {
    fontSize: 14,
    color: '#475569',
    fontWeight: '600'
  },
  modalBody: {
    padding: 20
  },
  modalField: {
    marginBottom: 20
  },
  modalLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 8
  },
  modalValue: {
    fontSize: 16,
    color: '#1e293b',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#f8fafc',
    borderRadius: 8
  },
  readOnlyValue: {
    color: '#64748b',
    fontStyle: 'italic'
  },
  joinModalDescription: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 20,
    lineHeight: 20
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 8
  },
  codeInput: {
    backgroundColor: '#f8fafc',
    borderWidth: 2,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 18,
    color: '#1e293b',
    fontFamily: 'monospace',
    textAlign: 'center',
    letterSpacing: 4,
    fontWeight: 'bold',
    marginBottom: 20
  },
  submitButton: {
    borderRadius: 10,
    overflow: 'hidden'
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff'
  },
  scoresModalContent: {
    maxHeight: '90%'
  },
  modalTitleContainer: {
    flex: 1
  },
  modalSubtitle: {
    fontSize: 14,
    color: '#64748b',
    marginTop: 4
  },
  statsRow: {
    flexDirection: 'row',
    marginBottom: 20,
    gap: 10
  },
  statCard: {
    flex: 1,
    backgroundColor: '#f8fafc',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center'
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 4
  },
  statLabel: {
    fontSize: 12,
    color: '#64748b',
    fontWeight: '600'
  }
});

export default StudentDashboardScreen;