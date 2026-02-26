// src/screens/teacher/ViewScoresScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator,
  RefreshControl, TouchableOpacity, Alert, TextInput, Modal, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, AnswerSheetResult } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import {
  getAnswerSheets,
  reassignAnswerSheet,
  validateStudentId,
  StudentIdValidation,
  updateStudentAnswerSheet,
  StudentAnswerEdit,
} from '../../services/answerSheetService';
import { QuestionBreakdown } from '../../types';

type Props = NativeStackScreenProps<RootStackParamList, 'ViewScores'>;

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

const pct = (score: number, total: number) =>
  total > 0 ? Math.round((score / total) * 100) : 0;

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

const formatDate = (ts: number) => {
  if (!ts) return '—';
  return new Date(ts).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

// ─────────────────────────────────────────────
// Local type for edited breakdown row
// ─────────────────────────────────────────────

interface EditableRow {
  questionKey: string;
  studentAnswer: string;
  correctAnswer: string;
  checkingResult: boolean | 'pending';
  // editing state
  editedAnswer: string;
  editedResult: boolean | 'pending';
  isDirty: boolean;
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

const ViewScoresScreen: React.FC<Props> = ({ route, navigation }) => {
  const { assessmentUid, assessmentName, teacherUid, subjectUid } = route.params;
  const { user } = useAuth();
  const effectiveTeacherUid = teacherUid ?? user?.uid ?? '';

  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [results, setResults]       = useState<AnswerSheetResult[]>([]);

  // ── Reassign Student ID modal ──────────────
  const [reassignModalVisible, setReassignModalVisible] = useState(false);
  const [reassignTarget, setReassignTarget]             = useState<AnswerSheetResult | null>(null);
  const [newStudentId, setNewStudentId]                 = useState('');
  const [savingReassign, setSavingReassign]             = useState(false);
  const [validating, setValidating]                     = useState(false);
  const [idValidation, setIdValidation]                 = useState<StudentIdValidation | null>(null);
  const [idValidated, setIdValidated]                   = useState(false);

  // ── Edit Answer Sheet modal ────────────────
  const [editSheetModalVisible, setEditSheetModalVisible] = useState(false);
  const [editingResult, setEditingResult]                 = useState<AnswerSheetResult | null>(null);
  const [editableRows, setEditableRows]                   = useState<EditableRow[]>([]);
  const [markFinal, setMarkFinal]                         = useState(false);
  const [savingSheet, setSavingSheet]                     = useState(false);

  // ─────────────────────────────────────────────
  // Data
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
    (async () => { setLoading(true); await loadResults(); setLoading(false); })();
  }, [loadResults]);

  const onRefresh = async () => { setRefreshing(true); await loadResults(); setRefreshing(false); };

  // ─────────────────────────────────────────────
  // Statistics
  // ─────────────────────────────────────────────

  const scored      = results.filter(r => r.is_final_score);
  const pendingList = results.filter(r => !r.is_final_score);
  const avgPct      = scored.length > 0
    ? scored.reduce((s, r) => s + pct(r.total_score, r.total_questions), 0) / scored.length : 0;
  const highPct     = scored.length > 0
    ? Math.max(...scored.map(r => pct(r.total_score, r.total_questions))) : 0;
  const hasUnmatched = results.some(r => !r.matchedStudentName);

  // ─────────────────────────────────────────────
  // Reassign Student ID
  // ─────────────────────────────────────────────

  const openReassign = (r: AnswerSheetResult) => {
    setReassignTarget(r);
    setNewStudentId('');
    setIdValidation(null);
    setIdValidated(false);
    setReassignModalVisible(true);
  };

  const closeReassign = () => {
    setReassignModalVisible(false);
    setReassignTarget(null);
    setNewStudentId('');
    setIdValidation(null);
    setIdValidated(false);
  };

  const handleValidateId = async () => {
    const trimmed = newStudentId.trim();
    if (!trimmed) { Alert.alert('Invalid', 'Student ID cannot be empty'); return; }
    if (trimmed === reassignTarget?.studentId) { setIdValidation(null); setIdValidated(false); return; }
    try {
      setValidating(true);
      const v = await validateStudentId(trimmed, effectiveTeacherUid, subjectUid);
      setIdValidation(v);
      setIdValidated(true);
    } catch { setIdValidation(null); setIdValidated(false); }
    finally { setValidating(false); }
  };

  const handleConfirmReassign = async () => {
    if (!reassignTarget) return;
    const trimmed = newStudentId.trim();
    if (!trimmed || trimmed === reassignTarget.studentId) { closeReassign(); return; }
    if (!idValidated) { Alert.alert('Validate First', 'Tap Validate before saving.'); return; }
    if (idValidation && !idValidation.exists) {
      Alert.alert('Not Found', `"${trimmed}" is not registered in the app.`); return;
    }

    let msg = `Move answer sheet from "${reassignTarget.studentId}" → "${trimmed}"`;
    if (idValidation?.studentName) msg += ` (${idValidation.studentName})`;
    if (idValidation && !idValidation.enrolled) msg += `\n\n⚠️ This student is not enrolled in this subject.`;
    msg += `\n\nThe old record will be permanently deleted.`;

    Alert.alert('⚠️ Reassign Answer Sheet', msg, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Reassign', style: 'destructive',
        onPress: async () => {
          try {
            setSavingReassign(true);
            await reassignAnswerSheet(effectiveTeacherUid, assessmentUid, reassignTarget.studentId, trimmed);
            await loadResults();
            closeReassign();
            Alert.alert('Reassigned', 'Answer sheet moved successfully.');
          } catch (error: any) {
            Alert.alert('Error', error.message);
          } finally { setSavingReassign(false); }
        },
      },
    ]);
  };

  // ─────────────────────────────────────────────
  // Edit Answer Sheet
  // ─────────────────────────────────────────────

  const openEditSheet = (r: AnswerSheetResult) => {
    setEditingResult(r);

    // Build editable rows from breakdown, sorted numerically
    const rows: EditableRow[] = Object.entries(r.breakdown)
      .sort(([a], [b]) => parseInt(a.replace(/\D/g, '')) - parseInt(b.replace(/\D/g, '')))
      .map(([key, qData]) => ({
        questionKey: key,
        studentAnswer: qData.student_answer,
        correctAnswer: qData.correct_answer,
        checkingResult: qData.checking_result,
        editedAnswer: qData.student_answer,
        editedResult: qData.checking_result,
        isDirty: false,
      }));

    setEditableRows(rows);
    // Default toggle: if sheet is pending, leave as not final; otherwise already final
    setMarkFinal(!r.is_final_score ? false : true);
    setEditSheetModalVisible(true);
  };

  const closeEditSheet = () => {
    setEditSheetModalVisible(false);
    setEditingResult(null);
    setEditableRows([]);
    setMarkFinal(false);
  };

  const updateRow = (index: number, field: 'editedAnswer' | 'editedResult', value: any) => {
    setEditableRows(prev => prev.map((row, i) => {
      if (i !== index) return row;
      const updated = { ...row, [field]: value, isDirty: true };

      // Auto-set result when answer changes (skip essay)
      if (field === 'editedAnswer') {
        const trimmed = (value as string).trim();
        if (trimmed === 'essay_answer') {
          updated.editedResult = 'pending';
        } else if (trimmed !== '') {
          updated.editedResult = trimmed === row.correctAnswer;
        }
      }
      return updated;
    }));
  };

  const handleSaveSheet = async () => {
    if (!editingResult) return;

    const dirtyRows = editableRows.filter(r => r.isDirty);
    if (dirtyRows.length === 0 && markFinal === editingResult.is_final_score) {
      closeEditSheet();
      return;
    }

    // Recalculate preview score
    const previewScore = editableRows.reduce((acc, row) => {
      const result = row.isDirty ? row.editedResult : row.checkingResult;
      return result === true ? acc + 1 : acc;
    }, 0);

    const hasPending = editableRows.some(row => {
      const result = row.isDirty ? row.editedResult : row.checkingResult;
      return result === 'pending';
    });

    const willBeFinal = markFinal || !hasPending;

    let msg = `Apply changes to ${editingResult.matchedStudentName ?? editingResult.studentId}?\n\n`;
    msg += `${dirtyRows.length} answer${dirtyRows.length !== 1 ? 's' : ''} edited\n`;
    msg += `New score: ${previewScore} / ${editingResult.total_questions} `;
    msg += `(${pct(previewScore, editingResult.total_questions)}%)\n`;
    msg += `Status: ${willBeFinal ? '✅ Final' : '⏳ Still Pending'}`;

    if (!willBeFinal && markFinal) {
      msg += `\n\n⚠️ There are still pending (essay) questions. Status will remain Pending until all are graded.`;
    }

    Alert.alert('Confirm Changes', msg, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Save & Re-score',
        onPress: async () => {
          try {
            setSavingSheet(true);
            const edits: StudentAnswerEdit[] = dirtyRows.map(row => ({
              questionKey: row.questionKey,
              newStudentAnswer: row.editedAnswer.trim(),
              newCheckingResult: row.editedResult,
            }));

            const { newScore, newTotal } = await updateStudentAnswerSheet(
              effectiveTeacherUid, assessmentUid,
              editingResult.studentId, edits, markFinal
            );

            await loadResults();
            closeEditSheet();
            Alert.alert(
              'Saved',
              `Score updated: ${newScore} / ${newTotal} (${pct(newScore, newTotal)}%)\n` +
              `Status: ${willBeFinal ? 'Final ✅' : 'Pending ⏳'}`
            );
          } catch (error: any) {
            Alert.alert('Error', error.message || 'Failed to save changes');
          } finally { setSavingSheet(false); }
        },
      },
    ]);
  };

  // ─────────────────────────────────────────────
  // Validation badge
  // ─────────────────────────────────────────────

  const renderValidationBadge = () => {
    if (!reassignTarget) return null;
    if (newStudentId.trim() === reassignTarget.studentId) return null;
    if (validating) return (
      <View style={styles.validationRow}>
        <ActivityIndicator size="small" color="#6366f1" />
        <Text style={styles.validatingText}>  Validating...</Text>
      </View>
    );
    if (!idValidated || !idValidation) return null;
    if (!idValidation.exists) return (
      <View style={[styles.validationRow, styles.valError]}>
        <Text style={styles.valErrorText}>❌ Student ID not registered in the app</Text>
      </View>
    );
    if (idValidation.enrolled) return (
      <View style={[styles.validationRow, styles.valOk]}>
        <Text style={styles.valOkText}>✅ {idValidation.studentName} — Enrolled</Text>
      </View>
    );
    return (
      <View style={[styles.validationRow, styles.valWarn]}>
        <Text style={styles.valWarnText}>⚠️ {idValidation.studentName} — Not enrolled in this subject</Text>
      </View>
    );
  };

  // ─────────────────────────────────────────────
  // Loading
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
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{assessmentName ?? 'Assessment Results'}</Text>
          <Text style={styles.headerUid}>UID: {assessmentUid}</Text>

          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statNum}>{results.length}</Text>
              <Text style={styles.statLbl}>Scanned</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statNum}>{pendingList.length}</Text>
              <Text style={styles.statLbl}>Pending</Text>
            </View>
            {scored.length > 0 && <>
              <View style={styles.statBox}>
                <Text style={styles.statNum}>{avgPct.toFixed(1)}%</Text>
                <Text style={styles.statLbl}>Average</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={styles.statNum}>{highPct}%</Text>
                <Text style={styles.statLbl}>Highest</Text>
              </View>
            </>}
          </View>

          {hasUnmatched && (
            <View style={styles.warningBanner}>
              <Text style={styles.warningBannerText}>
                ⚠️ Some student IDs could not be matched. Use ✏️ Edit → Reassign ID on a row to fix.
              </Text>
            </View>
          )}
        </View>

        {/* Results */}
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
              const percentage = pct(r.total_score, r.total_questions);
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
                      <Text style={styles.checkedAt}>Scanned: {formatDate(r.checked_at)}</Text>
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
                    <TouchableOpacity style={styles.editRowButton} onPress={() => openEditSheet(r)}>
                      <Text style={styles.editRowButtonText}>✏️ Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.reassignButton} onPress={() => openReassign(r)}>
                      <Text style={styles.reassignButtonText}>👤</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })
          )}
        </View>
      </ScrollView>

      {/* ── Reassign Student ID Modal ──────────────── */}
      <Modal visible={reassignModalVisible} transparent animationType="slide" onRequestClose={closeReassign}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Reassign Student ID</Text>

            {reassignTarget && (
              <View style={styles.infoBox}>
                <Text style={styles.infoName}>{reassignTarget.matchedStudentName ?? 'Unknown Student'}</Text>
                <Text style={styles.infoSub}>Current ID: {reassignTarget.studentId}</Text>
              </View>
            )}

            <Text style={styles.fieldLabel}>New Student ID</Text>
            <View style={styles.inputRow}>
              <TextInput
                style={[styles.textInput, { flex: 1, marginBottom: 0 }]}
                value={newStudentId}
                onChangeText={t => { setNewStudentId(t); setIdValidated(false); setIdValidation(null); }}
                placeholder="School-provided ID"
                keyboardType="numeric"
                editable={!savingReassign}
              />
              <TouchableOpacity
                style={[styles.validateBtn, validating && { opacity: 0.6 }]}
                onPress={handleValidateId}
                disabled={validating || savingReassign}
              >
                {validating
                  ? <ActivityIndicator size="small" color="#fff" />
                  : <Text style={styles.validateBtnText}>Validate</Text>
                }
              </TouchableOpacity>
            </View>
            {renderValidationBadge()}

            <View style={[styles.modalButtons, { marginTop: 12 }]}>
              <TouchableOpacity style={styles.cancelBtn} onPress={closeReassign} disabled={savingReassign}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.saveBtn, { backgroundColor: '#ef4444' }]}
                onPress={handleConfirmReassign}
                disabled={savingReassign}
              >
                {savingReassign
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.saveBtnText}>Reassign</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Edit Answer Sheet Modal ────────────────── */}
      <Modal visible={editSheetModalVisible} transparent animationType="slide" onRequestClose={closeEditSheet}>
        <View style={styles.modalOverlay}>
          <ScrollView contentContainerStyle={styles.modalScrollContent}>
            <View style={styles.modalContent}>
              <Text style={styles.modalTitle}>Edit Answer Sheet</Text>

              {editingResult && (
                <View style={styles.infoBox}>
                  <Text style={styles.infoName}>
                    {editingResult.matchedStudentName ?? 'Unknown Student'}
                  </Text>
                  <Text style={styles.infoSub}>
                    ID: {editingResult.studentId}{'  '}·{'  '}
                    Score: {editingResult.total_score}/{editingResult.total_questions}{'  '}·{'  '}
                    {editingResult.is_final_score ? '✅ Final' : '⏳ Pending'}
                  </Text>
                </View>
              )}

              <View style={styles.editInstructions}>
                <Text style={styles.editInstructionsText}>
                  Edit student answers below to correct OCR errors or manually grade essays.
                  The score will be recalculated automatically based on your changes.
                </Text>
              </View>

              {/* Question rows */}
              {editableRows.map((row, index) => {
                const isEssay = row.correctAnswer === 'essay_answer' ||
                                row.correctAnswer === 'will_check_by_teacher' ||
                                row.editedAnswer === 'essay_answer';
                const resultColor =
                  row.editedResult === true ? '#16a34a' :
                  row.editedResult === 'pending' ? '#d97706' : '#dc2626';

                return (
                  <View key={row.questionKey} style={[
                    styles.questionRow,
                    row.isDirty && styles.questionRowDirty,
                  ]}>
                    <View style={styles.qRowLeft}>
                      <Text style={styles.qLabel}>{row.questionKey}</Text>
                      {row.isDirty && <Text style={styles.dirtyDot}>●</Text>}
                    </View>

                    <View style={styles.qRowCenter}>
                      <Text style={styles.qCorrectLabel}>
                        Correct: <Text style={styles.qCorrectValue}>{row.correctAnswer}</Text>
                      </Text>
                      <TextInput
                        style={[styles.qAnswerInput, row.isDirty && styles.qAnswerInputDirty]}
                        value={row.editedAnswer}
                        onChangeText={t => updateRow(index, 'editedAnswer', t)}
                        placeholder="Student answer"
                        autoCapitalize="characters"
                      />
                    </View>

                    <View style={styles.qRowRight}>
                      {isEssay ? (
                        // Essay: 3-way toggle
                        <View style={styles.essayToggle}>
                          <TouchableOpacity
                            style={[styles.essayBtn, row.editedResult === true && styles.essayBtnCorrect]}
                            onPress={() => updateRow(index, 'editedResult', true)}
                          >
                            <Text style={styles.essayBtnText}>✓</Text>
                          </TouchableOpacity>
                          <TouchableOpacity
                            style={[styles.essayBtn, row.editedResult === false && styles.essayBtnWrong]}
                            onPress={() => updateRow(index, 'editedResult', false)}
                          >
                            <Text style={styles.essayBtnText}>✗</Text>
                          </TouchableOpacity>
                          <TouchableOpacity
                            style={[styles.essayBtn, row.editedResult === 'pending' && styles.essayBtnPending]}
                            onPress={() => updateRow(index, 'editedResult', 'pending')}
                          >
                            <Text style={styles.essayBtnText}>⏳</Text>
                          </TouchableOpacity>
                        </View>
                      ) : (
                        <View style={[styles.resultPill, { backgroundColor: resultColor + '20' }]}>
                          <Text style={[styles.resultPillText, { color: resultColor }]}>
                            {row.editedResult === true ? '✓' :
                             row.editedResult === 'pending' ? '⏳' : '✗'}
                          </Text>
                        </View>
                      )}
                    </View>
                  </View>
                );
              })}

              {/* Mark as Final toggle */}
              {editingResult && !editingResult.is_final_score && (
                <View style={styles.markFinalRow}>
                  <View style={styles.markFinalLeft}>
                    <Text style={styles.markFinalLabel}>Mark sheet as Final</Text>
                    <Text style={styles.markFinalSub}>
                      Turn on if all essays are now graded and score is complete.
                    </Text>
                  </View>
                  <Switch
                    value={markFinal}
                    onValueChange={setMarkFinal}
                    trackColor={{ false: '#cbd5e1', true: '#22c55e' }}
                    thumbColor={markFinal ? '#ffffff' : '#f1f5f9'}
                  />
                </View>
              )}

              <View style={styles.modalButtons}>
                <TouchableOpacity style={styles.cancelBtn} onPress={closeEditSheet} disabled={savingSheet}>
                  <Text style={styles.cancelBtnText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.saveBtn} onPress={handleSaveSheet} disabled={savingSheet}>
                  {savingSheet
                    ? <ActivityIndicator color="#fff" size="small" />
                    : <Text style={styles.saveBtnText}>Save & Re-score</Text>
                  }
                </TouchableOpacity>
              </View>
            </View>
          </ScrollView>
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

  header: {
    backgroundColor: '#171443', paddingHorizontal: 24,
    paddingVertical: 24, borderBottomWidth: 1, borderBottomColor: '#2a2060',
  },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#ffffff', marginBottom: 4 },
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
  warningBannerText: { fontSize: 12, color: '#92400e', lineHeight: 18 },

  listSection: { padding: 16 },
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 64, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#64748b', marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: '#94a3b8', textAlign: 'center', paddingHorizontal: 32 },

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
  unmatchedBadge: { backgroundColor: '#fef3c7', paddingHorizontal: 5, paddingVertical: 1, borderRadius: 4 },
  unmatchedText: { fontSize: 12 },
  schoolId: { fontSize: 13, color: '#64748b', fontFamily: 'monospace', marginBottom: 2 },
  checkedAt: { fontSize: 11, color: '#94a3b8' },
  scoreDisplay: { alignItems: 'flex-end', minWidth: 64 },
  scorePct: { fontSize: 28, fontWeight: 'bold' },
  scoreGrade: { fontSize: 14, fontWeight: '600' },
  pendingBadge: { backgroundColor: '#fef3c7', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  pendingText: { fontSize: 12, color: '#d97706', fontWeight: '700' },
  scoreFraction: { fontSize: 13, color: '#64748b', marginBottom: 8 },
  progressBg: { height: 8, backgroundColor: '#f1f5f9', borderRadius: 4, overflow: 'hidden', marginBottom: 12 },
  progressFill: { height: '100%', borderRadius: 4 },
  cardActions: { flexDirection: 'row', gap: 8 },
  breakdownButton: {
    flex: 1, backgroundColor: '#dbeafe',
    paddingVertical: 10, borderRadius: 8, alignItems: 'center',
  },
  breakdownButtonText: { fontSize: 14, fontWeight: '600', color: '#2563eb' },
  editRowButton: {
    flex: 1, backgroundColor: '#f0fdf4',
    paddingVertical: 10, borderRadius: 8, alignItems: 'center',
  },
  editRowButtonText: { fontSize: 14, fontWeight: '600', color: '#16a34a' },
  reassignButton: {
    backgroundColor: '#f1f5f9', paddingVertical: 10,
    paddingHorizontal: 14, borderRadius: 8, alignItems: 'center',
  },
  reassignButtonText: { fontSize: 16 },

  // Modal shared
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center', alignItems: 'center', padding: 16,
  },
  modalScrollContent: { flexGrow: 1, justifyContent: 'center', padding: 8 },
  modalContent: {
    backgroundColor: '#ffffff', borderRadius: 16,
    padding: 24, width: '100%', maxWidth: 440,
  },
  modalTitle: { fontSize: 20, fontWeight: 'bold', color: '#1e293b', marginBottom: 16, textAlign: 'center' },
  infoBox: { backgroundColor: '#f8fafc', borderRadius: 10, padding: 12, marginBottom: 16 },
  infoName: { fontSize: 15, fontWeight: '600', color: '#1e293b', marginBottom: 2 },
  infoSub: { fontSize: 12, color: '#64748b' },
  fieldLabel: { fontSize: 14, fontWeight: '600', color: '#475569', marginBottom: 8 },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  textInput: {
    borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8,
    paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 16, color: '#1e293b', marginBottom: 12,
  },
  validateBtn: { backgroundColor: '#6366f1', paddingVertical: 14, paddingHorizontal: 14, borderRadius: 8 },
  validateBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },

  // Validation
  validationRow: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, marginBottom: 8,
  },
  validatingText: { fontSize: 13, color: '#6366f1' },
  valOk: { backgroundColor: '#f0fdf4' },
  valOkText: { fontSize: 13, color: '#16a34a', fontWeight: '600' },
  valWarn: { backgroundColor: '#fefce8' },
  valWarnText: { fontSize: 13, color: '#ca8a04', fontWeight: '600' },
  valError: { backgroundColor: '#fef2f2' },
  valErrorText: { fontSize: 13, color: '#dc2626', fontWeight: '600' },

  // Edit answer sheet
  editInstructions: {
    backgroundColor: '#f0f9ff', borderRadius: 8, borderLeftWidth: 3,
    borderLeftColor: '#3b82f6', padding: 10, marginBottom: 16,
  },
  editInstructionsText: { fontSize: 12, color: '#1e40af', lineHeight: 18 },

  questionRow: {
    flexDirection: 'row', alignItems: 'center',
    paddingVertical: 10, paddingHorizontal: 8, borderRadius: 8,
    marginBottom: 6, backgroundColor: '#f8fafc',
    borderWidth: 1, borderColor: '#f1f5f9',
  },
  questionRowDirty: { borderColor: '#6366f1', backgroundColor: '#eef2ff' },
  qRowLeft: { width: 40, alignItems: 'center' },
  qLabel: { fontSize: 13, fontWeight: '700', color: '#475569' },
  dirtyDot: { fontSize: 8, color: '#6366f1', marginTop: 2 },
  qRowCenter: { flex: 1, paddingHorizontal: 8 },
  qCorrectLabel: { fontSize: 11, color: '#94a3b8', marginBottom: 4 },
  qCorrectValue: { fontWeight: '600', color: '#64748b' },
  qAnswerInput: {
    borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 6,
    paddingHorizontal: 10, paddingVertical: 6,
    fontSize: 14, color: '#1e293b', backgroundColor: '#fff',
  },
  qAnswerInputDirty: { borderColor: '#6366f1' },
  qRowRight: { width: 64, alignItems: 'center' },
  resultPill: {
    width: 36, height: 36, borderRadius: 18,
    justifyContent: 'center', alignItems: 'center',
  },
  resultPillText: { fontSize: 16, fontWeight: 'bold' },

  // Essay toggle
  essayToggle: { flexDirection: 'column', gap: 4 },
  essayBtn: {
    width: 32, height: 28, borderRadius: 6, backgroundColor: '#f1f5f9',
    justifyContent: 'center', alignItems: 'center',
  },
  essayBtnText: { fontSize: 12 },
  essayBtnCorrect: { backgroundColor: '#dcfce7' },
  essayBtnWrong: { backgroundColor: '#fee2e2' },
  essayBtnPending: { backgroundColor: '#fef3c7' },

  // Mark final toggle
  markFinalRow: {
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between', backgroundColor: '#f8fafc',
    borderRadius: 10, padding: 14, marginTop: 8, marginBottom: 8,
    borderWidth: 1, borderColor: '#e2e8f0',
  },
  markFinalLeft: { flex: 1, marginRight: 12 },
  markFinalLabel: { fontSize: 15, fontWeight: '600', color: '#1e293b', marginBottom: 2 },
  markFinalSub: { fontSize: 12, color: '#64748b', lineHeight: 16 },

  modalButtons: { flexDirection: 'row', gap: 12, marginTop: 8 },
  cancelBtn: { flex: 1, paddingVertical: 13, borderRadius: 8, backgroundColor: '#f1f5f9', alignItems: 'center' },
  cancelBtnText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  saveBtn: { flex: 1, paddingVertical: 13, borderRadius: 8, backgroundColor: '#22c55e', alignItems: 'center' },
  saveBtnText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },
});

export default ViewScoresScreen;