import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherAssessmentScoreTable'>;

interface StudentScore {
  studentId: string;
  familyName: string;
  firstName: string;
  score: number | null;
}

const AssessmentScoreTableScreen: React.FC<Props> = ({ route, navigation }) => {
  const { assessment, subject, section } = route.params;
  const { user } = useAuth();

  // State
  const [studentScores, setStudentScores] = useState<StudentScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedScores, setEditedScores] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    loadStudentScores();
  }, []);

  const loadStudentScores = async () => {
    try {
      setLoading(true);
      // TODO: Implement getAssessmentScores service function
      // Placeholder data for now
      const mockData: StudentScore[] = [
        { studentId: '1', familyName: 'Doe', firstName: 'John', score: 85 },
        { studentId: '2', familyName: 'Smith', firstName: 'Jane', score: 92 },
        { studentId: '3', familyName: 'Johnson', firstName: 'Mike', score: null },
      ];
      setStudentScores(mockData);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadStudentScores();
    setRefreshing(false);
  };

  const handleEditToggle = () => {
    if (isEditing) {
      // Save changes
      Alert.alert(
        'Save Changes',
        'Do you want to save your changes?',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Save',
            onPress: async () => {
              try {
                // TODO: Implement updateStudentScores service function
                Alert.alert('Success', 'Scores updated successfully!');
                setIsEditing(false);
                setEditedScores({});
                await loadStudentScores();
              } catch (error: any) {
                Alert.alert('Error', error.message);
              }
            }
          }
        ]
      );
    } else {
      setIsEditing(true);
    }
  };

  const handleScoreChange = (studentId: string, score: string) => {
    setEditedScores({
      ...editedScores,
      [studentId]: score
    });
  };

  const getDisplayScore = (student: StudentScore): string => {
    if (isEditing && editedScores[student.studentId] !== undefined) {
      return editedScores[student.studentId];
    }
    return student.score !== null ? student.score.toString() : '-';
  };

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
        {/* Assessment Info Header */}
        <View style={styles.assessmentInfoHeader}>
          <Text style={styles.assessmentInfoTitle}>{assessment.name}</Text>
          <Text style={styles.assessmentInfoSubtitle}>
            {assessment.type === 'quiz' ? '📝 Quiz' : '📄 Exam'}
          </Text>
          <Text style={styles.assessmentInfoSubtitle}>
            {subject.subjectName} • {section.year}-{section.sectionName}
          </Text>
        </View>

        {/* Edit Button */}
        <View style={styles.actionSection}>
          <TouchableOpacity
            style={styles.editButton}
            onPress={handleEditToggle}
          >
            <LinearGradient
              colors={isEditing ? ['#22c55e', '#16a34a'] : ['#6366f1', '#8b5cf6']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.editButtonText}>
                {isEditing ? '💾 Save Changes' : '✏️ Edit Scores'}
              </Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Scores Table */}
        <View style={styles.tableSection}>
          <Text style={styles.sectionTitle}>Student Scores</Text>
          
          {/* Table Header */}
          <View style={styles.tableHeader}>
            <Text style={[styles.tableHeaderText, styles.columnNo]}>No.</Text>
            <Text style={[styles.tableHeaderText, styles.columnFamilyName]}>Family Name</Text>
            <Text style={[styles.tableHeaderText, styles.columnFirstName]}>First Name</Text>
            <Text style={[styles.tableHeaderText, styles.columnScore]}>Score</Text>
          </View>

          {/* Table Rows */}
          {studentScores.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>📊</Text>
              <Text style={styles.emptyStateText}>No students enrolled</Text>
            </View>
          ) : (
            studentScores.map((student, index) => (
              <View key={student.studentId} style={styles.tableRow}>
                <Text style={[styles.tableRowText, styles.columnNo]}>{index + 1}</Text>
                <Text style={[styles.tableRowText, styles.columnFamilyName]}>
                  {student.familyName}
                </Text>
                <Text style={[styles.tableRowText, styles.columnFirstName]}>
                  {student.firstName}
                </Text>
                {isEditing ? (
                  <TextInput
                    style={[styles.scoreInput, styles.columnScore]}
                    value={getDisplayScore(student)}
                    onChangeText={(text) => handleScoreChange(student.studentId, text)}
                    keyboardType="numeric"
                    placeholder="-"
                    placeholderTextColor="#94a3b8"
                  />
                ) : (
                  <Text style={[styles.tableRowText, styles.columnScore, student.score === null && styles.emptyScore]}>
                    {getDisplayScore(student)}
                  </Text>
                )}
              </View>
            ))
          )}
        </View>

        {/* Statistics Section */}
        {studentScores.length > 0 && (
          <View style={styles.statsSection}>
            <Text style={styles.sectionTitle}>Statistics</Text>
            <View style={styles.statsGrid}>
              <View style={styles.statCard}>
                <Text style={styles.statLabel}>Total Students</Text>
                <Text style={styles.statValue}>{studentScores.length}</Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statLabel}>Completed</Text>
                <Text style={styles.statValue}>
                  {studentScores.filter(s => s.score !== null).length}
                </Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statLabel}>Average Score</Text>
                <Text style={styles.statValue}>
                  {studentScores.filter(s => s.score !== null).length > 0
                    ? Math.round(
                        studentScores
                          .filter(s => s.score !== null)
                          .reduce((sum, s) => sum + (s.score || 0), 0) /
                          studentScores.filter(s => s.score !== null).length
                      )
                    : '-'}
                </Text>
              </View>
            </View>
          </View>
        )}
      </ScrollView>
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
  assessmentInfoHeader: {
    backgroundColor: '#171443',
    paddingHorizontal: 24,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060'
  },
  assessmentInfoTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4
  },
  assessmentInfoSubtitle: {
    fontSize: 14,
    color: '#cdd5df',
    marginBottom: 4
  },
  actionSection: {
    paddingHorizontal: 24,
    paddingVertical: 20
  },
  editButton: {
    borderRadius: 12,
    overflow: 'hidden'
  },
  gradientButton: {
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center'
  },
  editButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff'
  },
  tableSection: {
    paddingHorizontal: 24,
    paddingBottom: 24
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 16
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#1e293b',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8
  },
  tableHeaderText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff'
  },
  tableRow: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0'
  },
  tableRowText: {
    fontSize: 14,
    color: '#1e293b'
  },
  columnNo: {
    width: 50,
    textAlign: 'center'
  },
  columnFamilyName: {
    flex: 2,
    paddingHorizontal: 8
  },
  columnFirstName: {
    flex: 2,
    paddingHorizontal: 8
  },
  columnScore: {
    flex: 1,
    textAlign: 'center'
  },
  scoreInput: {
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#22c55e',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    fontSize: 14,
    color: '#1e293b',
    textAlign: 'center'
  },
  emptyScore: {
    color: '#94a3b8'
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
    backgroundColor: '#ffffff',
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8
  },
  emptyStateIcon: {
    fontSize: 48,
    marginBottom: 16
  },
  emptyStateText: {
    fontSize: 18,
    color: '#64748b',
    fontWeight: '600'
  },
  statsSection: {
    paddingHorizontal: 24,
    paddingBottom: 24
  },
  statsGrid: {
    flexDirection: 'row',
    gap: 12
  },
  statCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2
  },
  statLabel: {
    fontSize: 12,
    color: '#64748b',
    marginBottom: 8,
    textAlign: 'center'
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b'
  }
});

export default AssessmentScoreTableScreen;