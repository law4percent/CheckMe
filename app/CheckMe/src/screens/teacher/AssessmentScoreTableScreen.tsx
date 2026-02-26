// src/screens/teacher/AssessmentScoreTableScreen.tsx
import React, { useState, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Image, Dimensions, FlatList, TextInput, Alert,
  ActivityIndicator, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, QuestionBreakdown } from '../../types';
import {
  updateStudentAnswerSheet,
  StudentAnswerEdit,
} from '../../services/answerSheetService';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherAssessmentScoreTable'>;

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const IMAGE_WIDTH = SCREEN_WIDTH - 48;

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface EditableRow {
  questionKey: string;
  studentAnswer: string;
  correctAnswer: string;
  checkingResult: boolean | 'pending';
  editedAnswer: string;
  editedResult: boolean | 'pending';
  isDirty: boolean;
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

const calcPct = (score: number, total: number) =>
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

const isEssayQuestion = (row: EditableRow) =>
  row.correctAnswer === 'essay_answer' ||
  row.correctAnswer === 'will_check_by_teacher' ||
  row.editedAnswer === 'essay_answer';

const buildRows = (breakdown: Record<string, QuestionBreakdown>): EditableRow[] =>
  Object.entries(breakdown)
    .sort(([a], [b]) => parseInt(a.replace(/\D/g, '')) - parseInt(b.replace(/\D/g, '')))
    .map(([key, q]) => ({
      questionKey: key,
      studentAnswer: q.student_answer,
      correctAnswer: q.correct_answer,
      checkingResult: q.checking_result,
      editedAnswer: q.student_answer,
      editedResult: q.checking_result,
      isDirty: false,
    }));

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

const AssessmentScoreTableScreen: React.FC<Props> = ({ route, navigation }) => {
  const {
    result: initialResult,
    assessmentName,
    teacherUid,
    assessmentUid,
    subjectUid,
  } = route.params;

  const flatListRef = useRef<FlatList>(null);

  // ── Local mutable state ────────────────────
  const [rows, setRows]       = useState<EditableRow[]>(() => buildRows(initialResult.breakdown));
  const [isFinal, setIsFinal] = useState(initialResult.is_final_score);
  const [saving, setSaving]   = useState(false);

  // Keep a live score preview derived from rows + isFinal
  const liveScore = rows.reduce((acc, r) => {
    const result = r.isDirty ? r.editedResult : r.checkingResult;
    return result === true ? acc + 1 : acc;
  }, 0);
  const liveTotal     = initialResult.total_questions;
  const livePct       = calcPct(liveScore, liveTotal);
  const liveColor     = scoreColor(livePct);
  const anyDirty      = rows.some(r => r.isDirty) || isFinal !== initialResult.is_final_score;
  const hasPendingRow = rows.some(r => (r.isDirty ? r.editedResult : r.checkingResult) === 'pending');

  // ─────────────────────────────────────────────
  // Row editing
  // ─────────────────────────────────────────────

  const updateRow = useCallback((index: number, field: 'editedAnswer' | 'editedResult', value: any) => {
    setRows(prev => prev.map((row, i) => {
      if (i !== index) return row;
      const updated: EditableRow = { ...row, [field]: value, isDirty: true };

      if (field === 'editedAnswer') {
        const trimmed = (value as string).trim().toUpperCase();
        if (trimmed === 'ESSAY_ANSWER' || trimmed === '') {
          updated.editedAnswer = value;
          updated.editedResult = 'pending';
        } else {
          updated.editedAnswer = value;
          updated.editedResult = trimmed === row.correctAnswer.toUpperCase();
        }
      }
      return updated;
    }));
  }, []);

  // ─────────────────────────────────────────────
  // Save
  // ─────────────────────────────────────────────

  const handleSave = () => {
    const dirtyRows = rows.filter(r => r.isDirty);
    const finalChanged = isFinal !== initialResult.is_final_score;

    if (dirtyRows.length === 0 && !finalChanged) return;

    // If teacher marks final but pending rows exist — warn but allow
    let msg = '';
    if (dirtyRows.length > 0) {
      msg += `${dirtyRows.length} answer${dirtyRows.length > 1 ? 's' : ''} edited.\n`;
    }
    msg += `New score: ${liveScore} / ${liveTotal} (${livePct}%)\n`;
    msg += `Status: ${isFinal ? '✅ Final' : '⏳ Pending'}`;

    if (isFinal && hasPendingRow) {
      msg += `\n\n⚠️ Some questions are still pending (essay). Marking as Final anyway — you can change this later.`;
    }

    Alert.alert('Save Changes?', msg, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Save & Re-score',
        onPress: async () => {
          try {
            setSaving(true);
            const edits: StudentAnswerEdit[] = dirtyRows.map(row => ({
              questionKey: row.questionKey,
              newStudentAnswer: row.editedAnswer.trim(),
              newCheckingResult: row.editedResult,
            }));

            await updateStudentAnswerSheet(
              teacherUid, assessmentUid,
              initialResult.studentId, edits, isFinal
            );

            // Mark rows clean
            setRows(prev => prev.map(r => ({
              ...r,
              studentAnswer: r.isDirty ? r.editedAnswer : r.studentAnswer,
              checkingResult: r.isDirty ? r.editedResult : r.checkingResult,
              isDirty: false,
            })));

            Alert.alert(
              'Saved',
              `Score: ${liveScore} / ${liveTotal} (${livePct}%)\n` +
              `Status: ${isFinal ? 'Final ✅' : 'Pending ⏳'}`
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
  // Render
  // ─────────────────────────────────────────────

  const displayName = initialResult.matchedStudentName ?? 'Unknown Student';

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView style={styles.scrollView} keyboardShouldPersistTaps="handled">

        {/* ── Student + score header ───────────── */}
        <View style={styles.header}>
          <View style={styles.headerTop}>
            <View style={styles.headerInfo}>
              <Text style={styles.studentName}>{displayName}</Text>
              <Text style={styles.schoolId}>ID: {initialResult.studentId}</Text>
              {!initialResult.matchedStudentName && (
                <View style={styles.unmatchedBadge}>
                  <Text style={styles.unmatchedText}>⚠️ Unmatched ID</Text>
                </View>
              )}
              <Text style={styles.assessmentLabel}>{assessmentName}</Text>
            </View>

            <View style={styles.scoreCircle}>
              <Text style={[styles.scoreCirclePct, { color: liveColor }]}>{livePct}%</Text>
              <Text style={[styles.scoreCircleGrade, { color: liveColor }]}>{gradeLabel(livePct)}</Text>
            </View>
          </View>

          {/* Summary row */}
          <View style={styles.scoreSummaryRow}>
            {[
              { label: 'Score', value: String(liveScore), color: '#ffffff' },
              { label: 'Total', value: String(liveTotal), color: '#ffffff' },
              {
                label: 'Correct',
                value: String(rows.filter(r => (r.isDirty ? r.editedResult : r.checkingResult) === true).length),
                color: '#22c55e',
              },
              {
                label: 'Wrong',
                value: String(rows.filter(r => (r.isDirty ? r.editedResult : r.checkingResult) === false).length),
                color: '#ef4444',
              },
              {
                label: 'Pending',
                value: String(rows.filter(r => (r.isDirty ? r.editedResult : r.checkingResult) === 'pending').length),
                color: '#f59e0b',
              },
            ].map((item, i, arr) => (
              <React.Fragment key={item.label}>
                <View style={styles.summaryItem}>
                  <Text style={[styles.summaryNum, { color: item.color }]}>{item.value}</Text>
                  <Text style={styles.summaryLbl}>{item.label}</Text>
                </View>
                {i < arr.length - 1 && <View style={styles.summaryDivider} />}
              </React.Fragment>
            ))}
          </View>

          {/* Final / Pending toggle — always visible */}
          <View style={styles.finalToggleRow}>
            <View style={styles.finalToggleLeft}>
              <Text style={styles.finalToggleLabel}>
                {isFinal ? '✅ Final Score' : '⏳ Pending'}
              </Text>
              <Text style={styles.finalToggleSub}>
                {isFinal
                  ? 'Tap to revert back to Pending'
                  : 'Turn on when all answers are graded'}
              </Text>
            </View>
            <Switch
              value={isFinal}
              onValueChange={setIsFinal}
              trackColor={{ false: '#475569', true: '#22c55e' }}
              thumbColor="#ffffff"
            />
          </View>
        </View>

        {/* ── Image gallery ────────────────────── */}
        {initialResult.image_urls.length > 0 && (
          <View style={styles.gallerySection}>
            <Text style={styles.sectionTitle}>
              📷 Answer Sheet Images ({initialResult.image_urls.length})
            </Text>
            <FlatList
              ref={flatListRef}
              data={initialResult.image_urls}
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              keyExtractor={(_, i) => String(i)}
              renderItem={({ item, index }) => (
                <View style={styles.imageWrapper}>
                  <Image
                    source={{ uri: item }}
                    style={styles.sheetImage}
                    resizeMode="contain"
                  />
                  <Text style={styles.imagePageLabel}>
                    Page {index + 1} of {initialResult.image_urls.length}
                  </Text>
                </View>
              )}
              snapToInterval={IMAGE_WIDTH + 12}
              decelerationRate="fast"
            />
          </View>
        )}

        {/* ── Edit instructions ────────────────── */}
        <View style={styles.instructionsBanner}>
          <Text style={styles.instructionsText}>
            ✏️ Tap any student answer field to correct an OCR error. Essay questions have a ✓ / ✗ / ⏳ toggle. Changes are highlighted in purple — tap <Text style={{ fontWeight: '700' }}>Save</Text> at the bottom when done.
          </Text>
        </View>

        {/* ── Breakdown table ──────────────────── */}
        <View style={styles.breakdownSection}>
          <Text style={styles.sectionTitle}>📝 Question Breakdown</Text>

          <View style={styles.tableHeader}>
            <Text style={[styles.thCell, styles.colQ]}>Q</Text>
            <Text style={[styles.thCell, styles.colStudentAnswer]}>Student Answer</Text>
            <Text style={[styles.thCell, styles.colCorrectAnswer]}>Correct</Text>
            <Text style={[styles.thCell, styles.colResult]}>Result</Text>
          </View>

          {rows.map((row, index) => {
            const essay = isEssayQuestion(row);
            const currentResult = row.isDirty ? row.editedResult : row.checkingResult;
            const resultColor =
              currentResult === true ? '#22c55e' :
              currentResult === 'pending' ? '#f59e0b' : '#ef4444';

            return (
              <View
                key={row.questionKey}
                style={[
                  styles.tableRow,
                  index % 2 === 0 ? styles.tableRowEven : styles.tableRowOdd,
                  currentResult === true   && styles.tableRowCorrect,
                  currentResult === false  && styles.tableRowWrong,
                  currentResult === 'pending' && styles.tableRowPending,
                  row.isDirty && styles.tableRowDirty,
                ]}
              >
                {/* Q label + dirty dot */}
                <View style={[styles.colQ, styles.qLabelCell]}>
                  <Text style={styles.qLabel}>{row.questionKey}</Text>
                  {row.isDirty && <View style={styles.dirtyDot} />}
                </View>

                {/* Student answer — editable */}
                <View style={styles.colStudentAnswer}>
                  <TextInput
                    style={[
                      styles.answerInput,
                      row.isDirty && styles.answerInputDirty,
                      currentResult === false && styles.answerInputWrong,
                    ]}
                    value={row.editedAnswer}
                    onChangeText={t => updateRow(index, 'editedAnswer', t)}
                    autoCapitalize="characters"
                    selectTextOnFocus
                    placeholder="—"
                  />
                </View>

                {/* Correct answer — read-only */}
                <View style={styles.colCorrectAnswer}>
                  <Text style={styles.correctAnswerText} numberOfLines={2}>
                    {row.correctAnswer}
                  </Text>
                </View>

                {/* Result — essay gets toggle, others auto */}
                <View style={[styles.colResult, styles.resultCell]}>
                  {essay ? (
                    <View style={styles.essayToggle}>
                      <TouchableOpacity
                        style={[styles.essayBtn, row.editedResult === true && styles.essayBtnActive]}
                        onPress={() => updateRow(index, 'editedResult', true)}
                      >
                        <Text style={styles.essayBtnText}>✓</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.essayBtn, row.editedResult === false && styles.essayBtnActiveWrong]}
                        onPress={() => updateRow(index, 'editedResult', false)}
                      >
                        <Text style={styles.essayBtnText}>✗</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.essayBtn, row.editedResult === 'pending' && styles.essayBtnActivePending]}
                        onPress={() => updateRow(index, 'editedResult', 'pending')}
                      >
                        <Text style={styles.essayBtnText}>⏳</Text>
                      </TouchableOpacity>
                    </View>
                  ) : (
                    <>
                      <Text style={[styles.resultIcon, { color: resultColor }]}>
                        {currentResult === true ? '✓' : currentResult === 'pending' ? '⏳' : '✗'}
                      </Text>
                      <Text style={[styles.resultLabel, { color: resultColor }]}>
                        {currentResult === true ? 'Correct' : currentResult === 'pending' ? 'Pending' : 'Wrong'}
                      </Text>
                    </>
                  )}
                </View>
              </View>
            );
          })}
        </View>

        {/* ── Metadata ─────────────────────────── */}
        <View style={styles.metaSection}>
          <Text style={styles.metaTitle}>Scan Details</Text>
          {[
            { key: 'Checked by', val: initialResult.checked_by || '—' },
            {
              key: 'Checked at',
              val: initialResult.checked_at
                ? new Date(initialResult.checked_at).toLocaleString() : '—',
            },
            {
              key: 'Last updated',
              val: initialResult.updated_at
                ? new Date(initialResult.updated_at).toLocaleString() : '—',
            },
          ].map(row => (
            <View key={row.key} style={styles.metaRow}>
              <Text style={styles.metaKey}>{row.key}</Text>
              <Text style={styles.metaVal}>{row.val}</Text>
            </View>
          ))}
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ── Sticky Save bar ──────────────────────── */}
      {anyDirty && (
        <View style={styles.saveBar}>
          <View style={styles.saveBarLeft}>
            <Text style={styles.saveBarScore}>{liveScore} / {liveTotal}</Text>
            <Text style={styles.saveBarChanges}>
              {rows.filter(r => r.isDirty).length} change{rows.filter(r => r.isDirty).length !== 1 ? 's' : ''}
              {' '}· {isFinal ? '✅ Final' : '⏳ Pending'}
            </Text>
          </View>
          <TouchableOpacity
            style={[styles.saveBtn, saving && { opacity: 0.7 }]}
            onPress={handleSave}
            disabled={saving}
          >
            {saving
              ? <ActivityIndicator color="#fff" size="small" />
              : <Text style={styles.saveBtnText}>Save & Re-score</Text>
            }
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
};

// ─────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollView: { flex: 1 },

  // Header
  header: {
    backgroundColor: '#171443',
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060',
  },
  headerTop: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 16 },
  headerInfo: { flex: 1, marginRight: 12 },
  studentName: { fontSize: 20, fontWeight: 'bold', color: '#ffffff', marginBottom: 4 },
  schoolId: { fontSize: 13, color: '#94a3b8', fontFamily: 'monospace', marginBottom: 6 },
  unmatchedBadge: {
    alignSelf: 'flex-start', backgroundColor: '#fef3c7',
    paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, marginBottom: 6,
  },
  unmatchedText: { fontSize: 11, color: '#d97706', fontWeight: '600' },
  assessmentLabel: { fontSize: 14, color: '#cdd5df' },
  scoreCircle: { alignItems: 'center', justifyContent: 'center' },
  scoreCirclePct: { fontSize: 36, fontWeight: 'bold' },
  scoreCircleGrade: { fontSize: 18, fontWeight: '600' },

  scoreSummaryRow: {
    flexDirection: 'row', backgroundColor: '#2a2060',
    borderRadius: 12, paddingVertical: 12, marginBottom: 14,
  },
  summaryItem: { flex: 1, alignItems: 'center' },
  summaryNum: { fontSize: 18, fontWeight: 'bold', color: '#ffffff', marginBottom: 2 },
  summaryLbl: { fontSize: 10, color: '#94a3b8' },
  summaryDivider: { width: 1, backgroundColor: '#475569', marginVertical: 4 },

  // Final toggle
  finalToggleRow: {
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#2a2060', borderRadius: 12,
    paddingHorizontal: 16, paddingVertical: 12,
  },
  finalToggleLeft: { flex: 1, marginRight: 12 },
  finalToggleLabel: { fontSize: 15, fontWeight: '700', color: '#ffffff', marginBottom: 2 },
  finalToggleSub: { fontSize: 12, color: '#94a3b8' },

  // Gallery
  gallerySection: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 8 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#1e293b', marginBottom: 12 },
  imageWrapper: {
    width: IMAGE_WIDTH, marginRight: 12,
    backgroundColor: '#1e293b', borderRadius: 12, overflow: 'hidden',
  },
  sheetImage: { width: IMAGE_WIDTH, height: IMAGE_WIDTH * 1.35 },
  imagePageLabel: {
    textAlign: 'center', color: '#94a3b8', fontSize: 12,
    paddingVertical: 8, backgroundColor: '#1e293b',
  },

  // Instructions banner
  instructionsBanner: {
    marginHorizontal: 24, marginTop: 16, marginBottom: 4,
    backgroundColor: '#eff6ff', borderRadius: 10,
    borderLeftWidth: 4, borderLeftColor: '#3b82f6',
    paddingHorizontal: 14, paddingVertical: 10,
  },
  instructionsText: { fontSize: 12, color: '#1e40af', lineHeight: 18 },

  // Breakdown table
  breakdownSection: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8 },
  tableHeader: {
    flexDirection: 'row', backgroundColor: '#1e293b',
    paddingVertical: 10, paddingHorizontal: 8,
    borderTopLeftRadius: 8, borderTopRightRadius: 8,
  },
  thCell: { fontSize: 12, fontWeight: '700', color: '#ffffff' },
  tableRow: {
    flexDirection: 'row', paddingVertical: 8,
    paddingHorizontal: 8, alignItems: 'center',
    borderBottomWidth: 1, borderBottomColor: '#e2e8f0',
  },
  tableRowEven: { backgroundColor: '#ffffff' },
  tableRowOdd: { backgroundColor: '#f8fafc' },
  tableRowCorrect: { borderLeftWidth: 3, borderLeftColor: '#22c55e' },
  tableRowWrong: { borderLeftWidth: 3, borderLeftColor: '#ef4444' },
  tableRowPending: { borderLeftWidth: 3, borderLeftColor: '#f59e0b' },
  tableRowDirty: { backgroundColor: '#eef2ff', borderLeftWidth: 3, borderLeftColor: '#6366f1' },

  // Columns
  colQ: { width: 36 },
  colStudentAnswer: { flex: 1, paddingHorizontal: 6 },
  colCorrectAnswer: { flex: 1, paddingHorizontal: 6 },
  colResult: { width: 68 },

  qLabelCell: { justifyContent: 'center', alignItems: 'center' },
  qLabel: { fontSize: 13, fontWeight: '700', color: '#6366f1', fontFamily: 'monospace' },
  dirtyDot: {
    width: 6, height: 6, borderRadius: 3,
    backgroundColor: '#6366f1', marginTop: 3,
  },

  answerInput: {
    borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 6,
    paddingHorizontal: 8, paddingVertical: 5,
    fontSize: 13, color: '#1e293b', backgroundColor: '#fff',
    textAlign: 'center',
  },
  answerInputDirty: { borderColor: '#6366f1', backgroundColor: '#eef2ff' },
  answerInputWrong: { color: '#ef4444' },

  correctAnswerText: {
    fontSize: 13, color: '#16a34a', fontWeight: '600', textAlign: 'center',
  },

  resultCell: { alignItems: 'center', justifyContent: 'center' },
  resultIcon: { fontSize: 18, fontWeight: 'bold', textAlign: 'center' },
  resultLabel: { fontSize: 9, fontWeight: '600', marginTop: 1, textAlign: 'center' },

  // Essay toggle
  essayToggle: { flexDirection: 'row', gap: 4, justifyContent: 'center' },
  essayBtn: {
    width: 26, height: 26, borderRadius: 6,
    backgroundColor: '#f1f5f9',
    justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: '#e2e8f0',
  },
  essayBtnText: { fontSize: 11 },
  essayBtnActive: { backgroundColor: '#dcfce7', borderColor: '#22c55e' },
  essayBtnActiveWrong: { backgroundColor: '#fee2e2', borderColor: '#ef4444' },
  essayBtnActivePending: { backgroundColor: '#fef3c7', borderColor: '#f59e0b' },

  // Meta
  metaSection: {
    marginHorizontal: 24, marginTop: 16, marginBottom: 8,
    backgroundColor: '#ffffff', borderRadius: 12, padding: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  metaTitle: { fontSize: 14, fontWeight: '700', color: '#475569', marginBottom: 12 },
  metaRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#f1f5f9',
  },
  metaKey: { fontSize: 13, color: '#64748b' },
  metaVal: {
    fontSize: 13, color: '#1e293b', fontWeight: '500',
    maxWidth: '60%', textAlign: 'right',
  },

  // Sticky save bar
  saveBar: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#1e293b',
    paddingHorizontal: 20, paddingVertical: 14,
    paddingBottom: 24,
    shadowColor: '#000', shadowOffset: { width: 0, height: -3 },
    shadowOpacity: 0.2, shadowRadius: 8, elevation: 10,
    borderTopLeftRadius: 16, borderTopRightRadius: 16,
  },
  saveBarLeft: { flex: 1 },
  saveBarScore: { fontSize: 18, fontWeight: 'bold', color: '#ffffff' },
  saveBarChanges: { fontSize: 12, color: '#94a3b8', marginTop: 1 },
  saveBtn: {
    backgroundColor: '#22c55e', paddingVertical: 12,
    paddingHorizontal: 20, borderRadius: 10,
  },
  saveBtnText: { fontSize: 15, fontWeight: '700', color: '#ffffff' },
});

export default AssessmentScoreTableScreen;