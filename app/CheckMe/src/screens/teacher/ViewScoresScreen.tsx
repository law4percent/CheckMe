// src/screens/teacher/ViewScoresScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator,
  RefreshControl, TouchableOpacity, Alert, TextInput, Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, AnswerSheetResult } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import {
  getAnswerSheets,
  updateAnswerSheetScore,
  reassignAnswerSheet,
  reassignAnswerKey,
  validateStudentId,
  StudentIdValidation,
} from '../../services/answerSheetService';

type Props = NativeStackScreenProps<RootStackParamList, 'ViewScores'>;

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

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

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

const ViewScoresScreen: React.FC<Props> = ({ route, navigation }) => {
  const { assessmentUid, assessmentName, teacherUid, subjectUid } = route.params;
  const { user } = useAuth();
  const effectiveTeacherUid = teacherUid ?? user?.uid ?? '';

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [results, setResults] = useState<AnswerSheetResult[]>([]);

  // ── Edit Sheet Modal ───────────────────────
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingResult, setEditingResult] = useState<AnswerSheetResult | null>(null);
  const [editScore, setEditScore] = useState('');
  const [editStudentId, setEditStudentId] = useState('');
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [idValidation, setIdValidation] = useState<StudentIdValidation | null>(null);
  const [idValidated, setIdValidated] = useState(false);

  // ── Edit Assessment UID Modal ──────────────
  const [uidModalVisible, setUidModalVisible] = useState(false);
  const [newAssessmentUid, setNewAssessmentUid] = useState('');
  const [savingUid, setSavingUid] = useState(false);

  // ─────────────────────────────────────────────
  // Data loading
  // ─────────────────────────────────────────────

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

  // ─────────────────────────────────────────────
  // Statistics
  // ─────────────────────────────────────────────

  const scored  = results.filter(r => r.is_final_score);
  const pending = results.filter(r => !r.is_final_score);
  const avgPct  = scored.length > 0
    ? scored.reduce((s, r) => s + pct(r), 0) / scored.length : 0;
  const highPct = scored.length > 0 ? Math.max(...scored.map(pct)) : 0;
  const hasUnmatched = results.some(r => !r.matchedStudentName);

  // ─────────────────────────────────────────────
  // Edit Sheet Modal handlers
  // ─────────────────────────────────────────────

  const openEdit = (r: AnswerSheetResult) => {
    setEditingResult(r);
    setEditScore(String(r.total_score));
    setEditStudentId(r.studentId);
    setIdValidation(null);
    setIdValidated(false);
    setEditModalVisible(true);
  };

  const closeEdit = () => {
    setEditModalVisible(false);
    setEditingResult(null);
    setEditScore('');
    setEditStudentId('');
    setIdValidation(null);
    setIdValidated(false);
  };

  const handleValidateStudentId = async () => {
    if (!editingResult) return;
    const trimmed = editStudentId.trim();

    if (trimmed === editingResult.studentId) {
      setIdValidation(null);
      setIdValidated(false);
      return;
    }
    if (!trimmed) {
      Alert.alert('Invalid', 'Student ID cannot be empty');
      return;
    }

    try {
      setValidating(true);
      const validation = await validateStudentId(trimmed, effectiveTeacherUid, subjectUid);
      setIdValidation(validation);
      setIdValidated(true);
    } catch {
      setIdValidation(null);
      setIdValidated(false);
    } finally {
      setValidating(false);
    }
  };

  const handleSaveSheet = async () => {
    if (!editingResult) return;

    const newScore      = parseInt(editScore, 10);
    const newStudentId  = editStudentId.trim();
    const idChanged     = newStudentId !== editingResult.studentId;

    if (isNaN(newScore) || newScore < 0) {
      Alert.alert('Invalid', 'Please enter a valid score (≥ 0)');
      return;
    }
    if (newScore > editingResult.total_questions) {
      Alert.alert('Invalid', `Score cannot exceed ${editingResult.total_questions}`);
      return;
    }

    // Must validate before saving a changed ID
    if (idChanged && !idValidated) {
      Alert.alert('Validate First', 'Tap "Validate" before saving a new Student ID.');
      return;
    }

    // Block if ID doesn't exist in the app
    if (idChanged && idValidation && !idValidation.exists) {
      Alert.alert(
        'Student Not Found',
        `"${newStudentId}" is not registered in the app.\n\nVerify the correct ID before reassigning.`
      );
      return;
    }

    // Build confirmation message
    let confirmTitle = idChanged ? '⚠️ Reassign Answer Sheet' : 'Update Score';
    let confirmMsg = '';

    if (idChanged) {
      confirmMsg =
        `Move answer sheet from "${editingResult.studentId}" → "${newStudentId}"`;
      if (idValidation?.studentName) confirmMsg += ` (${idValidation.studentName})`;
      if (idValidation && !idValidation.enrolled) {
        confirmMsg += `\n\n⚠️ This student is not enrolled in this subject.`;
      }
      confirmMsg += `\n\nThe old record will be permanently deleted.`;
      if (newScore !== editingResult.total_score) {
        confirmMsg += `\nScore will also be updated to ${newScore}/${editingResult.total_questions}.`;
      }
    } else {
      confirmMsg = `Update score to ${newScore} / ${editingResult.total_questions}?`;
    }

    Alert.alert(confirmTitle, confirmMsg, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: idChanged ? 'Reassign' : 'Save',
        style: idChanged ? 'destructive' : 'default',
        onPress: async () => {
          try {
            setSaving(true);
            if (idChanged) {
              await reassignAnswerSheet(
                effectiveTeacherUid, assessmentUid,
                editingResult.studentId, newStudentId
              );
              if (newScore !== editingResult.total_score) {
                await updateAnswerSheetScore(
                  effectiveTeacherUid, assessmentUid, newStudentId, newScore
                );
              }
              await loadResults();
            } else {
              await updateAnswerSheetScore(
                effectiveTeacherUid, assessmentUid, editingResult.studentId, newScore
              );
              setResults(prev =>
                prev
                  .map(r => r.studentId === editingResult.studentId
                    ? { ...r, total_score: newScore, updated_at: Date.now() }
                    : r)
                  .sort((a, b) => pct(b) - pct(a))
              );
            }
            closeEdit();
            Alert.alert('Saved', idChanged
              ? 'Answer sheet reassigned successfully.'
              : 'Score updated successfully.'
            );
          } catch (error: any) {
            Alert.alert('Error', error.message || 'Failed to save changes');
          } finally {
            setSaving(false);
          }
        },
      },
    ]);
  };

  // ─────────────────────────────────────────────
  // Edit Assessment UID Modal handlers
  // ─────────────────────────────────────────────

  const openUidModal = () => {
    setNewAssessmentUid('');
    setUidModalVisible(true);
  };

  const handleSaveAssessmentUid = async () => {
    const trimmed = newAssessmentUid.trim().toUpperCase();
    if (!trimmed) {
      Alert.alert('Invalid', 'Assessment UID cannot be empty');
      return;
    }
    if (trimmed === assessmentUid) {
      Alert.alert('No Change', 'The new UID is the same as the current one.');
      return;
    }

    Alert.alert(
      '⚠️ Rename Answer Key',
      `Move answer key: "${assessmentUid}" → "${trimmed}"\n\n` +
      `Answer sheets under "${assessmentUid}" will NOT be moved.\n\n` +
      `After renaming:\n` +
      `• Re-scan student sheets under the new UID "${trimmed}", OR\n` +
      `• Use ✏️ Edit on each row to reassign existing sheets manually\n\n` +
      `The old answer key will be permanently deleted.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Rename',
          style: 'destructive',
          onPress: async () => {
            try {
              setSavingUid(true);
              await reassignAnswerKey(effectiveTeacherUid, assessmentUid, trimmed);
              setUidModalVisible(false);
              Alert.alert(
                'Answer Key Renamed',
                `Answer key moved to "${trimmed}".\n\n` +
                `Existing answer sheets are still under "${assessmentUid}". ` +
                `Re-scan or reassign them as needed.`,
                [{ text: 'OK', onPress: () => navigation.goBack() }]
              );
            } catch (error: any) {
              Alert.alert('Error', error.message || 'Failed to rename answer key');
            } finally {
              setSavingUid(false);
            }
          },
        },
      ]
    );
  };

  // ─────────────────────────────────────────────
  // Validation badge
  // ─────────────────────────────────────────────

  const renderValidationBadge = () => {
    if (!editingResult) return null;
    if (editStudentId.trim() === editingResult.studentId) return null;

    if (validating) {
      return (
        <View style={styles.validationRow}>
          <ActivityIndicator size="small" color="#6366f1" />
          <Text style={styles.validatingText}>  Validating...</Text>
        </View>
      );
    }
    if (!idValidated || !idValidation) return null;

    if (!idValidation.exists) {
      return (
        <View style={[styles.validationRow, styles.validationError]}>
          <Text style={styles.validationErrorText}>
            ❌ Student ID not registered in the app
          </Text>
        </View>
      );
    }

    if (idValidation.enrolled) {
      return (
        <View style={[styles.validationRow, styles.validationOk]}>
          <Text style={styles.validationOkText}>
            ✅ {idValidation.studentName} — Enrolled
          </Text>
        </View>
      );
    }

    return (
      <View style={[styles.validationRow, styles.validationWarn]}>
        <Text style={styles.validationWarnText}>
          ⚠️ {idValidation.studentName} — Not enrolled in this subject
        </Text>
      </View>
    );
  };

  // ─────────────────────────────────────────────
  // Loading screen
  // ─────────────────────────────────────────────

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

  // ─────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* ── Header ── */}
        <View style={styles.header}>
          <View style={styles.headerTopRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.headerTitle}>{assessmentName ?? 'Assessment Results'}</Text>
              <Text style={styles.headerUid}>UID: {assessmentUid}</Text>
            </View>
            <TouchableOpacity style={styles.editUidButton} onPress={openUidModal}>
              <Text style={styles.editUidButtonText}>✏️ Edit UID</Text>
            </TouchableOpacity>
          </View>

          {/* Stats */}
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

          {hasUnmatched && (
            <View style={styles.warningBanner}>
              <Text style={styles.warningBannerText}>
                ⚠️ Some student IDs could not be matched to enrolled students.
                Use ✏️ Edit on a row to reassign a sheet to the correct student ID.
              </Text>
            </View>
          )}
        </View>

        {/* ── Results list ── */}
        <View style={styles.listSection}>
          {results.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>📋</Text>
              <Text style={styles.emptyTitle}>No submissions yet</Text>
              <Text style={styles.emptySubtitle}>
                Scores will appear here once the Raspberry Pi scans answer sheets.
              </Text>
            </View>
          ) : (
            results.map((r, index) => {
              const percentage = pct(r);
              const color = scoreColor(percentage);
              const name = r.matchedStudentName ?? 'Unknown Student';

              return (
                <View key={r.studentId} style={styles.resultCard}>
                  <View style={styles.cardHeader}>
                    <View style={styles.rankBadge}>
                      <Text style={styles.rankText}>#{index + 1}</Text>
                    </View>
                    <View style={styles.studentInfo}>
                      <View style={styles.nameRow}>
                        <Text style={styles.studentName}>{name}</Text>
                        {!r.matchedStudentName && (
                          <View style={styles.unmatchedBadge}>
                            <Text style={styles.unmatchedText}>⚠️</Text>
                          </View>
                        )}
                      </View>
                      <Text style={styles.schoolId}>ID: {r.studentId}</Text>
                      <Text style={styles.checkedAt}>
                        Scanned: {formatCheckedAt(r.checked_at)}
                      </Text>
                    </View>
                    <View style={styles.scoreDisplay}>
                      {r.is_final_score ? (
                        <>
                          <Text style={[styles.scorePct, { color }]}>{percentage}%</Text>
                          <Text style={[styles.scoreGrade, { color }]}>{gradeLabel(percentage)}</Text>
                        </>
                      ) : (
                        <View style={styles.pendingBadge}>
                          <Text style={styles.pendingText}>⏳ Pending</Text>
                        </View>
                      )}
                    </View>
                  </View>

                  <Text style={styles.scoreFraction}>
                    {r.total_score} / {r.total_questions} correct
                  </Text>

                  {r.is_final_score && (
                    <View style={styles.progressBg}>
                      <View style={[styles.progressFill, { width: `${percentage}%` as any, backgroundColor: color }]} />
                    </View>
                  )}

                  <View style={styles.cardActions}>
                    <TouchableOpacity
                      style={styles.breakdownButton}
                      onPress={() => navigation.navigate('TeacherAssessmentScoreTable', {
                        result: r, assessmentName: assessmentName ?? assessmentUid,
                      })}
                    >
                      <Text style={styles.breakdownButtonText}>📊 Breakdown</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.editRowButton} onPress={() => openEdit(r)}>
                      <Text style={styles.editRowButtonText}>✏️ Edit</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })
          )}
        </View>
      </ScrollView>

      {/* ── Edit Sheet Modal ───────────────────────── */}
      <Modal visible={editModalVisible} transparent animationType="slide" onRequestClose={closeEdit}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Answer Sheet</Text>

            {editingResult && (
              <View style={styles.infoBox}>
                <Text style={styles.infoName}>{editingResult.matchedStudentName ?? 'Unknown Student'}</Text>
                <Text style={styles.infoSub}>
                  Current ID: {editingResult.studentId}
                  {'  '}·{'  '}
                  Score: {editingResult.total_score}/{editingResult.total_questions}
                </Text>
              </View>
            )}

            {/* Student ID row */}
            <Text style={styles.fieldLabel}>Student ID</Text>
            <View style={styles.inputRow}>
              <TextInput
                style={[styles.textInput, { flex: 1 }]}
                value={editStudentId}
                onChangeText={t => {
                  setEditStudentId(t);
                  setIdValidated(false);
                  setIdValidation(null);
                }}
                placeholder="School-provided ID"
                keyboardType="numeric"
                editable={!saving}
              />
              <TouchableOpacity
                style={[styles.validateBtn, validating && { opacity: 0.6 }]}
                onPress={handleValidateStudentId}
                disabled={validating || saving}
              >
                {validating
                  ? <ActivityIndicator size="small" color="#fff" />
                  : <Text style={styles.validateBtnText}>Validate</Text>
                }
              </TouchableOpacity>
            </View>

            {renderValidationBadge()}

            {/* Score row */}
            <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Score</Text>
            <TextInput
              style={styles.textInput}
              value={editScore}
              onChangeText={setEditScore}
              keyboardType="numeric"
              placeholder="Enter score"
              editable={!saving}
            />

            {editScore !== '' && editingResult && !isNaN(parseInt(editScore)) && (
              <View style={styles.previewRow}>
                <Text style={styles.previewText}>
                  Preview: {editScore} / {editingResult.total_questions} ={' '}
                  {Math.round((parseInt(editScore) / editingResult.total_questions) * 100)}%
                </Text>
              </View>
            )}

            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.cancelBtn} onPress={closeEdit} disabled={saving}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.saveBtn} onPress={handleSaveSheet} disabled={saving}>
                {saving
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.saveBtnText}>Save</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Edit Assessment UID Modal ──────────────── */}
      <Modal visible={uidModalVisible} transparent animationType="slide" onRequestClose={() => setUidModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Assessment UID</Text>

            <View style={styles.infoBox}>
              <Text style={styles.fieldLabel}>Current UID</Text>
              <Text style={styles.uidDisplay}>{assessmentUid}</Text>
            </View>

            <View style={styles.warningBox}>
              <Text style={styles.warningBoxTitle}>⚠️ What happens when you rename</Text>
              <Text style={styles.warningBoxBody}>
                Only the answer key is moved. Answer sheets already saved under{' '}
                <Text style={{ fontWeight: '700' }}>"{assessmentUid}"</Text> will stay there.{'\n\n'}
                After renaming you should:{'\n'}
                {'  '}• Re-scan student sheets under the new UID, OR{'\n'}
                {'  '}• Use ✏️ Edit on each row to manually reassign existing sheets
              </Text>
            </View>

            <Text style={styles.fieldLabel}>New Assessment UID</Text>
            <TextInput
              style={[styles.textInput, styles.uidInput]}
              value={newAssessmentUid}
              onChangeText={t => setNewAssessmentUid(t.toUpperCase())}
              placeholder="e.g. AB3K9P2Q"
              autoCapitalize="characters"
              maxLength={8}
              editable={!savingUid}
            />

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setUidModalVisible(false)}
                disabled={savingUid}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.saveBtn, { backgroundColor: '#ef4444' }]}
                onPress={handleSaveAssessmentUid}
                disabled={savingUid}
              >
                {savingUid
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.saveBtnText}>Rename</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

// ─────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollView: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 16, color: '#64748b' },

  // Header
  header: {
    backgroundColor: '#171443', paddingHorizontal: 24,
    paddingVertical: 24, borderBottomWidth: 1, borderBottomColor: '#2a2060',
  },
  headerTopRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 16 },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#ffffff', marginBottom: 4 },
  headerUid: { fontSize: 12, color: '#94a3b8', fontFamily: 'monospace' },
  editUidButton: {
    backgroundColor: '#374151', paddingHorizontal: 12,
    paddingVertical: 8, borderRadius: 8, marginLeft: 12,
  },
  editUidButtonText: { fontSize: 13, color: '#e5e7eb', fontWeight: '600' },
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
  warningBannerText: { fontSize: 12, color: '#92400e', lineHeight: 18 },

  // List
  listSection: { padding: 16 },
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 64, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#64748b', marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: '#94a3b8', textAlign: 'center', paddingHorizontal: 32 },

  // Result card
  resultCard: {
    backgroundColor: '#ffffff', borderRadius: 14, padding: 16, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08, shadowRadius: 6, elevation: 3,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10 },
  rankBadge: {
    width: 36, height: 36, borderRadius: 18, backgroundColor: '#f1f5f9',
    justifyContent: 'center', alignItems: 'center', marginRight: 10, marginTop: 2,
  },
  rankText: { fontSize: 12, fontWeight: 'bold', color: '#475569' },
  studentInfo: { flex: 1 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 2 },
  studentName: { fontSize: 16, fontWeight: 'bold', color: '#1e293b' },
  unmatchedBadge: {
    backgroundColor: '#fef3c7', paddingHorizontal: 5,
    paddingVertical: 1, borderRadius: 4,
  },
  unmatchedText: { fontSize: 12 },
  schoolId: { fontSize: 13, color: '#64748b', fontFamily: 'monospace', marginBottom: 2 },
  checkedAt: { fontSize: 11, color: '#94a3b8' },
  scoreDisplay: { alignItems: 'flex-end', minWidth: 64 },
  scorePct: { fontSize: 28, fontWeight: 'bold' },
  scoreGrade: { fontSize: 14, fontWeight: '600' },
  pendingBadge: {
    backgroundColor: '#fef3c7', paddingHorizontal: 8,
    paddingVertical: 4, borderRadius: 6,
  },
  pendingText: { fontSize: 12, color: '#d97706', fontWeight: '700' },
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
  editRowButton: {
    backgroundColor: '#f1f5f9', paddingVertical: 10,
    paddingHorizontal: 18, borderRadius: 8, alignItems: 'center',
  },
  editRowButtonText: { fontSize: 14, fontWeight: '600', color: '#475569' },

  // Modal shared
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center', alignItems: 'center', padding: 24,
  },
  modalContent: {
    backgroundColor: '#ffffff', borderRadius: 16,
    padding: 24, width: '100%', maxWidth: 420,
  },
  modalTitle: {
    fontSize: 20, fontWeight: 'bold', color: '#1e293b',
    marginBottom: 16, textAlign: 'center',
  },
  infoBox: {
    backgroundColor: '#f8fafc', borderRadius: 10,
    padding: 14, marginBottom: 16,
  },
  infoName: { fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 2 },
  infoSub: { fontSize: 13, color: '#64748b' },
  fieldLabel: { fontSize: 14, fontWeight: '600', color: '#475569', marginBottom: 8 },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  textInput: {
    borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8,
    paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 16, color: '#1e293b', marginBottom: 12,
  },
  validateBtn: {
    backgroundColor: '#6366f1', paddingVertical: 14,
    paddingHorizontal: 14, borderRadius: 8,
  },
  validateBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },

  // Validation badges
  validationRow: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 12, paddingVertical: 8,
    borderRadius: 8, marginBottom: 8,
  },
  validatingText: { fontSize: 13, color: '#6366f1' },
  validationOk: { backgroundColor: '#f0fdf4' },
  validationOkText: { fontSize: 13, color: '#16a34a', fontWeight: '600' },
  validationWarn: { backgroundColor: '#fefce8' },
  validationWarnText: { fontSize: 13, color: '#ca8a04', fontWeight: '600' },
  validationError: { backgroundColor: '#fef2f2' },
  validationErrorText: { fontSize: 13, color: '#dc2626', fontWeight: '600' },

  previewRow: {
    backgroundColor: '#f0fdf4', borderRadius: 8,
    padding: 12, marginBottom: 16, alignItems: 'center',
  },
  previewText: { fontSize: 15, color: '#16a34a', fontWeight: '700' },
  modalButtons: { flexDirection: 'row', gap: 12, marginTop: 4 },
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

  // UID modal extras
  uidDisplay: {
    fontSize: 22, fontWeight: 'bold', color: '#6366f1',
    fontFamily: 'monospace', marginTop: 2,
  },
  warningBox: {
    backgroundColor: '#fff7ed', borderRadius: 10,
    borderLeftWidth: 4, borderLeftColor: '#f59e0b',
    padding: 14, marginBottom: 16,
  },
  warningBoxTitle: { fontSize: 14, fontWeight: '700', color: '#92400e', marginBottom: 6 },
  warningBoxBody: { fontSize: 13, color: '#78350f', lineHeight: 20 },
  uidInput: {
    fontSize: 20, fontFamily: 'monospace',
    fontWeight: 'bold', textAlign: 'center', letterSpacing: 4,
  },
});

export default ViewScoresScreen;