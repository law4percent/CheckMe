// src/screens/teacher/SubjectDashboardScreen.tsx
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
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, Assessment } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';
import {
  getSubjectEnrollments,
  approveEnrollment,
  rejectEnrollment,
  removeEnrollment,
  Enrollment
} from '../../services/enrollmentService';
import { getSubjectInviteCode } from '../../services/inviteCodeService';
import {
  createAssessment,
  getAssessments,
  deleteAssessment,
} from '../../services/assessmentService';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherSubjectDashboard'>;

const SubjectDashboardScreen: React.FC<Props> = ({ route, navigation }) => {
  const { subject, section } = route.params;
  const { user } = useAuth();

  // State
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [inviteCode, setInviteCode] = useState<string | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);

  // Modal states
  const [createAssessmentModalVisible, setCreateAssessmentModalVisible] = useState(false);
  const [selectedAssessmentType, setSelectedAssessmentType] = useState<'quiz' | 'exam' | null>(null);
  const [assessmentName, setAssessmentName] = useState('');
  const [enrolledStudentsModalVisible, setEnrolledStudentsModalVisible] = useState(false);
  const [isEditingEnrollments, setIsEditingEnrollments] = useState(false);
  const [pendingEnrollmentsModalVisible, setPendingEnrollmentsModalVisible] = useState(false);

  useEffect(() => {
    if (subject.id && user?.uid) {
      loadEnrollments();
      loadInviteCode();
      loadExistingAssessment();
    }
  }, [subject.id, user?.uid]);

  // ── Load existing assessment for this subject ──
  const loadExistingAssessment = async () => {
    if (!user?.uid) {
      setAssessments([]);
      return;
    }

    try {
      const result = await getAssessments(user.uid, subject.id);
      const sorted = result.sort((a, b) => b.createdAt - a.createdAt);
      setAssessments(sorted);
    } catch (error: any) {
      console.error('❌ [SubjectDashboard] Error loading assessments:', error);
      setAssessments([]);
    }
  };

  const loadEnrollments = async () => {
    if (!user?.uid) return;
    try {
      setLoading(true);
      const fetched = await getSubjectEnrollments(user.uid, subject.id);
      setEnrollments(fetched);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadInviteCode = async () => {
    if (!user?.uid) return;
    try {
      const code = await getSubjectInviteCode(user.uid, subject.id);
      setInviteCode(code);
    } catch (error: any) {
      console.error('❌ Error loading invite code:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadEnrollments(), loadInviteCode(), loadExistingAssessment()]);
    setRefreshing(false);
  };

  // ── Create Assessment ─────────────────────────
  const handleCreateAssessment = () => {
    setSelectedAssessmentType(null);
    setAssessmentName('');
    setCreateAssessmentModalVisible(true);
  };

  const handleConfirmCreateAssessment = async () => {
    if (!selectedAssessmentType) {
      Alert.alert('Error', 'Please select assessment type');
      return;
    }
    if (!assessmentName.trim()) {
      Alert.alert('Error', 'Please enter assessment name');
      return;
    }
    if (!user?.uid) {
      Alert.alert('Error', 'User not authenticated');
      return;
    }

    try {
      setActionLoading(true);

      // NEW: createAssessment now takes (teacherId, name, type, sectionUid, subjectUid)
      // Path written: /assessments/{teacherId}/{assessmentUid}/
      const assessment = await createAssessment(
        user.uid,
        assessmentName.trim(),
        selectedAssessmentType,
        section.id,   // sectionUid
        subject.id    // subjectUid
      );

      setAssessments(prev => [assessment, ...prev]);
      setCreateAssessmentModalVisible(false);

      Alert.alert(
        'Success! 🎉',
        `Assessment "${assessment.assessmentName}" created!\n\nAssessment UID: ${assessment.assessmentUid}\n\nWrite this UID at the top of your answer key paper before scanning.`,
        [{ text: 'OK' }]
      );

      setSelectedAssessmentType(null);
      setAssessmentName('');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create assessment');
    } finally {
      setActionLoading(false);
    }
  };

  // ── Delete Assessment ─────────────────────────
  const handleDeleteAssessment = (assessment: Assessment) => {
    Alert.alert(
      '⚠️ Delete Assessment',
      `Are you sure you want to delete "${assessment.assessmentName}"?\n\nAssessment UID: ${assessment.assessmentUid}\n\nThis will permanently delete:\n• The assessment record\n• The scanned answer key\n• All student answer sheets and scores\n\nThis action cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            if (!user?.uid) return;
            try {
              setActionLoading(true);
              await deleteAssessment(user.uid, assessment.assessmentUid);
              setAssessments(prev => prev.filter(a => a.assessmentUid !== assessment.assessmentUid));
              Alert.alert('Success', 'Assessment deleted successfully');
            } catch (error: any) {
              Alert.alert('Error', error.message);
            } finally {
              setActionLoading(false);
            }
          }
        }
      ]
    );
  };

  // ── View Scores ───────────────────────────────
  const handleViewAnswerKeys = () => {
    if (!user?.uid) return;
    navigation.navigate('AnswerKeys', {
      teacherUid: user.uid,
      subjectUid: subject.id,
      subjectName: subject.subjectName,
    });
  };

  const handleViewScores = (assessment: Assessment) => {
    if (!user?.uid) return;
    navigation.navigate('ViewScores', {
      assessmentUid: assessment.assessmentUid,
      assessmentName: assessment.assessmentName,
      teacherUid: user.uid,
      subjectUid: assessment.subjectUid,
    });
  };

  // ── Enrollment handlers ───────────────────────
  const handleViewEnrolledStudents = () => {
    setIsEditingEnrollments(false);
    setEnrolledStudentsModalVisible(true);
  };

  const handleViewPendingEnrollments = () => {
    setPendingEnrollmentsModalVisible(true);
  };

  const handleUnenrollStudent = async (studentId: string, studentName: string) => {
    Alert.alert(
      'Unenroll Student',
      `Are you sure you want to unenroll ${studentName}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Unenroll',
          style: 'destructive',
          onPress: async () => {
            if (!user?.uid) return;
            try {
              setActionLoading(true);
              await removeEnrollment(user.uid, subject.id, studentId);
              await loadEnrollments();
              Alert.alert('Success', `${studentName} has been unenrolled`);
            } catch (error: any) {
              Alert.alert('Error', error.message);
            } finally {
              setActionLoading(false);
            }
          }
        }
      ]
    );
  };

  const handleCopyInviteCode = () => {
    if (!inviteCode) {
      Alert.alert('Error', 'No invite code available.');
      return;
    }
    Clipboard.setString(inviteCode);
    Alert.alert('Copied!', 'Invite code copied to clipboard');
  };

  const handleApproveEnrollment = async (enrollment: Enrollment) => {
    if (!user?.uid) return;
    try {
      setActionLoading(true);
      await approveEnrollment(user.uid, subject.id, enrollment.studentId);
      setEnrollments(enrollments.map(e =>
        e.studentId === enrollment.studentId
          ? { ...e, status: 'approved', approvedAt: Date.now() }
          : e
      ));
      Alert.alert('Success', `${enrollment.studentName} has been approved!`);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectEnrollment = async (enrollment: Enrollment) => {
    if (!user?.uid) return;
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
              await rejectEnrollment(user.uid, subject.id, enrollment.studentId);
              setEnrollments(enrollments.map(e =>
                e.studentId === enrollment.studentId
                  ? { ...e, status: 'rejected' }
                  : e
              ));
              Alert.alert('Success', 'Enrollment rejected');
            } catch (error: any) {
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
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Subject Info Header */}
        <View style={styles.subjectInfoHeader}>
          <Text style={styles.subjectInfoTitle}>{subject.subjectName}</Text>
          <Text style={styles.subjectInfoSubtitle}>
            {section.year}-{section.sectionName}
          </Text>
          {inviteCode && (
            <TouchableOpacity style={styles.inviteCodeContainer} onPress={handleCopyInviteCode}>
              <Text style={styles.inviteCodeLabel}>Invite Code:</Text>
              <Text style={styles.inviteCodeText}>{inviteCode}</Text>
              <Text style={styles.copyIcon}>📋</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Create Assessment Button */}
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
        </View>

        {/* Assessments Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Assessments</Text>
            <View style={styles.headerButtonsContainer}>
              <TouchableOpacity style={styles.answerKeysHeaderButton} onPress={handleViewAnswerKeys} disabled={actionLoading}>
                <Text style={styles.answerKeysHeaderButtonText}>🗝️ Answer Keys</Text>
              </TouchableOpacity>
              {pendingEnrollments.length > 0 && (
                <TouchableOpacity onPress={handleViewPendingEnrollments}>
                  <Text style={[styles.sectionTitle, styles.clickableTitle, styles.pendingBadge]}>
                    Pending ({pendingEnrollments.length}) 🔔
                  </Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity onPress={handleViewEnrolledStudents}>
                <Text style={[styles.sectionTitle, styles.clickableTitle]}>
                  Enrolled ({approvedEnrollments.length}) 👁️
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          {assessments.length > 0 ? (
            assessments.map(assessment => (
              <View key={assessment.assessmentUid} style={styles.assessmentCard}>
                <View style={styles.assessmentHeader}>
                  <Text style={styles.assessmentIcon}>
                    {assessment.assessmentType === 'quiz' ? '📝' : '📄'}
                  </Text>
                  <View style={styles.assessmentInfo}>
                    <Text style={styles.assessmentName}>{assessment.assessmentName}</Text>
                    <Text style={styles.assessmentType}>
                      {assessment.assessmentType.charAt(0).toUpperCase() +
                        assessment.assessmentType.slice(1)}
                    </Text>
                    <Text style={styles.assessmentUid}>UID: {assessment.assessmentUid}</Text>
                  </View>
                </View>

                <View style={styles.assessmentMeta}>
                  <Text style={styles.assessmentDate}>
                    Created: {new Date(assessment.createdAt).toLocaleDateString()}
                  </Text>
                  <View style={styles.assessmentStatus}>
                    <View style={[styles.statusDot, { backgroundColor: '#22c55e' }]} />
                    <Text style={styles.statusText}>Active</Text>
                  </View>
                </View>

                <View style={styles.assessmentActions}>
                  <TouchableOpacity style={styles.viewScoresButton} onPress={() => handleViewScores(assessment)}>
                    <Text style={styles.viewScoresButtonText}>📊 View Scores</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.deleteAssessmentButton} onPress={() => handleDeleteAssessment(assessment)}>
                    <Text style={styles.deleteAssessmentButtonText}>🗑️ Delete</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>📝</Text>
              <Text style={styles.emptyStateText}>No assessments yet</Text>
              <Text style={styles.emptyStateSubtext}>
                Create an assessment to get started
              </Text>
            </View>
          )}
        </View>
      </ScrollView>

      {/* Loading Overlay */}
      {actionLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#22c55e" />
        </View>
      )}

      {/* ── Create Assessment Modal ───────────────── */}
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
              <Text style={styles.modalLabel}>Assessment Name</Text>
              <TextInput
                style={styles.textInput}
                placeholder="Enter assessment name"
                placeholderTextColor="#94a3b8"
                value={assessmentName}
                onChangeText={setAssessmentName}
                autoCapitalize="words"
              />

              <Text style={[styles.modalLabel, { marginTop: 20 }]}>Assessment Type</Text>

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
                ]}>Quiz</Text>
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
                ]}>Exam</Text>
              </TouchableOpacity>

              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={styles.cancelButton}
                  onPress={() => setCreateAssessmentModalVisible(false)}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.confirmButton} onPress={handleConfirmCreateAssessment}>
                  <LinearGradient
                    colors={['#84cc16', '#22c55e']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradientButton}
                  >
                    {actionLoading
                      ? <ActivityIndicator color="#ffffff" />
                      : <Text style={styles.confirmButtonText}>Create</Text>
                    }
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Enrolled Students Modal ───────────────── */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={enrolledStudentsModalVisible}
        onRequestClose={() => setEnrolledStudentsModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Enrolled Students ({approvedEnrollments.length})</Text>
            </View>
            <ScrollView style={styles.modalScrollView}>
              <View style={styles.modalBody}>
                {approvedEnrollments.length === 0 ? (
                  <View style={styles.emptyState}>
                    <Text style={styles.emptyStateIcon}>👥</Text>
                    <Text style={styles.emptyStateText}>No enrolled students</Text>
                  </View>
                ) : (
                  approvedEnrollments.map(enrollment => (
                    <View key={enrollment.studentId} style={styles.enrolledStudentItem}>
                      <View style={styles.enrolledStudentInfo}>
                        <Text style={styles.studentName}>{enrollment.studentName}</Text>
                        <Text style={styles.studentEmail}>{enrollment.studentEmail}</Text>
                      </View>
                      {isEditingEnrollments && (
                        <TouchableOpacity
                          style={styles.unenrollButton}
                          onPress={() => handleUnenrollStudent(enrollment.studentId, enrollment.studentName || 'Student')}
                        >
                          <Text style={styles.unenrollButtonText}>Unenroll</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  ))
                )}
                <View style={styles.modalActions}>
                  {approvedEnrollments.length > 0 && (
                    <TouchableOpacity
                      style={styles.editButton}
                      onPress={() => setIsEditingEnrollments(!isEditingEnrollments)}
                    >
                      <Text style={styles.editButtonText}>
                        {isEditingEnrollments ? '✓ Done' : '✏️ Edit'}
                      </Text>
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={styles.closeButton}
                    onPress={() => {
                      setEnrolledStudentsModalVisible(false);
                      setIsEditingEnrollments(false);
                    }}
                  >
                    <Text style={styles.closeButtonText}>Close</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* ── Pending Enrollments Modal ─────────────── */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={pendingEnrollmentsModalVisible}
        onRequestClose={() => setPendingEnrollmentsModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Pending Enrollments ({pendingEnrollments.length})</Text>
            </View>
            <ScrollView style={styles.modalScrollView}>
              <View style={styles.modalBody}>
                {pendingEnrollments.length === 0 ? (
                  <View style={styles.emptyState}>
                    <Text style={styles.emptyStateIcon}>✅</Text>
                    <Text style={styles.emptyStateText}>No pending requests</Text>
                  </View>
                ) : (
                  pendingEnrollments.map(enrollment => (
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
                  ))
                )}
                <View style={styles.modalActions}>
                  <TouchableOpacity
                    style={styles.closeButton}
                    onPress={() => setPendingEnrollmentsModalVisible(false)}
                  >
                    <Text style={styles.closeButtonText}>Close</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollView: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 16, color: '#64748b' },
  loadingOverlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.3)', justifyContent: 'center', alignItems: 'center'
  },
  subjectInfoHeader: {
    backgroundColor: '#171443', paddingHorizontal: 24, paddingVertical: 20,
    borderBottomWidth: 1, borderBottomColor: '#2a2060'
  },
  subjectInfoTitle: { fontSize: 24, fontWeight: 'bold', color: '#ffffff', marginBottom: 4 },
  subjectInfoSubtitle: { fontSize: 14, color: '#cdd5df', marginBottom: 12 },
  copyIcon: { fontSize: 16 },
  headerButtonsContainer: { flexDirection: 'row', gap: 12, alignItems: 'center' },
  pendingBadge: { color: '#f59e0b', marginRight: 8 },
  actionSection: { paddingHorizontal: 24, paddingVertical: 20 },
  actionButton: { borderRadius: 12, overflow: 'hidden' },
  gradientButton: { paddingVertical: 16, alignItems: 'center', justifyContent: 'center' },
  actionButtonText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },
  section: { paddingHorizontal: 24, paddingBottom: 24 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', color: '#1e293b' },
  clickableTitle: { color: '#6366f1', textDecorationLine: 'underline' },
  inviteCodeContainer: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#22c55e',
    paddingHorizontal: 12, paddingVertical: 10, borderRadius: 8,
    marginTop: 8, alignSelf: 'flex-start'
  },
  inviteCodeLabel: { fontSize: 12, color: '#ffffff', marginRight: 8, fontWeight: '600' },
  inviteCodeText: {
    fontSize: 16, fontWeight: 'bold', color: '#ffffff',
    fontFamily: 'monospace', marginRight: 8, letterSpacing: 2
  },
  emptyState: { alignItems: 'center', justifyContent: 'center', paddingVertical: 40 },
  emptyStateIcon: { fontSize: 48, marginBottom: 16 },
  emptyStateText: { fontSize: 18, color: '#64748b', fontWeight: '600', marginBottom: 8 },
  emptyStateSubtext: { fontSize: 14, color: '#94a3b8', textAlign: 'center' },
  assessmentCard: {
    backgroundColor: '#ffffff', borderRadius: 12, padding: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1, shadowRadius: 4, elevation: 3,
    borderLeftWidth: 4, borderLeftColor: '#6366f1'
  },
  assessmentHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  assessmentIcon: { fontSize: 40, marginRight: 12 },
  assessmentInfo: { flex: 1 },
  assessmentName: { fontSize: 18, fontWeight: 'bold', color: '#1e293b', marginBottom: 4 },
  assessmentType: { fontSize: 14, color: '#6366f1', fontWeight: '600', marginBottom: 2 },
  assessmentUid: { fontSize: 12, color: '#94a3b8', fontFamily: 'monospace' },
  assessmentMeta: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 8, borderTopWidth: 1, borderTopColor: '#f1f5f9', marginBottom: 12
  },
  assessmentDate: { fontSize: 12, color: '#64748b' },
  assessmentStatus: { flexDirection: 'row', alignItems: 'center' },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  statusText: { fontSize: 12, color: '#22c55e', fontWeight: '600' },
  assessmentActions: { flexDirection: 'row', gap: 8 },
  answerKeysHeaderButton: {
    backgroundColor: '#fef3c7',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
  },
  answerKeysHeaderButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#d97706',
  },
  viewScoresButton: { flex: 1, backgroundColor: '#dbeafe', paddingVertical: 12, borderRadius: 8, alignItems: 'center' },
  viewScoresButtonText: { fontSize: 14, fontWeight: '600', color: '#2563eb' },
  deleteAssessmentButton: { backgroundColor: '#fee2e2', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 8, alignItems: 'center' },
  deleteAssessmentButtonText: { fontSize: 14, fontWeight: '600', color: '#dc2626' },
  enrollmentCard: {
    backgroundColor: '#ffffff', borderRadius: 12, padding: 16, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2
  },
  enrollmentInfo: { marginBottom: 12 },
  studentName: { fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 4 },
  studentEmail: { fontSize: 14, color: '#64748b', marginBottom: 4 },
  enrollmentDate: { fontSize: 12, color: '#94a3b8' },
  enrollmentActions: { flexDirection: 'row', gap: 8 },
  approveButton: { flex: 1, backgroundColor: '#dcfce7', paddingVertical: 10, borderRadius: 8, alignItems: 'center' },
  approveButtonText: { fontSize: 14, fontWeight: '600', color: '#16a34a' },
  rejectButton: { flex: 1, backgroundColor: '#fee2e2', paddingVertical: 10, borderRadius: 8, alignItems: 'center' },
  rejectButtonText: { fontSize: 14, fontWeight: '600', color: '#dc2626' },
  enrolledStudentItem: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#e2e8f0'
  },
  enrolledStudentInfo: { flex: 1 },
  unenrollButton: { backgroundColor: '#fee2e2', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  unenrollButtonText: { fontSize: 14, fontWeight: '600', color: '#dc2626' },
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center', alignItems: 'center', padding: 20
  },
  modalContent: {
    backgroundColor: '#ffffff', borderRadius: 20,
    width: '100%', maxWidth: 500, maxHeight: '80%',
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3, shadowRadius: 10, elevation: 10
  },
  modalHeader: {
    paddingHorizontal: 20, paddingTop: 20, paddingBottom: 15,
    borderBottomWidth: 1, borderBottomColor: '#e2e8f0'
  },
  modalTitle: { fontSize: 22, fontWeight: 'bold', color: '#1e293b' },
  modalBody: { padding: 20 },
  modalLabel: { fontSize: 16, fontWeight: '600', color: '#475569', marginBottom: 12 },
  textInput: {
    backgroundColor: '#f8fafc', borderWidth: 1, borderColor: '#e2e8f0',
    borderRadius: 10, paddingHorizontal: 16, paddingVertical: 12,
    fontSize: 16, color: '#1e293b', marginBottom: 8
  },
  modalScrollView: { maxHeight: '70%' },
  modalActions: { flexDirection: 'row', gap: 12, marginTop: 20 },
  cancelButton: { flex: 1, paddingVertical: 14, borderRadius: 10, backgroundColor: '#f1f5f9', alignItems: 'center' },
  cancelButtonText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  confirmButton: { flex: 1, borderRadius: 10, overflow: 'hidden' },
  confirmButtonText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },
  editButton: { flex: 1, paddingVertical: 14, borderRadius: 10, backgroundColor: '#dbeafe', alignItems: 'center', marginRight: 8 },
  editButtonText: { fontSize: 16, fontWeight: '600', color: '#2563eb' },
  closeButton: { flex: 1, paddingVertical: 14, borderRadius: 10, backgroundColor: '#f1f5f9', alignItems: 'center' },
  closeButtonText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  assessmentTypeButton: {
    flexDirection: 'row', alignItems: 'center', padding: 16,
    borderRadius: 12, borderWidth: 2, borderColor: '#e2e8f0',
    marginBottom: 12, backgroundColor: '#ffffff'
  },
  assessmentTypeButtonSelected: { borderColor: '#22c55e', backgroundColor: '#f0fdf4' },
  assessmentTypeIcon: { fontSize: 24, marginRight: 12 },
  assessmentTypeText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  assessmentTypeTextSelected: { color: '#16a34a' },
});

export default SubjectDashboardScreen;