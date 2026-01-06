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

// NEW: Match Python structure exactly
interface StudentScore {
  studentId: string; // From object key
  score: number; // Raw score (e.g., 17)
  perfectScore: number; // Total questions (e.g., 20)
  isPartialScore: boolean; // Always false from Python
  assessmentUid: string;
  scannedAt: string; // Format: "MM/DD/YYYY HH:MM:SS"
}

const ViewScoresScreen: React.FC<Props> = ({ route, navigation }) => {
  const assessmentUid = route.params?.assessmentUid;
  const assessmentName = route.params?.assessmentName;
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scores, setScores] = useState<StudentScore[]>([]);

  useEffect(() => {
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

      // Parse student scores from Firebase
      // Structure: { [studentId]: { score, perfectScore, isPartialScore, assessmentUid, scannedAt } }
      const studentScores: StudentScore[] = [];
      
      Object.keys(data).forEach(key => {
        const studentData = data[key];
        
        // Validate that this is a student score object (has required fields from Python)
        if (studentData && 
            typeof studentData.score === 'number' && 
            typeof studentData.perfectScore === 'number' &&
            typeof studentData.scannedAt === 'string') {
          
          studentScores.push({
            studentId: key, // Use the key as studentId
            score: studentData.score,
            perfectScore: studentData.perfectScore,
            isPartialScore: studentData.isPartialScore ?? false,
            assessmentUid: studentData.assessmentUid || assessmentUid,
            scannedAt: studentData.scannedAt
          });
        }
      });

      // Sort by percentage score (highest first)
      studentScores.sort((a, b) => {
        const percentA = (a.score / a.perfectScore) * 100;
        const percentB = (b.score / b.perfectScore) * 100;
        return percentB - percentA;
      });

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

  // Calculate percentage from raw score
  const calculatePercentage = (score: number, perfectScore: number): number => {
    if (perfectScore === 0) return 0;
    return Math.round((score / perfectScore) * 100);
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

  // Parse scannedAt date (format: "MM/DD/YYYY HH:MM:SS")
  const formatDate = (scannedAt: string): string => {
    try {
      // Python format: "01/06/2026 14:30:45"
      const [datePart, timePart] = scannedAt.split(' ');
      const [month, day, year] = datePart.split('/');
      const [hour, minute, second] = timePart.split(':');
      
      const date = new Date(
        parseInt(year),
        parseInt(month) - 1,
        parseInt(day),
        parseInt(hour),
        parseInt(minute),
        parseInt(second)
      );
      
      return date.toLocaleString();
    } catch (e) {
      return scannedAt; // Fallback to raw string
    }
  };

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

  // Calculate statistics
  const averagePercentage = scores.length > 0
    ? scores.reduce((sum, s) => sum + calculatePercentage(s.score, s.perfectScore), 0) / scores.length
    : 0;

  const highestPercentage = scores.length > 0
    ? Math.max(...scores.map(s => calculatePercentage(s.score, s.perfectScore)))
    : 0;

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
                    {averagePercentage.toFixed(1)}%
                  </Text>
                  <Text style={styles.statLabel}>Average</Text>
                </View>
                <View style={styles.statBox}>
                  <Text style={styles.statNumber}>{highestPercentage}%</Text>
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
            scores.map((studentScore, index) => {
              const percentage = calculatePercentage(studentScore.score, studentScore.perfectScore);
              
              return (
                <View key={studentScore.studentId} style={styles.scoreCard}>
                  <View style={styles.scoreHeader}>
                    <View style={styles.rankBadge}>
                      <Text style={styles.rankText}>#{index + 1}</Text>
                    </View>
                    
                    <View style={styles.studentInfo}>
                      <Text style={styles.studentId}>{studentScore.studentId}</Text>
                      <Text style={styles.scoreStats}>
                        {studentScore.score}/{studentScore.perfectScore} correct
                      </Text>
                      {studentScore.isPartialScore && (
                        <Text style={styles.partialScoreLabel}>⚠️ Partial Score (Editable)</Text>
                      )}
                      <Text style={styles.timestamp}>
                        {formatDate(studentScore.scannedAt)}
                      </Text>
                    </View>

                    <View style={styles.scoreDisplay}>
                      <Text 
                        style={[
                          styles.scorePercentage,
                          { color: getScoreColor(percentage) }
                        ]}
                      >
                        {percentage}%
                      </Text>
                      <Text 
                        style={[
                          styles.scoreGrade,
                          { color: getScoreColor(percentage) }
                        ]}
                      >
                        {getScoreGrade(percentage)}
                      </Text>
                    </View>
                  </View>

                  {/* Progress Bar */}
                  <View style={styles.progressBarContainer}>
                    <View 
                      style={[
                        styles.progressBar,
                        { 
                          width: `${percentage}%`,
                          backgroundColor: getScoreColor(percentage)
                        }
                      ]}
                    />
                  </View>
                </View>
              );
            })
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
  partialScoreLabel: {
    fontSize: 11,
    color: '#f59e0b',
    fontWeight: '600',
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
});

export default ViewScoresScreen;