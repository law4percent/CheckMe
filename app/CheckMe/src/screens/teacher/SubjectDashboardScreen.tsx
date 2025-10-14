import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
  RefreshControl,
  Clipboard,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';
import { 
  getSubjectEnrollments, 
  approveEnrollment, 
  rejectEnrollment,
  Enrollment 
} from '../../services/enrollmentService';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherSubjectDashboard'>;

const SubjectDashboardScreen: React.FC<Props> = ({ route, navigation }) => {
  const { subject, section } = route.params;
  const { user } = useAuth();

  // State
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Modal states
  const [createAssessmentModalVisible, setCreateAssessmentModalVisible] = useState(false);
  const [selectedAssessmentType, setSelectedAssessmentType] = useState<'quiz' | 'exam' | null>(null);

  useEffect(() => {
    console.log('🔄 [SubjectDashboard] useEffect triggered');
    console.log('  - subject:', subject);
    console.log('  - subject.id:', subject.id);
    console.log('  - user:', user);
    console.log('  - user?.uid:', user?.uid);
    
    if (subject.id) {
      loadEnrollments();
    }
  }, [subject.id]);

  const loadEnrollments = async () => {
    console.log('🔍 [SubjectDashboard] loadEnrollments called');
    console.log('  - user?.uid:', user?.uid);
    console.log('  - subject.id:', subject.id);
    console.log('  - subject:', subject);
    
    if (!user?.uid) {
      console.warn('⚠️ [SubjectDashboard] No user UID, returning early');
      return;
    }
    
    try {
      setLoading(true);
      console.log('📡 [SubjectDashboard] Calling getSubjectEnrollments with:', {
        teacherId: user.uid,
        subjectId: subject.id
      });
      
      const fetchedEnrollments = await getSubjectEnrollments(user.uid, subject.id);
      
      console.log('✅ [SubjectDashboard] Enrollments fetched successfully:', fetchedEnrollments.length);
      setEnrollments(fetchedEnrollments);
    } catch (error: any) {
      console.error('❌ [SubjectDashboard] Error loading enrollments:', error);
      console.error('  - Error code:', error.code);
      console.error('  - Error message:', error.message);
      console.error('  - Full error:', error);
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadEnrollments();
    setRefreshing(false);
  };

  const handleCopySubjectCode = () => {
    if (subject.subjectCode) {
      Clipboard.setString(subject.subjectCode);
      Alert.alert('Copied!', 'Subject code copied to clipboard');
    }
  };

  const handleCreateAssessment = () => {
    setSelectedAssessmentType(null);
    setCreateAssessmentModalVisible(true);
  };

  const handleConfirmCreateAssessment = () => {
    if (!selectedAssessmentType) {
      Alert.alert('Error', 'Please select assessment type');
      return;
    }

    Alert.alert('Coming Soon', `${selectedAssessmentType === 'quiz' ? 'Quiz' : 'Exam'} creation will be available soon!`);
    setCreateAssessmentModalVisible(false);
  };

  const handleApproveEnrollment = async (enrollment: Enrollment) => {
    console.log('✅ [SubjectDashboard] handleApproveEnrollment called');
    console.log('  - enrollment:', enrollment);
    console.log('  - user?.uid:', user?.uid);
    
    if (!user?.uid) {
      console.warn('⚠️ [SubjectDashboard] No user UID, returning early');
      return;
    }
    
    try {
      setActionLoading(true);
      console.log('📡 [SubjectDashboard] Calling approveEnrollment with:', {
        teacherId: user.uid,
        subjectId: subject.id,
        studentId: enrollment.studentId
      });
      
      await approveEnrollment(user.uid, subject.id, enrollment.studentId);
      
      // Update local state
      setEnrollments(enrollments.map(e =>
        e.studentId === enrollment.studentId
          ? { ...e, status: 'approved', approvedAt: Date.now() }
          : e
      ));

      console.log('✅ [SubjectDashboard] Enrollment approved successfully');
      Alert.alert('Success', `${enrollment.studentName} has been approved!`);
    } catch (error: any) {
      console.error('❌ [SubjectDashboard] Error approving enrollment:', error);
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectEnrollment = async (enrollment: Enrollment) => {
    console.log('❌ [SubjectDashboard] handleRejectEnrollment called');
    console.log('  - enrollment:', enrollment);
    console.log('  - user?.uid:', user?.uid);
    
    if (!user?.uid) {
      console.warn('⚠️ [SubjectDashboard] No user UID, returning early');
      return;
    }
    
    Alert.alert(
      'Reject Enrollment',
      `Are you sure you want to reject ${enrollment.studentName}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reject',
          style: 'destructive',
          onPress: async () => {
            try {
              setActionLoading(true);
              console.log('📡 [SubjectDashboard] Calling rejectEnrollment with:', {
                teacherId: user.uid,
                subjectId: subject.id,
                studentId: enrollment.studentId
              });
              
              await rejectEnrollment(user.uid, subject.id, enrollment.studentId);
              
              // Update local state
              setEnrollments(enrollments.map(e =>
                e.studentId === enrollment.studentId
                  ? { ...e, status: 'rejected', rejectedAt: Date.now() }
                  : e
              ));

              console.log('✅ [SubjectDashboard] Enrollment rejected successfully');
              Alert.alert('Success', 'Enrollment rejected');
            } catch (error: any) {
              console.error('❌ [SubjectDashboard] Error rejecting enrollment:', error);
              Alert.alert('Error', error.message);
            } finally {
              setActionLoading(false);
            }
          }
        }
      ]
    );
  };

  const pendingEnrollments = enrollments.filter(e => e.status === 'pending');
  const approvedEnrollments = enrollments.filter(e => e.status === 'approved');

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#22c55e" />
          <Text style={styles.loadingText}>Loading...</Text>
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
        {/* Subject Info Header */}
        <View style={styles.subjectInfoHeader}>
          <Text style={styles.subjectInfoTitle}>{subject.subjectName}</Text>
          <Text style={styles.subjectInfoSubtitle}>
            {section.year}-{section.sectionName}
          </Text>
          {subject.subjectCode && (
            <TouchableOpacity 
              style={styles.subjectCodeContainer}
              onPress={handleCopySubjectCode}
            >
              <Text style={styles.subjectCodeLabel}>Subject Code:</Text>
              <Text style={styles.subjectCode}>{subject.subjectCode}</Text>
              <Text style={styles.copyIcon}>📋</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Action Buttons */}
        <View style={styles.actionSection}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={handleCreateAssessment}
            disabled={actionLoading}
          >
            <LinearGradient
              colors={['#6366f1', '#8b5cf6']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.actionButtonText}>📝 Create Assessment</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => Alert.alert('Coming Soon', 'Student invitation feature will be available soon!')}
            disabled={actionLoading}
          >
            <LinearGradient
              colors={['#22c55e', '#16a34a']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.actionButtonText}>👥 Invite Students</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Pending Enrollments */}
        {pendingEnrollments.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Pending Enrollments ({pendingEnrollments.length})</Text>
            {pendingEnrollments.map((enrollment) => (
              <View key={enrollment.studentId} style={styles.enrollmentCard}>
                <View style={styles.enrollmentInfo}>
                  <Text style={styles.studentName}>{enrollment.studentName}</Text>
                  <Text style={styles.studentEmail}>{enrollment.studentEmail}</Text>
                  <Text style={styles.enrollmentDate}>
                    Requested: {new Date(enrollment.joinedAt).toLocaleDateString()}
                  </Text>
                </View>
                <View style={styles.enrollmentActions}>
                  <TouchableOpacity
                    style={styles.approveButton}
                    onPress={() => handleApproveEnrollment(enrollment)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.approveButtonText}>✓ Approve</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.rejectButton}
                    onPress={() => handleRejectEnrollment(enrollment)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.rejectButtonText}>✕ Reject</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Enrolled Students */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Enrolled Students ({approvedEnrollments.length})</Text>
          {approvedEnrollments.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>👥</Text>
              <Text style={styles.emptyStateText}>No enrolled students yet</Text>
              <Text style={styles.emptyStateSubtext}>Invite students to get started</Text>
            </View>
          ) : (
            approvedEnrollments.map((enrollment) => (
              <View key={enrollment.studentId} style={styles.studentCard}>
                <Text style={styles.studentName}>{enrollment.studentName}</Text>
                <Text style={styles.studentEmail}>{enrollment.studentEmail}</Text>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      {/* Loading Overlay */}
      {actionLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#22c55e" />
        </View>
      )}

      {/* Create Assessment Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={createAssessmentModalVisible}
        onRequestClose={() => setCreateAssessmentModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Create Assessment</Text>
            </View>

            <View style={styles.modalBody}>
              <Text style={styles.modalLabel}>Select Assessment Type:</Text>
              
              <TouchableOpacity
                style={[
                  styles.assessmentTypeButton,
                  selectedAssessmentType === 'quiz' && styles.assessmentTypeButtonSelected
                ]}
                onPress={() => setSelectedAssessmentType('quiz')}
              >
                <Text style={styles.assessmentTypeIcon}>📝</Text>
                <Text style={[
                  styles.assessmentTypeText,
                  selectedAssessmentType === 'quiz' && styles.assessmentTypeTextSelected
                ]}>
                  Quiz
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.assessmentTypeButton,
                  selectedAssessmentType === 'exam' && styles.assessmentTypeButtonSelected
                ]}
                onPress={() => setSelectedAssessmentType('exam')}
              >
                <Text style={styles.assessmentTypeIcon}>📄</Text>
                <Text style={[
                  styles.assessmentTypeText,
                  selectedAssessmentType === 'exam' && styles.assessmentTypeTextSelected
                ]}>
                  Exam
                </Text>
              </TouchableOpacity>

              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={styles.cancelButton}
                  onPress={() => setCreateAssessmentModalVisible(false)}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.confirmButton}
                  onPress={handleConfirmCreateAssessment}
                >
                  <LinearGradient
                    colors={['#84cc16', '#22c55e']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradientButton}
                  >
                    <Text style={styles.confirmButtonText}>Create</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </View>
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
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    justifyContent: 'center',
    alignItems: 'center'
  },
  subjectInfoHeader: {
    backgroundColor: '#171443',
    paddingHorizontal: 24,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060'
  },
  subjectInfoTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4
  },
  subjectInfoSubtitle: {
    fontSize: 14,
    color: '#cdd5df',
    marginBottom: 12
  },
  subjectCodeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2a2060',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    alignSelf: 'flex-start'
  },
  subjectCodeLabel: {
    fontSize: 12,
    color: '#cdd5df',
    marginRight: 8
  },
  subjectCode: {
    fontSize: 14,
    fontWeight: '600',
    color: '#22c55e',
    fontFamily: 'monospace',
    marginRight: 8
  },
  copyIcon: {
    fontSize: 16
  },
  actionSection: {
    paddingHorizontal: 24,
    paddingVertical: 20,
    gap: 12
  },
  actionButton: {
    borderRadius: 12,
    overflow: 'hidden'
  },
  gradientButton: {
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center'
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff'
  },
  section: {
    paddingHorizontal: 24,
    paddingBottom: 24
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 12
  },
  enrollmentCard: {
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
  enrollmentInfo: {
    marginBottom: 12
  },
  studentName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4
  },
  studentEmail: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 4
  },
  enrollmentDate: {
    fontSize: 12,
    color: '#94a3b8'
  },
  enrollmentActions: {
    flexDirection: 'row',
    gap: 8
  },
  approveButton: {
    flex: 1,
    backgroundColor: '#dcfce7',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center'
  },
  approveButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#16a34a'
  },
  rejectButton: {
    flex: 1,
    backgroundColor: '#fee2e2',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center'
  },
  rejectButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#dc2626'
  },
  studentCard: {
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
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40
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
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 10
  },
  modalHeader: {
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
  modalBody: {
    padding: 20
  },
  modalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 16
  },
  assessmentTypeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#e2e8f0',
    marginBottom: 12,
    backgroundColor: '#ffffff'
  },
  assessmentTypeButtonSelected: {
    borderColor: '#22c55e',
    backgroundColor: '#f0fdf4'
  },
  assessmentTypeIcon: {
    fontSize: 24,
    marginRight: 12
  },
  assessmentTypeText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#475569'
  },
  assessmentTypeTextSelected: {
    color: '#16a34a'
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    backgroundColor: '#f1f5f9',
    alignItems: 'center'
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#475569'
  },
  confirmButton: {
    flex: 1,
    borderRadius: 10,
    overflow: 'hidden'
  },
  confirmButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff'
  }
});

export default SubjectDashboardScreen;