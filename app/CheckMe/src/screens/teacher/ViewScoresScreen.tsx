// src/screens/teacher/ViewScoresScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
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
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, AnswerSheetResult } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { getAnswerSheets, updateAnswerSheetScore } from '../../services/answerSheetService';

type Props = NativeStackScreenProps<RootStackParamList, 'ViewScores'>;

const ViewScoresScreen: React.FC<Props> = ({ route, navigation }) => {
  const { assessmentUid, assessmentName, teacherUid, subjectUid } = route.params;
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [results, setResults] = useState<AnswerSheetResult[]>([]);

  // Edit modal
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingResult, setEditingResult] = useState<AnswerSheetResult | null>(null);
  const [editScore, setEditScore] = useState('');
  const [saving, setSaving] = useState(false);

  const effectiveTeacherUid = teacherUid ?? user?.uid ?? '';

  const loadResults = useCallback(async () => {
    if (!effectiveTeacherUid || !assessmentUid) return;
    try {
      const data = await getAnswerSheets(effectiveTeacherUid, assessmentUid, subjectUid);
      setResults(data);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to load results');
    }
  }, [effectiveTeacherUid, assessmentUid, subjectUid]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await loadResults();
      setLoading(false);
    })();
  }, [loadResults]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadResults();
    setRefreshing(false);
  };

  // ── Helpers ───────────────────────────────────
  const pct = (r: AnswerSheetResult) =>
    r.total_questions > 0 ? Math.round((r.total_score / r.total_questions) * 100) : 0;

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

  const scoreColor = (p: number) => {
    if (p >= 90) return '#22c55e';
    if (p >= 75) return '#3b82f6';
    if (p >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const formatCheckedAt = (ts: number) => {
    if (!ts) return '—';
    return new Date(ts).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  /**
   * Display name priority:
   * 1. matchedStudentName (once school ID field added to enrollments)
   * 2. "Unknown Student"
   * Subtitle always shows school ID from paper.
   */
  const displayName = (r: AnswerSheetResult) =>
    r.matchedStudentName ?? 'Unknown Student';

  // ── Statistics ────────────────────────────────
  const scored = results.filter(r => r.is_final_score);
  const pending = results.filter(r => !r.is_final_score);
  const avgPct =
    scored.length > 0
      ? scored.reduce((s, r) => s + pct(r), 0) / scored.length
      : 0;
  const highPct = scored.length > 0 ? Math.max(...scored.map(pct)) : 0;

  // ── Edit modal ────────────────────────────────
  const openEdit = (r: AnswerSheetResult) => {
    setEditingResult(r);
    setEditScore(String(r.total_score));
    setEditModalVisible(true);
  };

  const closeEdit = () => {
    setEditModalVisible(false);
    setEditingResult(null);
    setEditScore('');
  };

  const handleSaveScore = async () => {
    if (!editingResult) return;

    const newScore = parseInt(editScore, 10);
    if (isNaN(newScore) || newScore < 0) {
      Alert.alert('Invalid', 'Please enter a valid score (≥ 0)');
      return;
    }
    if (newScore > editingResult.total_questions) {
      Alert.alert('Invalid', `Score cannot exceed total questions (${editingResult.total_questions})`);
      return;
    }

    try {
      setSaving(true);
      await updateAnswerSheetScore(
        effectiveTeacherUid,
        assessmentUid,
        editingResult.studentId,
        newScore
      );
      setResults(prev =>
        prev
          .map(r =>
            r.studentId === editingResult.studentId
              ? { ...r, total_score: newScore, updated_at: Date.now() }
              : r
          )
          .sort((a, b) => pct(b) - pct(a))
      );
      closeEdit();
      Alert.alert('Saved', 'Score updated successfully');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to save score');
    } finally {
      setSaving(false);
    }
  };

  // ── Navigate to breakdown ─────────────────────
  const handleViewBreakdown = (r: AnswerSheetResult) => {
    navigation.navigate('TeacherAssessmentScoreTable', {
      result: r,
      assessmentName: assessmentName ?? assessmentUid,
    });
  };

  // ── Loading ───────────────────────────────────
  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#22c55e" />
          <Text style={styles.loadingText}>Loading results...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // ── Render ────────────────────────────────────
  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>
            {assessmentName ?? 'Assessment Results'}
          </Text>
          <Text style={styles.headerUid}>UID: {assessmentUid}</Text>

          {/* Stats row */}
          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statNum}>{results.length}</Text>
              <Text style={styles.statLbl}>Scanned</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statNum}>{pending.length}</Text>
              <Text style={styles.statLbl}>Pending</Text>
            </View>
            {scored.length > 0 && (
              <>
                <View style={styles.statBox}>
                  <Text style={styles.statNum}>{avgPct.toFixed(1)}%</Text>
                  <Text style={styles.statLbl}>Average</Text>
                </View>
                <View style={styles.statBox}>
                  <Text style={styles.statNum}>{highPct}%</Text>
                  <Text style={styles.statLbl}>Highest</Text>
                </View>
              </>
            )}
          </View>

          {/* Unmatched warning */}
          {results.some(r => !r.matchedStudentName) && (
            <View style={styles.warningBanner}>
              <Text style={styles.warningText}>
                ⚠️ Some student IDs could not be matched to enrolled students.
                School ID field will be available in a future update.
              </Text>
            </View>
          )}
        </View>

        {/* Results list */}
        <View style={styles.listSection}>
          {results.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>📋</Text>
              <Text style={styles.emptyTitle}>No submissions yet</Text>
              <Text style={styles.emptySubtitle}>
                Scores will appear here once the Raspberry Pi scans answer sheets
              </Text>
            </View>
          ) : (
            results.map((r, index) => {
              const percentage = pct(r);
              const color = scoreColor(percentage);

              return (
                <View key={r.studentId} style={styles.resultCard}>
                  {/* Card header row */}
                  <View style={styles.cardHeader}>
                    {/* Rank */}
                    <View style={styles.rankBadge}>
                      <Text style={styles.rankText}>#{index + 1}</Text>
                    </View>

                    {/* Student info */}
                    <View style={styles.studentInfo}>
                      <Text style={styles.studentName}>{displayName(r)}</Text>
                      <Text style={styles.schoolId}>ID: {r.studentId}</Text>
                      {!r.matchedStudentName && (
                        <View style={styles.unmatchedBadge}>
                          <Text style={styles.unmatchedText}>⚠️ Unmatched ID</Text>
                        </View>
                      )}
                      <Text style={styles.checkedAt}>
                        Scanned: {formatCheckedAt(r.checked_at)}
                      </Text>
                    </View>

                    {/* Score display */}
                    <View style={styles.scoreDisplay}>
                      {r.is_final_score ? (
                        <>
                          <Text style={[styles.scorePct, { color }]}>{percentage}%</Text>
                          <Text style={[styles.scoreGrade, { color }]}>{gradeLabel(percentage)}</Text>
                        </>
                      ) : (
                        <View style={styles.pendingBadge}>
                          <Text style={styles.pendingText}>Pending</Text>
                        </View>
                      )}
                    </View>
                  </View>

                  {/* Score fraction */}
                  <Text style={styles.scoreFraction}>
                    {r.total_score} / {r.total_questions} correct
                  </Text>

                  {/* Progress bar */}
                  {r.is_final_score && (
                    <View style={styles.progressBg}>
                      <View style={[styles.progressFill, { width: `${percentage}%`, backgroundColor: color }]} />
                    </View>
                  )}

                  {/* Action buttons */}
                  <View style={styles.cardActions}>
                    <TouchableOpacity
                      style={styles.breakdownButton}
                      onPress={() => handleViewBreakdown(r)}
                    >
                      <Text style={styles.breakdownButtonText}>📊 View Breakdown</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.editButton}
                      onPress={() => openEdit(r)}
                    >
                      <Text style={styles.editButtonText}>✏️ Edit</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })
          )}
        </View>
      </ScrollView>

      {/* Edit Score Modal */}
      <Modal
        visible={editModalVisible}
        transparent
        animationType="slide"
        onRequestClose={closeEdit}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Score</Text>

            {editingResult && (
              <View style={styles.modalStudentBox}>
                <Text style={styles.modalStudentName}>{displayName(editingResult)}</Text>
                <Text style={styles.modalStudentId}>ID: {editingResult.studentId}</Text>
                <Text style={styles.modalOriginal}>
                  Current: {editingResult.total_score} / {editingResult.total_questions}
                </Text>
              </View>
            )}

            <Text style={styles.inputLabel}>New Score</Text>
            <TextInput
              style={styles.input}
              value={editScore}
              onChangeText={setEditScore}
              keyboardType="numeric"
              placeholder="Enter score"
              editable={!saving}
            />

            {editScore && editingResult && (
              <View style={styles.previewBox}>
                <Text style={styles.previewLabel}>Preview: </Text>
                <Text style={styles.previewValue}>
                  {editScore} / {editingResult.total_questions} ={' '}
                  {editingResult.total_questions > 0
                    ? Math.round((parseInt(editScore) / editingResult.total_questions) * 100)
                    : 0}%
                </Text>
              </View>
            )}

            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.cancelBtn} onPress={closeEdit} disabled={saving}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.saveBtn} onPress={handleSaveScore} disabled={saving}>
                {saving
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.saveBtnText}>Save</Text>
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
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 16, color: '#64748b' },

  // Header
  header: {
    backgroundColor: '#171443',
    paddingHorizontal: 24,
    paddingVertical: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060',
  },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#ffffff', marginBottom: 4 },
  headerUid: { fontSize: 12, color: '#94a3b8', fontFamily: 'monospace', marginBottom: 16 },
  statsRow: { flexDirection: 'row', gap: 10 },
  statBox: {
    flex: 1, backgroundColor: '#2a2060', borderRadius: 10,
    paddingVertical: 12, alignItems: 'center',
  },
  statNum: { fontSize: 20, fontWeight: 'bold', color: '#22c55e', marginBottom: 2 },
  statLbl: { fontSize: 11, color: '#cdd5df' },
  warningBanner: {
    marginTop: 12, backgroundColor: '#fef3c7',
    borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8,
  },
  warningText: { fontSize: 12, color: '#92400e', lineHeight: 18 },

  // List
  listSection: { padding: 16 },
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 64, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#64748b', marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: '#94a3b8', textAlign: 'center', paddingHorizontal: 32 },

  // Result card
  resultCard: {
    backgroundColor: '#ffffff', borderRadius: 14, padding: 16,
    marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08, shadowRadius: 6, elevation: 3,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10 },
  rankBadge: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: '#f1f5f9', justifyContent: 'center',
    alignItems: 'center', marginRight: 10, marginTop: 2,
  },
  rankText: { fontSize: 12, fontWeight: 'bold', color: '#475569' },
  studentInfo: { flex: 1 },
  studentName: { fontSize: 16, fontWeight: 'bold', color: '#1e293b', marginBottom: 2 },
  schoolId: { fontSize: 13, color: '#64748b', fontFamily: 'monospace', marginBottom: 4 },
  unmatchedBadge: {
    alignSelf: 'flex-start', backgroundColor: '#fef3c7',
    paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, marginBottom: 4,
  },
  unmatchedText: { fontSize: 11, color: '#d97706', fontWeight: '600' },
  checkedAt: { fontSize: 11, color: '#94a3b8' },
  scoreDisplay: { alignItems: 'flex-end', minWidth: 60 },
  scorePct: { fontSize: 28, fontWeight: 'bold' },
  scoreGrade: { fontSize: 14, fontWeight: '600' },
  pendingBadge: {
    backgroundColor: '#fef3c7', paddingHorizontal: 10,
    paddingVertical: 4, borderRadius: 6,
  },
  pendingText: { fontSize: 13, color: '#d97706', fontWeight: '700' },
  scoreFraction: { fontSize: 13, color: '#64748b', marginBottom: 8 },
  progressBg: {
    height: 8, backgroundColor: '#f1f5f9',
    borderRadius: 4, overflow: 'hidden', marginBottom: 12,
  },
  progressFill: { height: '100%', borderRadius: 4 },
  cardActions: { flexDirection: 'row', gap: 8 },
  breakdownButton: {
    flex: 1, backgroundColor: '#dbeafe',
    paddingVertical: 10, borderRadius: 8, alignItems: 'center',
  },
  breakdownButtonText: { fontSize: 14, fontWeight: '600', color: '#2563eb' },
  editButton: {
    backgroundColor: '#f1f5f9',
    paddingVertical: 10, paddingHorizontal: 16,
    borderRadius: 8, alignItems: 'center',
  },
  editButtonText: { fontSize: 14, fontWeight: '600', color: '#475569' },

  // Modal
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center', alignItems: 'center', padding: 24,
  },
  modalContent: {
    backgroundColor: '#ffffff', borderRadius: 16,
    padding: 24, width: '100%', maxWidth: 400,
  },
  modalTitle: { fontSize: 20, fontWeight: 'bold', color: '#1e293b', marginBottom: 16, textAlign: 'center' },
  modalStudentBox: {
    backgroundColor: '#f8fafc', borderRadius: 10,
    padding: 14, marginBottom: 16,
  },
  modalStudentName: { fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 2 },
  modalStudentId: { fontSize: 13, color: '#64748b', fontFamily: 'monospace', marginBottom: 4 },
  modalOriginal: { fontSize: 13, color: '#94a3b8' },
  inputLabel: { fontSize: 14, fontWeight: '600', color: '#475569', marginBottom: 8 },
  input: {
    borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8,
    paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 18, color: '#1e293b', marginBottom: 12,
    textAlign: 'center', fontWeight: 'bold',
  },
  previewBox: {
    flexDirection: 'row', backgroundColor: '#f0fdf4',
    borderRadius: 8, padding: 12, marginBottom: 16,
    alignItems: 'center', justifyContent: 'center',
  },
  previewLabel: { fontSize: 14, color: '#166534', fontWeight: '600' },
  previewValue: { fontSize: 16, color: '#22c55e', fontWeight: 'bold' },
  modalButtons: { flexDirection: 'row', gap: 12 },
  cancelBtn: {
    flex: 1, paddingVertical: 13, borderRadius: 8,
    backgroundColor: '#f1f5f9', alignItems: 'center',
  },
  cancelBtnText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  saveBtn: {
    flex: 1, paddingVertical: 13, borderRadius: 8,
    backgroundColor: '#22c55e', alignItems: 'center',
  },
  saveBtnText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },
});

export default ViewScoresScreen;