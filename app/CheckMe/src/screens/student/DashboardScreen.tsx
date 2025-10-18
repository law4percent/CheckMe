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
}

interface Assessment {
  id: string;
  name: string;
  type: 'quiz' | 'exam';
  score: number | null;
  maxScore: number;
  date: number;
}

const StudentDashboardScreen: React.FC<Props> = ({ navigation }) => {
  const { user, signOut } = useAuth();
  
  // State
  const [enrolledSubjects, setEnrolledSubjects] = useState<EnrolledSubject[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [profileModalVisible, setProfileModalVisible] = useState(false);
  const [joinSubjectModalVisible, setJoinSubjectModalVisible] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [joiningSubject, setJoiningSubject] = useState(false);

  useEffect(() => {
    if (user?.uid) {
      loadEnrolledSubjects();
    }
  }, [user?.uid]);

  const loadEnrolledSubjects = async () => {
    if (!user?.uid) return;
    
    try {
      setLoading(true);
      const enrollments = await getStudentEnrollments(user.uid);
      
      // Map enrollments to EnrolledSubject format
      const subjects: EnrolledSubject[] = enrollments.map(e => ({
        id: e.subjectId,
        subjectName: e.subjectName,
        subjectCode: e.subjectCode,
        teacherName: e.teacherName,
        sectionName: e.sectionName,
        year: e.year
      }));
      
      setEnrolledSubjects(subjects);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadEnrolledSubjects();
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
        await loadEnrolledSubjects();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error: any) {
      setJoiningSubject(false);
      Alert.alert('Error', error.message);
    }
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
              >
                <View style={styles.subjectCardHeader}>
                  <Text style={styles.subjectName}>{subject.subjectName}</Text>
                  <Text style={styles.subjectCode}>{subject.subjectCode}</Text>
                </View>
                <Text style={styles.subjectDetails}>
                  {subject.year}-{subject.sectionName} • {subject.teacherName}
                </Text>
              </TouchableOpacity>
            ))
          )}
        </View>

        {/* Recent Assessments */}
        <View style={styles.assessmentsSection}>
          <Text style={styles.sectionTitle}>Recent Assessments</Text>
          
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateIcon}>📝</Text>
            <Text style={styles.emptyStateText}>No assessments yet</Text>
            <Text style={styles.emptyStateSubtext}>Your scores will appear here</Text>
          </View>
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
  sectionTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 16
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
  }
});

export default StudentDashboardScreen;