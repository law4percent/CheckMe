// src/screens/teacher/SectionDashboardScreen.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  TouchableOpacity,
  Modal,
  TextInput,
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
  createSubject,
  getSectionSubjects,
  updateSubject,
  deleteSubject,
  Subject,
} from '../../services/subjectService';
import { updateSectionSubjectCount } from '../../services/sectionService';
import { deleteSubjectCascade, getAssessments } from '../../services/assessmentService';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherSectionDashboard'>;

const SectionDashboardScreen: React.FC<Props> = ({ route, navigation }) => {
  const { section } = route.params;
  const { user } = useAuth();

  const [subjects, setSubjects]         = useState<Subject[]>([]);
  const [loading, setLoading]           = useState(true);
  const [refreshing, setRefreshing]     = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Assessment count per subject
  const [assessmentCounts, setAssessmentCounts] = useState<Record<string, number>>({});

  // Delete confirmation modal
  const [deleteSubjectTarget, setDeleteSubjectTarget] = useState<Subject | null>(null);

  // Create Subject Modal
  const [createSubjectModalVisible, setCreateSubjectModalVisible] = useState(false);
  const [newSubjectName, setNewSubjectName] = useState('');

  // Edit Subject Modal
  const [editSubjectModalVisible, setEditSubjectModalVisible] = useState(false);
  const [editingSubjectId, setEditingSubjectId] = useState<string | null>(null);
  const [editSubjectName, setEditSubjectName] = useState('');

  // Subject Details Modal
  const [subjectDetailsModalVisible, setSubjectDetailsModalVisible] = useState(false);
  const [selectedSubjectForDetails, setSelectedSubjectForDetails] = useState<Subject | null>(null);

  useEffect(() => {
    if (user?.uid && section.id) loadSubjects();
  }, [user?.uid, section.id]);

  const loadSubjects = async () => {
    if (!user?.uid) return;
    try {
      setLoading(true);
      const fetchedSubjects = await getSectionSubjects(user.uid, section.id);
      setSubjects(fetchedSubjects);
      if (fetchedSubjects.length !== section.subjectCount) {
        await updateSectionSubjectCount(user.uid, section.id, fetchedSubjects.length);
      }

      // Load assessment counts for each subject
      const counts: Record<string, number> = {};
      await Promise.all(
        fetchedSubjects.map(async s => {
          const a = await getAssessments(user!.uid!, s.id);
          counts[s.id] = a.length;
        })
      );
      setAssessmentCounts(counts);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadSubjects();
    setRefreshing(false);
  };

  // ── Create Subject ─────────────────────────────
  const handleCreateSubject = () => {
    setNewSubjectName('');
    setCreateSubjectModalVisible(true);
  };

  const handleConfirmCreateSubject = async () => {
    if (!user?.uid || !newSubjectName.trim()) {
      Alert.alert('Error', 'Please enter a subject name');
      return;
    }
    try {
      setActionLoading(true);
      const newSubject = await createSubject({
        year: section.year,
        subjectName: newSubjectName,
        teacherId: user.uid,
        sectionId: section.id,
        teacherName: user.role === 'teacher' ? user.fullName : undefined,
        sectionName: section.sectionName,
      });
      setSubjects([newSubject, ...subjects]);
      await updateSectionSubjectCount(user.uid, section.id, subjects.length + 1);
      setCreateSubjectModalVisible(false);
      Alert.alert('Success', `Subject "${newSubjectName}" created!`);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Edit Subject ───────────────────────────────
  const handleEditSubject = (subject: Subject) => {
    setEditingSubjectId(subject.id);
    setEditSubjectName(subject.subjectName);
    setEditSubjectModalVisible(true);
  };

  const handleConfirmEditSubject = async () => {
    if (!user?.uid || !editingSubjectId || !editSubjectName.trim()) {
      Alert.alert('Error', 'Please enter a subject name');
      return;
    }
    try {
      setActionLoading(true);
      await updateSubject(user.uid, section.id, editingSubjectId, { subjectName: editSubjectName });
      setSubjects(subjects.map(s =>
        s.id === editingSubjectId
          ? { ...s, subjectName: editSubjectName.trim(), updatedAt: Date.now() }
          : s
      ));
      setEditSubjectModalVisible(false);
      Alert.alert('Success', 'Subject updated successfully!');
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Delete Subject (cascade) ───────────────────
  const handleDeleteSubject = (subject: Subject) => {
    setDeleteSubjectTarget(subject);
  };

  const confirmDeleteSubject = async () => {
    if (!deleteSubjectTarget || !user?.uid) return;
    try {
      setActionLoading(true);
      await deleteSubjectCascade(user.uid, section.id, deleteSubjectTarget.id);
      const newSubjects = subjects.filter(s => s.id !== deleteSubjectTarget.id);
      setSubjects(newSubjects);
      await updateSectionSubjectCount(user.uid, section.id, newSubjects.length);
      setDeleteSubjectTarget(null);
      Alert.alert('Deleted', 'Subject and all related data removed.');
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubjectPress = (subject: Subject) => {
    navigation.navigate('TeacherSubjectDashboard', { subject, section });
  };

  const handleCopyToClipboard = (text: string, label: string) => {
    Clipboard.setString(text);
    Alert.alert('Copied!', `${label} copied to clipboard`);
  };

  const formatDate = (timestamp: number) =>
    new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#22c55e" />
          <Text style={styles.loadingText}>Loading subjects...</Text>
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
        {/* Section Info Header */}
        <View style={styles.sectionInfoHeader}>
          <Text style={styles.sectionInfoTitle}>{section.year}-{section.sectionName}</Text>
          <Text style={styles.sectionInfoSubtitle}>
            {subjects.length} {subjects.length === 1 ? 'subject' : 'subjects'}
          </Text>
        </View>

        {/* Manage Subjects */}
        <View style={styles.manageSections}>
          <View style={styles.subjectHeader}>
            <Text style={styles.subjectTitle}>Subjects</Text>
            <TouchableOpacity
              style={styles.createButton}
              onPress={handleCreateSubject}
              disabled={actionLoading}
            >
              <Text style={styles.createButtonText}>+ Create Subject</Text>
            </TouchableOpacity>
          </View>

          {subjects.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>📚</Text>
              <Text style={styles.emptyStateText}>No subjects yet</Text>
              <Text style={styles.emptyStateSubtext}>Create your first subject to get started</Text>
            </View>
          ) : (
            subjects.map(subject => (
              <View key={subject.id} style={styles.subjectCard}>
                <TouchableOpacity
                  style={styles.subjectCardContent}
                  onPress={() => handleSubjectPress(subject)}
                  activeOpacity={0.7}
                  disabled={actionLoading}
                >
                  <View style={styles.subjectCardContentRow}>
                    <View style={styles.subjectCardInfo}>
                      <Text style={styles.subjectCardTitle}>{subject.subjectName}</Text>
                      <Text style={styles.subjectCardDetails}>
                        {subject.studentCount} enrolled{'  ·  '}
                        {assessmentCounts[subject.id] ?? 0}{' '}
                        {(assessmentCounts[subject.id] ?? 0) === 1 ? 'assessment' : 'assessments'}
                      </Text>
                    </View>
                    <TouchableOpacity
                      style={styles.detailIconButton}
                      onPress={() => {
                        setSelectedSubjectForDetails(subject);
                        setSubjectDetailsModalVisible(true);
                      }}
                      disabled={actionLoading}
                    >
                      <Text style={styles.detailIconText}>ℹ️</Text>
                    </TouchableOpacity>
                  </View>
                </TouchableOpacity>

                {/* Icon-only action row */}
                <View style={styles.cardActions}>
                  <TouchableOpacity
                    style={styles.iconActionBtn}
                    onPress={() => handleEditSubject(subject)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.iconActionText}>✏️</Text>
                  </TouchableOpacity>
                  <View style={styles.iconActionDivider} />
                  <TouchableOpacity
                    style={styles.iconActionBtnDanger}
                    onPress={() => handleDeleteSubject(subject)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.iconActionText}>🗑️</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      {actionLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#22c55e" />
        </View>
      )}

      {/* ── Create Subject Modal ─────────────────── */}
      <Modal animationType="slide" transparent visible={createSubjectModalVisible} onRequestClose={() => setCreateSubjectModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Create New Subject</Text>
            </View>
            <View style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Subject Name</Text>
                <TextInput
                  style={styles.modalInput}
                  value={newSubjectName}
                  onChangeText={setNewSubjectName}
                  placeholder="e.g., Mathematics"
                  autoCapitalize="words"
                  editable={!actionLoading}
                />
              </View>
              <View style={styles.modalButtonRow}>
                <TouchableOpacity style={styles.cancelButton} onPress={() => setCreateSubjectModalVisible(false)} disabled={actionLoading}>
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.confirmButton} onPress={handleConfirmCreateSubject} disabled={actionLoading}>
                  <LinearGradient colors={['#84cc16', '#22c55e']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.gradientButton}>
                    {actionLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.confirmButtonText}>Create</Text>}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Edit Subject Modal ───────────────────── */}
      <Modal animationType="slide" transparent visible={editSubjectModalVisible} onRequestClose={() => setEditSubjectModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit Subject</Text>
            </View>
            <View style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Subject Name</Text>
                <TextInput
                  style={styles.modalInput}
                  value={editSubjectName}
                  onChangeText={setEditSubjectName}
                  placeholder="e.g., Mathematics"
                  autoCapitalize="words"
                  editable={!actionLoading}
                />
              </View>
              <View style={styles.modalButtonRow}>
                <TouchableOpacity style={styles.cancelButton} onPress={() => setEditSubjectModalVisible(false)} disabled={actionLoading}>
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.confirmButton} onPress={handleConfirmEditSubject} disabled={actionLoading}>
                  <LinearGradient colors={['#84cc16', '#22c55e']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.gradientButton}>
                    {actionLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.confirmButtonText}>Save Changes</Text>}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Subject Details Modal ────────────────── */}
      <Modal animationType="fade" transparent visible={subjectDetailsModalVisible} onRequestClose={() => setSubjectDetailsModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Subject Details</Text>
              <TouchableOpacity style={styles.iconButton} onPress={() => setSubjectDetailsModalVisible(false)}>
                <Text style={styles.iconButtonText}>✕ Close</Text>
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Subject Name</Text>
                <Text style={styles.modalValue}>{selectedSubjectForDetails?.subjectName}</Text>
              </View>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Enrolled Students</Text>
                <Text style={styles.modalValue}>{selectedSubjectForDetails?.studentCount ?? 0}</Text>
              </View>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Assessments Created</Text>
                <Text style={styles.modalValue}>
                  {selectedSubjectForDetails ? (assessmentCounts[selectedSubjectForDetails.id] ?? 0) : 0}
                </Text>
              </View>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Created At</Text>
                <Text style={styles.modalValue}>
                  {selectedSubjectForDetails?.createdAt ? formatDate(selectedSubjectForDetails.createdAt) : 'N/A'}
                </Text>
              </View>
              {[
                { label: 'Subject ID (UID)', val: selectedSubjectForDetails?.id },
                { label: 'Section ID (UID)', val: selectedSubjectForDetails?.sectionId },
                { label: 'Teacher ID (UID)', val: selectedSubjectForDetails?.teacherId },
              ].map(row => (
                <View key={row.label} style={styles.modalField}>
                  <Text style={styles.modalLabel}>{row.label}</Text>
                  <View style={styles.uidContainer}>
                    <Text style={[styles.modalValue, styles.monoValue]}>{row.val}</Text>
                    <TouchableOpacity style={styles.copyButton} onPress={() => handleCopyToClipboard(row.val || '', row.label)}>
                      <Text style={styles.copyButtonText}>📋 Copy</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* ── Delete Subject Confirmation Modal ─────── */}
      <Modal visible={deleteSubjectTarget !== null} transparent animationType="fade" onRequestClose={() => setDeleteSubjectTarget(null)}>
        <View style={styles.modalOverlay}>
          <View style={styles.deleteModalContent}>
            <Text style={styles.deleteModalTitle}>⚠️ Delete Subject</Text>

            {deleteSubjectTarget && (
              <View style={styles.deleteWarningBox}>
                <Text style={styles.deleteWarningName}>{deleteSubjectTarget.subjectName}</Text>
                <Text style={styles.deleteWarningDesc}>Deleting this subject will permanently remove:</Text>
                <View style={styles.deleteConsequenceList}>
                  <Text style={styles.deleteConsequenceItem}>
                    • All {assessmentCounts[deleteSubjectTarget.id] ?? 0} assessments in this subject
                  </Text>
                  <Text style={styles.deleteConsequenceItem}>• All scanned answer keys</Text>
                  <Text style={styles.deleteConsequenceItem}>• All student answer sheets and scores</Text>
                  <Text style={styles.deleteConsequenceItem}>• All student enrollments</Text>
                </View>
                <Text style={styles.deleteWarningNote}>This action cannot be undone.</Text>
              </View>
            )}

            <View style={styles.deleteModalButtons}>
              <TouchableOpacity style={styles.deleteCancelBtn} onPress={() => setDeleteSubjectTarget(null)} disabled={actionLoading}>
                <Text style={styles.deleteCancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.deleteConfirmBtn} onPress={confirmDeleteSubject} disabled={actionLoading}>
                {actionLoading
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.deleteConfirmBtnText}>Delete</Text>
                }
              </TouchableOpacity>
            </View>
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
    backgroundColor: 'rgba(0,0,0,0.3)', justifyContent: 'center', alignItems: 'center',
  },
  sectionInfoHeader: {
    backgroundColor: '#171443', paddingHorizontal: 24, paddingVertical: 20,
    borderBottomWidth: 1, borderBottomColor: '#2a2060',
  },
  sectionInfoTitle: { fontSize: 24, fontWeight: 'bold', color: '#ffffff', marginBottom: 4 },
  sectionInfoSubtitle: { fontSize: 14, color: '#cdd5df' },
  manageSections: { paddingHorizontal: 24, paddingTop: 24, paddingBottom: 24 },
  subjectHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  subjectTitle: { fontSize: 22, fontWeight: 'bold', color: '#1e293b' },
  createButton: { backgroundColor: '#22c55e', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  createButtonText: { color: '#ffffff', fontWeight: '600', fontSize: 14 },
  emptyState: { alignItems: 'center', justifyContent: 'center', paddingVertical: 40 },
  emptyStateIcon: { fontSize: 48, marginBottom: 16 },
  emptyStateText: { fontSize: 18, color: '#64748b', fontWeight: '600', marginBottom: 8 },
  emptyStateSubtext: { fontSize: 14, color: '#94a3b8' },

  subjectCard: {
    backgroundColor: '#ffffff', borderRadius: 12, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2, overflow: 'hidden',
  },
  subjectCardContent: { padding: 20 },
  subjectCardContentRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  subjectCardInfo: { flex: 1 },
  detailIconButton: { padding: 8, marginLeft: 8 },
  detailIconText: { fontSize: 20 },
  subjectCardTitle: { fontSize: 18, fontWeight: '600', color: '#1e293b', marginBottom: 4 },
  subjectCardDetails: { fontSize: 14, color: '#64748b' },

  // Icon-only action row
  cardActions: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: '#f1f5f9', justifyContent: 'flex-end' },
  iconActionBtn: { paddingVertical: 10, paddingHorizontal: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: '#eff6ff' },
  iconActionBtnDanger: { paddingVertical: 10, paddingHorizontal: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fef2f2' },
  iconActionText: { fontSize: 18 },
  iconActionDivider: { width: 1, backgroundColor: '#f1f5f9' },

  // Modal shared
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: {
    backgroundColor: '#ffffff', borderRadius: 20, width: '100%', maxWidth: 500, maxHeight: '80%',
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 10, elevation: 10,
  },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: 20, paddingBottom: 15,
    borderBottomWidth: 1, borderBottomColor: '#e2e8f0',
  },
  modalTitle: { fontSize: 22, fontWeight: 'bold', color: '#1e293b' },
  iconButton: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6, backgroundColor: '#f1f5f9' },
  iconButtonText: { fontSize: 14, color: '#475569', fontWeight: '600' },
  modalBody: { padding: 20 },
  modalField: { marginBottom: 20 },
  modalLabel: { fontSize: 14, fontWeight: '600', color: '#475569', marginBottom: 8 },
  modalValue: { fontSize: 16, color: '#1e293b', paddingVertical: 12, paddingHorizontal: 16, backgroundColor: '#f8fafc', borderRadius: 8 },
  monoValue: { fontFamily: 'monospace', fontSize: 12 },
  uidContainer: { flexDirection: 'column', gap: 8 },
  copyButton: { backgroundColor: '#22c55e', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 6, alignItems: 'center' },
  copyButtonText: { color: '#ffffff', fontWeight: '600', fontSize: 14 },
  modalInput: {
    fontSize: 16, color: '#1e293b', paddingVertical: 12, paddingHorizontal: 16,
    backgroundColor: '#ffffff', borderRadius: 8, borderWidth: 1, borderColor: '#e2e8f0',
  },
  modalButtonRow: { flexDirection: 'row', gap: 12, marginTop: 20 },
  cancelButton: { flex: 1, paddingVertical: 14, borderRadius: 10, backgroundColor: '#f1f5f9', alignItems: 'center' },
  cancelButtonText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  confirmButton: { flex: 1, borderRadius: 10, overflow: 'hidden' },
  gradientButton: { paddingVertical: 14, alignItems: 'center', justifyContent: 'center' },
  confirmButtonText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },

  // Delete modal
  deleteModalContent: {
    backgroundColor: '#fff', borderRadius: 16, padding: 24, width: '100%', maxWidth: 420,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 10, elevation: 10,
  },
  deleteModalTitle: { fontSize: 20, fontWeight: 'bold', color: '#1e293b', marginBottom: 16 },
  deleteWarningBox: { backgroundColor: '#fef2f2', borderRadius: 10, borderLeftWidth: 4, borderLeftColor: '#ef4444', padding: 14, marginBottom: 16 },
  deleteWarningName: { fontSize: 16, fontWeight: '700', color: '#1e293b', marginBottom: 8 },
  deleteWarningDesc: { fontSize: 13, color: '#475569', marginBottom: 8 },
  deleteConsequenceList: { marginBottom: 10 },
  deleteConsequenceItem: { fontSize: 13, color: '#7f1d1d', lineHeight: 22 },
  deleteWarningNote: { fontSize: 12, color: '#dc2626', fontWeight: '700', marginTop: 4 },
  deleteModalButtons: { flexDirection: 'row', gap: 12 },
  deleteCancelBtn: { flex: 1, paddingVertical: 13, borderRadius: 8, backgroundColor: '#f1f5f9', alignItems: 'center' },
  deleteCancelBtnText: { fontSize: 15, fontWeight: '600', color: '#475569' },
  deleteConfirmBtn: { flex: 1, paddingVertical: 13, borderRadius: 8, backgroundColor: '#ef4444', alignItems: 'center' },
  deleteConfirmBtnText: { fontSize: 15, fontWeight: '600', color: '#fff' },
});

export default SectionDashboardScreen;