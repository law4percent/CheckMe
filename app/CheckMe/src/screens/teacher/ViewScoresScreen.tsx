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
  TextInput,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import { useAuth } from '../../contexts/AuthContext';

type Props = NativeStackScreenProps<RootStackParamList, 'ViewScores'>;

// Match Python structure exactly
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
  
  // Edit modal state
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingStudent, setEditingStudent] = useState<StudentScore | null>(null);
  const [editScore, setEditScore] = useState('');
  const [editPerfectScore, setEditPerfectScore] = useState('');
  const [saving, setSaving] = useState(false);

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
      const studentScores: StudentScore[] = [];
      
      Object.keys(data).forEach(key => {
        const studentData = data[key];
        
        // Validate that this is a student score object
        if (studentData && 
            typeof studentData.score === 'number' && 
            typeof studentData.perfectScore === 'number' &&
            typeof studentData.scannedAt === 'string') {
          
          studentScores.push({
            studentId: key,
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

  // Open edit modal
  const openEditModal = (studentScore: StudentScore) => {
    setEditingStudent(studentScore);
    setEditScore(studentScore.score.toString());
    setEditPerfectScore(studentScore.perfectScore.toString());
    setEditModalVisible(true);
  };

  // Close edit modal
  const closeEditModal = () => {
    setEditModalVisible(false);
    setEditingStudent(null);
    setEditScore('');
    setEditPerfectScore('');
  };

  // Save edited score
  const saveEditedScore = async () => {
    if (!editingStudent || !user?.uid || !assessmentUid) {
      return;
    }

    const newScore = parseInt(editScore);
    const newPerfectScore = parseInt(editPerfectScore);

    // Validation
    if (isNaN(newScore) || isNaN(newPerfectScore)) {
      Alert.alert('Invalid Input', 'Please enter valid numbers');
      return;
    }

    if (newScore < 0 || newPerfectScore < 0) {
      Alert.alert('Invalid Input', 'Scores cannot be negative');
      return;
    }

    if (newScore > newPerfectScore) {
      Alert.alert('Invalid Input', 'Score cannot be greater than perfect score');
      return;
    }

    try {
      setSaving(true);
      console.log('💾 [ViewScores] Saving edited score...');
      console.log('  - Student:', editingStudent.studentId);
      console.log('  - New score:', newScore);
      console.log('  - New perfect score:', newPerfectScore);

      const url = `https://checkme-68003-default-rtdb.asia-southeast1.firebasedatabase.app/assessmentScoresAndImages/${user.uid}/${assessmentUid}/${editingStudent.studentId}.json`;
      
      // Update only score and perfectScore, keep other fields
      const updatedData = {
        score: newScore,
        perfectScore: newPerfectScore,
        isPartialScore: true, // Mark as edited
        assessmentUid: editingStudent.assessmentUid,
        scannedAt: editingStudent.scannedAt
      };

      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedData)
      });

      if (!response.ok) {
        throw new Error('Failed to update score');
      }

      console.log('✅ [ViewScores] Score updated successfully');
      
      // Update local state
      setScores(prevScores => 
        prevScores.map(s => 
          s.studentId === editingStudent.studentId
            ? { ...s, score: newScore, perfectScore: newPerfectScore, isPartialScore: true }
            : s
        ).sort((a, b) => {
          const percentA = (a.score / a.perfectScore) * 100;
          const percentB = (b.score / b.perfectScore) * 100;
          return percentB - percentA;
        })
      );

      closeEditModal();
      Alert.alert('Success', 'Score updated successfully');

    } catch (error: any) {
      console.error('❌ [ViewScores] Error saving score:', error);
      Alert.alert('Error', error.message || 'Failed to update score');
    } finally {
      setSaving(false);
    }
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
      return scannedAt;
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
                        <View style={styles.partialScoreBadge}>
                          <Text style={styles.partialScoreLabel}>✏️ Manually Edited</Text>
                        </View>
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

                  {/* Edit Button - Always visible for all scores */}
                  <TouchableOpacity
                    style={styles.editButton}
                    onPress={() => openEditModal(studentScore)}
                  >
                    <Text style={styles.editButtonText}>✏️ Edit Score</Text>
                  </TouchableOpacity>
                </View>
              );
            })
          )}
        </View>
      </ScrollView>

      {/* Edit Modal */}
      <Modal
        visible={editModalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={closeEditModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Score</Text>
            
            {editingStudent && (
              <View style={styles.modalStudentInfo}>
                <Text style={styles.modalStudentId}>Student: {editingStudent.studentId}</Text>
                <Text style={styles.modalOriginalScore}>
                  Original: {editingStudent.score}/{editingStudent.perfectScore}
                </Text>
              </View>
            )}

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Score</Text>
              <TextInput
                style={styles.input}
                value={editScore}
                onChangeText={setEditScore}
                keyboardType="numeric"
                placeholder="Enter score"
                editable={!saving}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Perfect Score (Total Questions)</Text>
              <TextInput
                style={styles.input}
                value={editPerfectScore}
                onChangeText={setEditPerfectScore}
                keyboardType="numeric"
                placeholder="Enter perfect score"
                editable={!saving}
              />
            </View>

            {editScore && editPerfectScore && (
              <View style={styles.previewContainer}>
                <Text style={styles.previewLabel}>Preview:</Text>
                <Text style={styles.previewText}>
                  {calculatePercentage(parseInt(editScore) || 0, parseInt(editPerfectScore) || 1)}%
                </Text>
              </View>
            )}

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.cancelButton]}
                onPress={closeEditModal}
                disabled={saving}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalButton, styles.saveButton]}
                onPress={saveEditedScore}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator size="small" color="#ffffff" />
                ) : (
                  <Text style={styles.saveButtonText}>Save</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  partialScoreBadge: {
    backgroundColor: '#fef3c7',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    alignSelf: 'flex-start',
    marginBottom: 2,
  },
  partialScoreLabel: {
    fontSize: 11,
    color: '#d97706',
    fontWeight: '600',
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
  editButton: {
    marginTop: 12,
    backgroundColor: '#6366f1',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  editButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 16,
    textAlign: 'center',
  },
  modalStudentInfo: {
    backgroundColor: '#f8fafc',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  modalStudentId: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  modalOriginalScore: {
    fontSize: 14,
    color: '#64748b',
  },
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: '#1e293b',
    backgroundColor: '#ffffff',
  },
  previewContainer: {
    backgroundColor: '#f0fdf4',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  previewLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#166534',
    marginRight: 8,
  },
  previewText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#22c55e',
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: '#f1f5f9',
  },
  cancelButtonText: {
    color: '#475569',
    fontSize: 16,
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: '#22c55e',
  },
  saveButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default ViewScoresScreen;