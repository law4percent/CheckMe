// src/screens/student/DashboardScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
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
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../contexts/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import { ref, get } from 'firebase/database';
import { database } from '../../config/firebase';
import { joinSubjectWithCode } from '../../services/enrollmentService';

type Props = NativeStackScreenProps<RootStackParamList, 'StudentDashboard'>;

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface EnrolledSubject {
  subjectId: string;
  subjectName: string;
  subjectCode: string;
  teacherName: string;
  sectionName: string;
  year: string;
  teacherId: string;
}

interface StudentResult {
  assessmentUid: string;
  assessmentName: string;
  total_score: number;
  total_questions: number;
  percentage: number;
  checked_at: number;
  is_final_score: boolean;
  subjectName: string;
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

const pct = (score: number, total: number) =>
  total > 0 ? Math.round((score / total) * 100) : 0;

const scoreColor = (p: number) => {
  if (p >= 90) return '#22c55e';
  if (p >= 75) return '#3b82f6';
  if (p >= 60) return '#f59e0b';
  return '#ef4444';
};

const gradeLabel = (p: number) => {
  if (p >= 90) return 'A';
  if (p >= 85) return 'B+';
  if (p >= 80) return 'B';
  if (p >= 75) return 'C+';
  if (p >= 70) return 'C';
  if (p >= 65) return 'D+';
  if (p >= 60) return 'D';
  return 'F';
};

const formatDate = (ts: number) => {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
};

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

const StudentDashboardScreen: React.FC<Props> = () => {
  const { user, signOut } = useAuth();

  const [enrolledSubjects, setEnrolledSubjects] = useState<EnrolledSubject[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Modals
  const [profileModalVisible, setProfileModalVisible] = useState(false);
  const [joinModalVisible, setJoinModalVisible] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [joining, setJoining] = useState(false);

  // Subject scores modal
  const [scoresModalVisible, setScoresModalVisible] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<EnrolledSubject | null>(null);
  const [subjectResults, setSubjectResults] = useState<StudentResult[]>([]);
  const [loadingScores, setLoadingScores] = useState(false);

  // The school ID the student wrote on their answer sheet
  // = studentId field from their profile
  const schoolId = user?.role === 'student' ? user.studentId : '';

  // ── Load enrolled subjects ────────────────────
  const loadEnrolledSubjects = useCallback(async () => {
    if (!user?.uid) return;

    try {
      // Read all enrollments and find approved ones for this student
      const snapshot = await get(ref(database, 'enrollments'));
      if (!snapshot.exists()) {
        setEnrolledSubjects([]);
        return;
      }

      const allEnrollments = snapshot.val() as Record<string, Record<string, Record<string, any>>>;
      const subjects: EnrolledSubject[] = [];

      // Also fetch invite codes to resolve subject metadata
      const inviteCodesSnap = await get(ref(database, 'inviteCodes'));
      const inviteCodes = inviteCodesSnap.exists() ? inviteCodesSnap.val() : {};

      // Build subjectId → metadata map from invite codes
      const subjectMeta: Record<string, any> = {};
      Object.values(inviteCodes).forEach((ic: any) => {
        if (ic?.subjectId) subjectMeta[ic.subjectId] = ic;
      });

      // Walk enrollments/{teacherId}/{subjectId}/{studentUid}
      Object.entries(allEnrollments).forEach(([teacherId, teacherEnrollments]) => {
        Object.entries(teacherEnrollments).forEach(([subjectId, subjectEnrollments]) => {
          const myEnrollment = subjectEnrollments[user.uid];
          if (myEnrollment?.status === 'approved') {
            const meta = subjectMeta[subjectId];
            subjects.push({
              subjectId,
              subjectName: meta?.subjectName ?? myEnrollment.subjectName ?? 'Unknown Subject',
              subjectCode: meta?.code ?? '',
              teacherName: meta?.teacherName ?? 'Unknown Teacher',
              sectionName: meta?.sectionName ?? '',
              year: meta?.year ?? '',
              teacherId,
            });
          }
        });
      });

      setEnrolledSubjects(subjects);
    } catch (error: any) {
      console.error('❌ [StudentDashboard] Error loading subjects:', error);
      Alert.alert('Error', error.message);
    }
  }, [user?.uid]);

  // ── Load scores for a subject ─────────────────
  /**
   * Reads /answer_sheets/{teacherId}/{assessmentUid}/{schoolId}
   * Matches by schoolId (student's school-provided ID on the paper).
   * Also reads /assessments/{teacherId}/ to get assessment names.
   */
  const loadSubjectScores = async (subject: EnrolledSubject) => {
    if (!schoolId) {
      Alert.alert('Missing ID', 'Your student ID is not set. Contact your teacher.');
      return;
    }

    setLoadingScores(true);
    setSubjectResults([]);

    try {
      // Get all assessments for this teacher filtered to this subject
      const assessmentsSnap = await get(ref(database, `assessments/${subject.teacherId}`));
      if (!assessmentsSnap.exists()) {
        setSubjectResults([]);
        setLoadingScores(false);
        return;
      }

      const allAssessments = assessmentsSnap.val() as Record<string, any>;

      // Filter to assessments belonging to this subject
      const subjectAssessments = Object.entries(allAssessments).filter(
        ([, data]) => data.subject_uid === subject.subjectId
      );

      if (subjectAssessments.length === 0) {
        setSubjectResults([]);
        setLoadingScores(false);
        return;
      }

      const results: StudentResult[] = [];

      // For each assessment, check if this student has a result
      await Promise.all(
        subjectAssessments.map(async ([assessmentUid, assessmentData]) => {
          try {
            const sheetSnap = await get(
              ref(database, `answer_sheets/${subject.teacherId}/${assessmentUid}/${schoolId}`)
            );
            if (!sheetSnap.exists()) return;

            const sheet = sheetSnap.val();
            const percentage = pct(sheet.total_score ?? 0, sheet.total_questions ?? 0);

            results.push({
              assessmentUid,
              assessmentName: assessmentData.assessmentName ?? assessmentUid,
              total_score: sheet.total_score ?? 0,
              total_questions: sheet.total_questions ?? 0,
              percentage,
              checked_at: sheet.checked_at ?? 0,
              is_final_score: sheet.is_final_score ?? true,
              subjectName: subject.subjectName,
            });
          } catch {
            // No result for this assessment — skip
          }
        })
      );

      // Sort newest first
      results.sort((a, b) => b.checked_at - a.checked_at);
      setSubjectResults(results);
    } catch (error: any) {
      console.error('❌ [StudentDashboard] Error loading scores:', error);
      Alert.alert('Error', error.message);
    } finally {
      setLoadingScores(false);
    }
  };

  // ── Init ──────────────────────────────────────
  useEffect(() => {
    (async () => {
      setLoading(true);
      await loadEnrolledSubjects();
      setLoading(false);
    })();
  }, [loadEnrolledSubjects]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadEnrolledSubjects();
    setRefreshing(false);
  };

  // ── Handlers ──────────────────────────────────
  const handleSignOut = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: () => signOut() },
    ]);
  };

  const handleOpenSubject = async (subject: EnrolledSubject) => {
    setSelectedSubject(subject);
    setScoresModalVisible(true);
    await loadSubjectScores(subject);
  };

  const handleJoinSubject = async () => {
    if (!inviteCode.trim()) {
      Alert.alert('Error', 'Please enter an invite code');
      return;
    }
    if (!user?.uid) return;

    try {
      setJoining(true);
      const studentName = user.role === 'student'
        ? `${user.firstName} ${user.lastName}`
        : user.fullName ?? '';

      const result = await joinSubjectWithCode(
        inviteCode.trim().toUpperCase(),
        user.uid,
        studentName,
        user.email
      );

      setJoining(false);

      if (result.success) {
        setJoinModalVisible(false);
        Alert.alert('Success', result.message);
        await loadEnrolledSubjects();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error: any) {
      setJoining(false);
      Alert.alert('Error', error.message);
    }
  };

  // ── Loading ───────────────────────────────────
  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#3b82f6" />
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // ── Render ────────────────────────────────────
  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Welcome back,</Text>
            <TouchableOpacity onPress={() => setProfileModalVisible(true)} activeOpacity={0.7}>
              <Text style={styles.userName}>
                {user?.role === 'student'
                  ? `${user.firstName} ${user.lastName}`
                  : user?.fullName}
              </Text>
            </TouchableOpacity>
            <Text style={styles.studentIdLabel}>
              School ID: {schoolId || 'Not set'}
            </Text>
          </View>
          <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut}>
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>

        {/* School ID warning */}
        {!schoolId && (
          <View style={styles.warningBanner}>
            <Text style={styles.warningText}>
              ⚠️ Your school ID is not set. Answer sheets scanned by the Raspberry Pi
              use your school ID to find your results. Contact your teacher or update
              your profile.
            </Text>
          </View>
        )}

        {/* Join Subject */}
        <View style={styles.joinSection}>
          <TouchableOpacity
            style={styles.joinButton}
            onPress={() => { setInviteCode(''); setJoinModalVisible(true); }}
          >
            <LinearGradient
              colors={['#3b82f6', '#2563eb']}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.joinButtonText}>📚 Join Subject</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* My Subjects */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>My Subjects</Text>

          {enrolledSubjects.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>📚</Text>
              <Text style={styles.emptyTitle}>No subjects enrolled</Text>
              <Text style={styles.emptySub}>Ask your teacher for a subject code to join</Text>
            </View>
          ) : (
            enrolledSubjects.map(subject => (
              <TouchableOpacity
                key={subject.subjectId}
                style={styles.subjectCard}
                activeOpacity={0.7}
                onPress={() => handleOpenSubject(subject)}
              >
                <View style={styles.subjectCardHeader}>
                  <Text style={styles.subjectName}>{subject.subjectName}</Text>
                  {subject.subjectCode ? (
                    <Text style={styles.subjectCode}>{subject.subjectCode}</Text>
                  ) : null}
                </View>
                <Text style={styles.subjectMeta}>
                  {[subject.year, subject.sectionName].filter(Boolean).join('-')}
                  {subject.teacherName ? ` • ${subject.teacherName}` : ''}
                </Text>
                <Text style={styles.tapHint}>Tap to view your scores →</Text>
              </TouchableOpacity>
            ))
          )}
        </View>
      </ScrollView>

      {/* ── Profile Modal ────────────────────────── */}
      <Modal
        animationType="slide" transparent visible={profileModalVisible}
        onRequestClose={() => setProfileModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Profile</Text>
              <TouchableOpacity style={styles.closeBtn} onPress={() => setProfileModalVisible(false)}>
                <Text style={styles.closeBtnText}>✕ Close</Text>
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.modalBody}>
              {[
                ['First Name', user?.role === 'student' ? user.firstName : '—'],
                ['Last Name', user?.role === 'student' ? user.lastName : '—'],
                ['Email', user?.email ?? '—'],
                ['Username', user?.username ?? '—'],
                ['School ID', schoolId || 'Not set'],
                ['Role', user?.role ?? '—'],
              ].map(([label, value]) => (
                <View key={label} style={styles.profileField}>
                  <Text style={styles.profileLabel}>{label}</Text>
                  <Text style={styles.profileValue}>{value}</Text>
                </View>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* ── Join Subject Modal ───────────────────── */}
      <Modal
        animationType="slide" transparent visible={joinModalVisible}
        onRequestClose={() => setJoinModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Join Subject</Text>
              <TouchableOpacity style={styles.closeBtn} onPress={() => setJoinModalVisible(false)}>
                <Text style={styles.closeBtnText}>✕ Close</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.modalBody}>
              <Text style={styles.joinDesc}>
                Enter the invite code your teacher gave you.
              </Text>
              <Text style={styles.inputLabel}>Invite Code</Text>
              <TextInput
                style={styles.codeInput}
                placeholder="e.g. AB1234"
                placeholderTextColor="#94a3b8"
                value={inviteCode}
                onChangeText={t => setInviteCode(t.toUpperCase())}
                autoCapitalize="characters"
                maxLength={6}
                editable={!joining}
              />
              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleJoinSubject}
                disabled={joining}
              >
                <LinearGradient
                  colors={['#22c55e', '#16a34a']}
                  start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
                  style={styles.gradientButton}
                >
                  {joining
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={styles.submitButtonText}>Join</Text>
                  }
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Subject Scores Modal ─────────────────── */}
      <Modal
        animationType="slide" transparent visible={scoresModalVisible}
        onRequestClose={() => setScoresModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '90%' }]}>
            <View style={styles.modalHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.modalTitle}>
                  {selectedSubject?.subjectName ?? 'Scores'}
                </Text>
                {selectedSubject && (
                  <Text style={styles.modalSubtitle}>
                    {[selectedSubject.year, selectedSubject.sectionName].filter(Boolean).join('-')}
                    {selectedSubject.teacherName ? ` • ${selectedSubject.teacherName}` : ''}
                  </Text>
                )}
              </View>
              <TouchableOpacity style={styles.closeBtn} onPress={() => setScoresModalVisible(false)}>
                <Text style={styles.closeBtnText}>✕ Close</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              {loadingScores ? (
                <View style={styles.center}>
                  <ActivityIndicator size="large" color="#3b82f6" />
                  <Text style={styles.loadingText}>Loading scores...</Text>
                </View>
              ) : subjectResults.length === 0 ? (
                <View style={styles.emptyState}>
                  <Text style={styles.emptyIcon}>📝</Text>
                  <Text style={styles.emptyTitle}>No results yet</Text>
                  <Text style={styles.emptySub}>
                    Your results will appear here once the Raspberry Pi
                    scans your answer sheet.{'\n\n'}
                    Make sure you wrote your School ID ({schoolId || 'not set'}) clearly on the paper.
                  </Text>
                </View>
              ) : (
                <>
                  {/* Stats */}
                  <View style={styles.statsRow}>
                    {[
                      ['Assessments', String(subjectResults.length)],
                      ['Average', `${(subjectResults.reduce((s, r) => s + r.percentage, 0) / subjectResults.length).toFixed(1)}%`],
                      ['Best', `${Math.max(...subjectResults.map(r => r.percentage))}%`],
                    ].map(([label, value]) => (
                      <View key={label} style={styles.statCard}>
                        <Text style={styles.statValue}>{value}</Text>
                        <Text style={styles.statLabel}>{label}</Text>
                      </View>
                    ))}
                  </View>

                  {/* Result cards */}
                  {subjectResults.map((result, i) => {
                    const color = scoreColor(result.percentage);
                    return (
                      <View key={`${result.assessmentUid}-${i}`} style={styles.resultCard}>
                        <View style={styles.resultCardHeader}>
                          <View style={{ flex: 1, marginRight: 12 }}>
                            <Text style={styles.resultName}>{result.assessmentName}</Text>
                            <Text style={styles.resultDate}>{formatDate(result.checked_at)}</Text>
                            {!result.is_final_score && (
                              <View style={styles.pendingBadge}>
                                <Text style={styles.pendingText}>⏳ Pending</Text>
                              </View>
                            )}
                          </View>
                          <View style={{ alignItems: 'flex-end' }}>
                            <Text style={[styles.resultPct, { color }]}>{result.percentage}%</Text>
                            <Text style={[styles.resultGrade, { color }]}>{gradeLabel(result.percentage)}</Text>
                          </View>
                        </View>
                        <Text style={styles.resultFraction}>
                          {result.total_score} / {result.total_questions} correct
                        </Text>
                        <View style={styles.progressBg}>
                          <View style={[styles.progressFill, { width: `${result.percentage}%`, backgroundColor: color }]} />
                        </View>
                      </View>
                    );
                  })}
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
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollView: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
  loadingText: { marginTop: 12, fontSize: 16, color: '#64748b' },

  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start',
    paddingHorizontal: 24, paddingTop: 20, paddingBottom: 20,
    backgroundColor: '#171443', borderBottomWidth: 1, borderBottomColor: '#2a2060',
  },
  greeting: { fontSize: 16, color: '#cdd5df' },
  userName: { fontSize: 22, fontWeight: 'bold', color: '#ffffff', marginTop: 4, textDecorationLine: 'underline' },
  studentIdLabel: { fontSize: 13, color: '#94a3b8', marginTop: 2, fontFamily: 'monospace' },
  signOutButton: { backgroundColor: '#fee2e2', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  signOutText: { color: '#dc2626', fontWeight: '600', fontSize: 14 },

  warningBanner: {
    backgroundColor: '#fef3c7', marginHorizontal: 16, marginTop: 12,
    borderRadius: 10, padding: 12,
  },
  warningText: { fontSize: 13, color: '#92400e', lineHeight: 18 },

  joinSection: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 12 },
  joinButton: { borderRadius: 12, overflow: 'hidden' },
  gradientButton: { paddingVertical: 16, alignItems: 'center', justifyContent: 'center' },
  joinButtonText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },

  section: { paddingHorizontal: 24, paddingTop: 8, paddingBottom: 24 },
  sectionTitle: { fontSize: 22, fontWeight: 'bold', color: '#1e293b', marginBottom: 16 },

  emptyState: {
    alignItems: 'center', paddingVertical: 40,
    backgroundColor: '#ffffff', borderRadius: 12, padding: 24,
  },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#64748b', marginBottom: 6 },
  emptySub: { fontSize: 14, color: '#94a3b8', textAlign: 'center', lineHeight: 20 },

  subjectCard: {
    backgroundColor: '#ffffff', borderRadius: 12, padding: 20, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  subjectCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  subjectName: { fontSize: 17, fontWeight: '600', color: '#1e293b', flex: 1 },
  subjectCode: {
    fontSize: 13, fontWeight: '600', color: '#3b82f6',
    backgroundColor: '#dbeafe', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6,
  },
  subjectMeta: { fontSize: 13, color: '#64748b', marginBottom: 6 },
  tapHint: { fontSize: 12, color: '#3b82f6', fontWeight: '600' },

  // Modals
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center', alignItems: 'center', padding: 20,
  },
  modalContent: {
    backgroundColor: '#ffffff', borderRadius: 20,
    width: '100%', maxWidth: 500, maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: 20, paddingBottom: 15,
    borderBottomWidth: 1, borderBottomColor: '#e2e8f0',
  },
  modalTitle: { fontSize: 20, fontWeight: 'bold', color: '#1e293b' },
  modalSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
  closeBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6, backgroundColor: '#f1f5f9' },
  closeBtnText: { fontSize: 14, color: '#475569', fontWeight: '600' },
  modalBody: { padding: 20 },

  profileField: { marginBottom: 16 },
  profileLabel: { fontSize: 13, fontWeight: '600', color: '#475569', marginBottom: 6 },
  profileValue: {
    fontSize: 15, color: '#1e293b', paddingVertical: 10,
    paddingHorizontal: 14, backgroundColor: '#f8fafc', borderRadius: 8,
  },

  joinDesc: { fontSize: 14, color: '#64748b', marginBottom: 16, lineHeight: 20 },
  inputLabel: { fontSize: 14, fontWeight: '600', color: '#475569', marginBottom: 8 },
  codeInput: {
    backgroundColor: '#f8fafc', borderWidth: 2, borderColor: '#e2e8f0',
    borderRadius: 10, paddingHorizontal: 16, paddingVertical: 14,
    fontSize: 20, color: '#1e293b', fontFamily: 'monospace',
    textAlign: 'center', letterSpacing: 4, fontWeight: 'bold', marginBottom: 20,
  },
  submitButton: { borderRadius: 10, overflow: 'hidden' },
  submitButtonText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },

  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  statCard: {
    flex: 1, backgroundColor: '#f8fafc', borderRadius: 10,
    paddingVertical: 14, alignItems: 'center',
  },
  statValue: { fontSize: 20, fontWeight: 'bold', color: '#1e293b', marginBottom: 4 },
  statLabel: { fontSize: 11, color: '#64748b', fontWeight: '600' },

  resultCard: {
    backgroundColor: '#ffffff', borderRadius: 12, padding: 16, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  resultCardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  resultName: { fontSize: 15, fontWeight: '600', color: '#1e293b', marginBottom: 4 },
  resultDate: { fontSize: 12, color: '#64748b' },
  pendingBadge: {
    alignSelf: 'flex-start', backgroundColor: '#fef3c7',
    paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, marginTop: 4,
  },
  pendingText: { fontSize: 11, color: '#d97706', fontWeight: '600' },
  resultPct: { fontSize: 24, fontWeight: 'bold' },
  resultGrade: { fontSize: 14, fontWeight: '600' },
  resultFraction: { fontSize: 13, color: '#64748b', marginBottom: 8 },
  progressBg: { height: 6, backgroundColor: '#e2e8f0', borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 3 },
});

export default StudentDashboardScreen;