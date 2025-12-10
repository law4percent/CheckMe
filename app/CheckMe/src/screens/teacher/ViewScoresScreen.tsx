// src/screens/teacher/ViewScoresScreen.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import { useAuth } from '../../contexts/AuthContext';

type Props = NativeStackScreenProps<RootStackParamList, 'ViewScores'>;

interface StudentScore {
  studentId: string;
  score: number;
  totalQuestions: number;
  correctAnswers: number;
  incorrectAnswers: number;
  timestamp: string;
  details?: Array<{
    question: number;
    studentAnswer: string;
    correctAnswer: string;
    isCorrect: boolean;
  }>;
  collageImagePath?: string;
}

const ViewScoresScreen: React.FC<Props> = ({ route, navigation }) => {
  // CRITICAL FIX: Add safety checks for route.params
  const assessmentUid = route.params?.assessmentUid;
  const assessmentName = route.params?.assessmentName;
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scores, setScores] = useState<StudentScore[]>([]);
  const [expandedStudent, setExpandedStudent] = useState<string | null>(null);

  useEffect(() => {
    // CRITICAL FIX: Check if required params exist
    if (!assessmentUid) {
      console.error('❌ [ViewScores] No assessmentUid in route params');
      Alert.alert(
        'Error',
        'Assessment ID is missing. Please go back and try again.',
        [
          {
            text: 'Go Back',
            onPress: () => navigation.goBack()
          }
        ]
      );
      return;
    }

    loadScores();
  }, [assessmentUid]);

  const loadScores = async () => {
    if (!user?.uid) {
      console.error('❌ [ViewScores] No user UID');
      return;
    }

    if (!assessmentUid) {
      console.error('❌ [ViewScores] No assessmentUid');
      return;
    }

    try {
      setLoading(true);
      console.log('📊 [ViewScores] Loading scores...');
      console.log('  - teacherId:', user.uid);
      console.log('  - assessmentUid:', assessmentUid);

      const url = `https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/assessmentScoresAndImages/${user.uid}/${assessmentUid}.json`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch scores');
      }

      const data = await response.json();
      
      if (!data) {
        console.log('📊 [ViewScores] No data found');
        setScores([]);
        return;
      }

      // Filter out assessment metadata, keep only student scores
      const studentScores: StudentScore[] = [];
      
      Object.keys(data).forEach(key => {
        // Skip assessment metadata fields
        if (['assessmentUid', 'assessmentName', 'assessmentType', 'subjectId', 
             'subjectName', 'sectionId', 'sectionName', 'year', 'teacherId', 
             'createdAt', 'status', 'studentId'].includes(key)) {
          return;
        }

        // This is a student score
        const studentData = data[key];
        if (studentData && studentData.studentId) {
          studentScores.push(studentData);
        }
      });

      // Sort by score (highest first)
      studentScores.sort((a, b) => b.score - a.score);

      console.log('✅ [ViewScores] Loaded scores:', studentScores.length);
      setScores(studentScores);

    } catch (error: any) {
      console.error('❌ [ViewScores] Error loading scores:', error);
      Alert.alert('Error', error.message || 'Failed to load scores');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadScores();
    setRefreshing(false);
  };

  const toggleStudentDetails = (studentId: string) => {
    setExpandedStudent(expandedStudent === studentId ? null : studentId);
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return '#22c55e'; // Green
    if (score >= 75) return '#3b82f6'; // Blue
    if (score >= 60) return '#f59e0b'; // Orange
    return '#ef4444'; // Red
  };

  const getScoreGrade = (score: number) => {
    if (score >= 90) return 'A';
    if (score >= 85) return 'B+';
    if (score >= 80) return 'B';
    if (score >= 75) return 'C+';
    if (score >= 70) return 'C';
    if (score >= 65) return 'D+';
    if (score >= 60) return 'D';
    return 'F';
  };

  // CRITICAL FIX: Early return if no assessmentUid
  if (!assessmentUid) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <View style={styles.loadingContainer}>
          <Text style={styles.errorText}>❌ Assessment ID missing</Text>
          <TouchableOpacity 
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.backButtonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#22c55e" />
          <Text style={styles.loadingText}>Loading scores...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>📊 Assessment Results</Text>
          {assessmentName && (
            <Text style={styles.assessmentName}>{assessmentName}</Text>
          )}
          <Text style={styles.headerSubtitle}>UID: {assessmentUid}</Text>
          <View style={styles.statsContainer}>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>{scores.length}</Text>
              <Text style={styles.statLabel}>Submissions</Text>
            </View>
            {scores.length > 0 && (
              <>
                <View style={styles.statBox}>
                  <Text style={styles.statNumber}>
                    {(scores.reduce((sum, s) => sum + s.score, 0) / scores.length).toFixed(1)}%
                  </Text>
                  <Text style={styles.statLabel}>Average</Text>
                </View>
                <View style={styles.statBox}>
                  <Text style={styles.statNumber}>{Math.max(...scores.map(s => s.score))}%</Text>
                  <Text style={styles.statLabel}>Highest</Text>
                </View>
              </>
            )}
          </View>
        </View>

        {/* Scores List */}
        <View style={styles.scoresSection}>
          {scores.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>📝</Text>
              <Text style={styles.emptyStateText}>No submissions yet</Text>
              <Text style={styles.emptyStateSubtext}>
                Scores will appear here once students submit their answer sheets
              </Text>
            </View>
          ) : (
            scores.map((studentScore, index) => (
              <View key={studentScore.studentId} style={styles.scoreCard}>
                <TouchableOpacity
                  onPress={() => toggleStudentDetails(studentScore.studentId)}
                  activeOpacity={0.7}
                >
                  <View style={styles.scoreHeader}>
                    <View style={styles.rankBadge}>
                      <Text style={styles.rankText}>#{index + 1}</Text>
                    </View>
                    
                    <View style={styles.studentInfo}>
                      <Text style={styles.studentId}>{studentScore.studentId}</Text>
                      <Text style={styles.scoreStats}>
                        {studentScore.correctAnswers}/{studentScore.totalQuestions} correct
                      </Text>
                      <Text style={styles.timestamp}>
                        {new Date(studentScore.timestamp).toLocaleString()}
                      </Text>
                    </View>

                    <View style={styles.scoreDisplay}>
                      <Text 
                        style={[
                          styles.scorePercentage,
                          { color: getScoreColor(studentScore.score) }
                        ]}
                      >
                        {studentScore.score}%
                      </Text>
                      <Text 
                        style={[
                          styles.scoreGrade,
                          { color: getScoreColor(studentScore.score) }
                        ]}
                      >
                        {getScoreGrade(studentScore.score)}
                      </Text>
                    </View>
                  </View>

                  {/* Progress Bar */}
                  <View style={styles.progressBarContainer}>
                    <View 
                      style={[
                        styles.progressBar,
                        { 
                          width: `${studentScore.score}%`,
                          backgroundColor: getScoreColor(studentScore.score)
                        }
                      ]}
                    />
                  </View>
                </TouchableOpacity>

                {/* Expanded Details */}
                {expandedStudent === studentScore.studentId && studentScore.details && (
                  <View style={styles.detailsSection}>
                    <Text style={styles.detailsTitle}>Question-by-Question Breakdown:</Text>
                    <ScrollView 
                      horizontal 
                      showsHorizontalScrollIndicator={false}
                      style={styles.detailsScroll}
                    >
                      {studentScore.details.map((detail, idx) => (
                        <View 
                          key={idx} 
                          style={[
                            styles.questionBox,
                            detail.isCorrect ? styles.questionCorrect : styles.questionIncorrect
                          ]}
                        >
                          <Text style={styles.questionNumber}>Q{detail.question}</Text>
                          <View style={styles.answerRow}>
                            <Text style={styles.answerLabel}>Student:</Text>
                            <Text style={styles.answerValue}>{detail.studentAnswer}</Text>
                          </View>
                          <View style={styles.answerRow}>
                            <Text style={styles.answerLabel}>Correct:</Text>
                            <Text style={styles.answerValue}>{detail.correctAnswer}</Text>
                          </View>
                          <Text style={styles.resultIcon}>
                            {detail.isCorrect ? '✓' : '✗'}
                          </Text>
                        </View>
                      ))}
                    </ScrollView>

                    {studentScore.collageImagePath && (
                      <View style={styles.imagePathContainer}>
                        <Text style={styles.imagePathLabel}>📷 Image:</Text>
                        <Text style={styles.imagePathText} numberOfLines={1}>
                          {studentScore.collageImagePath}
                        </Text>
                      </View>
                    )}
                  </View>
                )}
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#64748b',
  },
  errorText: {
    fontSize: 18,
    color: '#ef4444',
    fontWeight: '600',
    marginBottom: 16,
  },
  backButton: {
    backgroundColor: '#6366f1',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    backgroundColor: '#171443',
    paddingHorizontal: 24,
    paddingVertical: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  assessmentName: {
    fontSize: 18,
    color: '#22c55e',
    fontWeight: '600',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#cdd5df',
    fontFamily: 'monospace',
    marginBottom: 16,
  },
  statsContainer: {
    flexDirection: 'row',
    gap: 12,
  },
  statBox: {
    flex: 1,
    backgroundColor: '#2a2060',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#22c55e',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#cdd5df',
  },
  scoresSection: {
    padding: 16,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyStateIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyStateText: {
    fontSize: 18,
    color: '#64748b',
    fontWeight: '600',
    marginBottom: 8,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#94a3b8',
    textAlign: 'center',
    paddingHorizontal: 40,
  },
  scoreCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  scoreHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  rankBadge: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#f1f5f9',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rankText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#475569',
  },
  studentInfo: {
    flex: 1,
  },
  studentId: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 2,
  },
  scoreStats: {
    fontSize: 13,
    color: '#64748b',
    marginBottom: 2,
  },
  timestamp: {
    fontSize: 11,
    color: '#94a3b8',
  },
  scoreDisplay: {
    alignItems: 'flex-end',
  },
  scorePercentage: {
    fontSize: 32,
    fontWeight: 'bold',
  },
  scoreGrade: {
    fontSize: 16,
    fontWeight: '600',
  },
  progressBarContainer: {
    height: 8,
    backgroundColor: '#f1f5f9',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    borderRadius: 4,
  },
  detailsSection: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  detailsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 12,
  },
  detailsScroll: {
    marginBottom: 12,
  },
  questionBox: {
    width: 120,
    padding: 12,
    borderRadius: 8,
    marginRight: 8,
    borderWidth: 2,
  },
  questionCorrect: {
    backgroundColor: '#f0fdf4',
    borderColor: '#22c55e',
  },
  questionIncorrect: {
    backgroundColor: '#fef2f2',
    borderColor: '#ef4444',
  },
  questionNumber: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#64748b',
    marginBottom: 8,
  },
  answerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  answerLabel: {
    fontSize: 11,
    color: '#94a3b8',
  },
  answerValue: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1e293b',
  },
  resultIcon: {
    fontSize: 20,
    textAlign: 'center',
    marginTop: 4,
  },
  imagePathContainer: {
    backgroundColor: '#f8fafc',
    padding: 12,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  imagePathLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#475569',
    marginRight: 8,
  },
  imagePathText: {
    flex: 1,
    fontSize: 11,
    color: '#64748b',
    fontFamily: 'monospace',
  },
});

export default ViewScoresScreen;