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
  reassignAnswerSheet,
  validateStudentId,
  StudentIdValidation,
  deleteAnswerSheet,
} from '../../services/answerSheetService';
import { getSubjectEnrollments, Enrollment } from '../../services/enrollmentService';
import * as XLSX from 'xlsx';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

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
// Component
// ─────────────────────────────────────────────

const ViewScoresScreen: React.FC<Props> = ({ route, navigation }) => {
  const { assessmentUid, assessmentName, assessmentType, teacherUid, subjectUid } = route.params;
  const { user } = useAuth();
  const effectiveTeacherUid = teacherUid ?? user?.uid ?? '';

  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [results, setResults]       = useState<AnswerSheetResult[]>([]);
  const [notScanned, setNotScanned] = useState<Enrollment[]>([]);

  // ── Delete answer sheet ──────────────────────
  const [deleteTarget, setDeleteTarget] = useState<AnswerSheetResult | null>(null);
  const [deleting, setDeleting]         = useState(false);

  // ── Export ──────────────────────────────────
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [exportSortOrder, setExportSortOrder] = useState<'firstName' | 'lastName' | 'studentId'>('firstName');
  const [exporting, setExporting] = useState(false);

  // ── Reassign Student ID modal ──────────────
  const [reassignModalVisible, setReassignModalVisible] = useState(false);
  const [reassignTarget, setReassignTarget]             = useState<AnswerSheetResult | null>(null);
  const [newStudentId, setNewStudentId]                 = useState('');
  const [savingReassign, setSavingReassign]             = useState(false);
  const [validating, setValidating]                     = useState(false);
  const [idValidation, setIdValidation]                 = useState<StudentIdValidation | null>(null);
  const [idValidated, setIdValidated]                   = useState(false);

  // ─────────────────────────────────────────────
  // Data
  // ─────────────────────────────────────────────

  const loadResults = useCallback(async () => {
    if (!effectiveTeacherUid || !assessmentUid) return;
    try {
      const [data, enrollments] = await Promise.all([
        getAnswerSheets(effectiveTeacherUid, assessmentUid, subjectUid),
        getSubjectEnrollments(effectiveTeacherUid, subjectUid),
      ]);
      setResults(data);

      // Build set of school IDs already scanned
      const scannedIds = new Set(data.map(r => String(r.studentId)));
      // Approved enrollments whose schoolId has no answer sheet yet
      const missing = enrollments.filter(e => {
        if (e.status !== 'approved') return false;
        if (!e.schoolId) return true; // no schoolId on record — always show as unscanned
        return !scannedIds.has(String(e.schoolId));
      });
      setNotScanned(missing);
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

  const scored       = results.filter(r => r.is_final_score);
  const pendingList  = results.filter(r => !r.is_final_score);
  const avgPct       = scored.length > 0
    ? scored.reduce((s, r) => s + pct(r.total_score, r.total_questions), 0) / scored.length : 0;
  const highPct      = scored.length > 0
    ? Math.max(...scored.map(r => pct(r.total_score, r.total_questions))) : 0;
  const hasUnmatched = results.some(r => !r.matchedStudentName);

  // ─────────────────────────────────────────────
  // Export to Excel
  // ─────────────────────────────────────────────

  const resolveTimestamp = (val: any): number => {
    if (!val) return 0;
    if (typeof val === 'number') return val;
    if (typeof val === 'string') return new Date(val).getTime();
    return 0;
  };

  const handleExport = async () => {
    try {
      setExporting(true);

      // ── Sort scanned results ──
      const sorted = [...results].sort((a, b) => {
        if (exportSortOrder === 'studentId') {
          return String(a.studentId).localeCompare(String(b.studentId), undefined, { numeric: true });
        }
        const nameA = a.matchedStudentName ?? '';
        const nameB = b.matchedStudentName ?? '';
        if (exportSortOrder === 'firstName') {
          const firstA = nameA.trim().split(' ')[0] ?? '';
          const firstB = nameB.trim().split(' ')[0] ?? '';
          return firstA.localeCompare(firstB);
        }
        // lastName
        const partsA = nameA.trim().split(' ');
        const partsB = nameB.trim().split(' ');
        const lastA = partsA[partsA.length - 1] ?? '';
        const lastB = partsB[partsB.length - 1] ?? '';
        return lastA.localeCompare(lastB);
      });

      // ── Sort not-scanned ──
      const sortedNotScanned = [...notScanned].sort((a, b) => {
        if (exportSortOrder === 'studentId') {
          return String(a.schoolId ?? '').localeCompare(String(b.schoolId ?? ''), undefined, { numeric: true });
        }
        const nameA = a.studentName ?? '';
        const nameB = b.studentName ?? '';
        if (exportSortOrder === 'firstName') {
          const firstA = nameA.trim().split(' ')[0] ?? '';
          const firstB = nameB.trim().split(' ')[0] ?? '';
          return firstA.localeCompare(firstB);
        }
        const partsA = nameA.trim().split(' ');
        const partsB = nameB.trim().split(' ');
        const lastA = partsA[partsA.length - 1] ?? '';
        const lastB = partsB[partsB.length - 1] ?? '';
        return lastA.localeCompare(lastB);
      });

      // ── Build rows ──
      const rows: any[] = [];

      // Assessment info rows
      rows.push([`Assessment Type: ${assessmentType ?? '—'}`]);
      rows.push([`Assessment Name: ${assessmentName ?? '—'}`]);
      rows.push([`Assessment UID: ${assessmentUid}`]);
      rows.push([]); // empty spacer row

      // Header row
      rows.push([
        '#',
        'Student ID',
        'Student Name',
        'Score',
        'Total Items',
        'Percentage',
        'Grade',
        'Status',
        'Scanned At',
      ]);

      // Scanned students
      sorted.forEach((r, index) => {
        const percentage = r.total_questions > 0
          ? Math.round((r.total_score / r.total_questions) * 100)
          : 0;
        const grade = (() => {
          if (!r.is_final_score) return 'Pending';
          if (percentage >= 90) return 'A';
          if (percentage >= 85) return 'B+';
          if (percentage >= 80) return 'B';
          if (percentage >= 75) return 'C+';
          if (percentage >= 70) return 'C';
          if (percentage >= 65) return 'D+';
          if (percentage >= 60) return 'D';
          return 'F';
        })();
        const status = r.is_final_score ? 'Scored' : 'Pending (Essay)';
        const scannedAt = resolveTimestamp(r.checked_at);
        const scannedAtStr = scannedAt
          ? new Date(scannedAt).toLocaleString('en-US', {
              month: 'short', day: 'numeric', year: 'numeric',
              hour: '2-digit', minute: '2-digit',
            })
          : '—';

        rows.push([
          index + 1,
          r.studentId,
          r.matchedStudentName ?? 'Unknown',
          r.is_final_score ? r.total_score : '—',
          r.total_questions,
          r.is_final_score ? `${percentage}%` : '—',
          grade,
          status,
          scannedAtStr,
        ]);
      });

      // Not-scanned students
      sortedNotScanned.forEach((e) => {
        rows.push([
          '—',
          e.schoolId ?? '—',
          e.studentName ?? 'Unknown',
          '—',
          '—',
          '—',
          '—',
          'No Answer Sheet Scanned',
          '—',
        ]);
      });

      // ── Build worksheet ──
      const ws = XLSX.utils.aoa_to_sheet(rows);

      // Column widths
      ws['!cols'] = [
        { wch: 4 },   // #
        { wch: 18 },  // Student ID
        { wch: 28 },  // Student Name
        { wch: 8 },   // Score
        { wch: 10 },  // Total Items
        { wch: 12 },  // Percentage
        { wch: 8 },   // Grade
        { wch: 24 },  // Status
        { wch: 24 },  // Scanned At
      ];

      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Scores');

      // ── Write to base64 ──
      const wbout = XLSX.write(wb, { type: 'base64', bookType: 'xlsx' });

      // ── Save to cache dir ──
      const safeName = (assessmentName ?? assessmentUid)
        .replace(/[^a-zA-Z0-9_\-]/g, '_')
        .substring(0, 40);
      const fileName = `${safeName}_${assessmentUid}_scores.xlsx`;
      // Property 'cacheDirectory' does not exist on type 'typeof import("/Users/fdc.lawrence-nc-aisolution/Desktop/CheckMe/app/CheckMe/node_modules/expo-file-system/build/index")'.ts(2339)
      // any
      const fileUri = `${FileSystem.cacheDirectory}${fileName}`; 

      // The signature '(fileUri: string, contents: string, options?: WritingOptions | undefined): Promise<void>' of 'FileSystem.writeAsStringAsync' is deprecated.ts(6387)
      // legacyWarnings.d.ts(15, 4): The declaration was marked as deprecated here.
      // function writeAsStringAsync(fileUri: string, contents: string, options?: WritingOptions | undefined): Promise<void>
      // @deprecated — Use new File().write() or import this method from expo-file-system/legacy. This method will throw in runtime.
      await FileSystem.writeAsStringAsync(fileUri, wbout, {
        encoding: 'base64',
      });

      // ── Share via Android share sheet ──
      const canShare = await Sharing.isAvailableAsync();
      if (!canShare) {
        Alert.alert('Error', 'Sharing is not available on this device.');
        return;
      }

      setExportModalVisible(false);
      await Sharing.shareAsync(fileUri, {
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        dialogTitle: `Export ${assessmentName ?? assessmentUid} Scores`,
        UTI: 'com.microsoft.excel.xlsx',
      });

    } catch (error: any) {
      Alert.alert('Export Failed', error.message || 'Failed to generate Excel file');
    } finally {
      setExporting(false);
    }
  };

  // ─────────────────────────────────────────────
  // Reassign Student ID
  // ─────────────────────────────────────────────

  const handleDeleteSheet = (r: AnswerSheetResult) => {
    setDeleteTarget(r);
  };

  const confirmDeleteSheet = async () => {
    if (!deleteTarget) return;
    try {
      setDeleting(true);
      await deleteAnswerSheet(effectiveTeacherUid, assessmentUid, deleteTarget.studentId);
      await loadResults();
      setDeleteTarget(null);
      Alert.alert('Deleted', 'Answer sheet removed successfully.');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to delete answer sheet');
    } finally {
      setDeleting(false);
    }
  };

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
    if (idValidation && !idValidation.enrolled)
      msg += `\n\n⚠️ This student is not enrolled in this subject.`;
    msg += `\n\nThe old record will be permanently deleted.`;

    Alert.alert('⚠️ Reassign Answer Sheet', msg, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Reassign', style: 'destructive',
        onPress: async () => {
          try {
            setSavingReassign(true);
            await reassignAnswerSheet(
              effectiveTeacherUid, assessmentUid,
              reassignTarget.studentId, trimmed
            );
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
        <Text style={styles.valWarnText}>
          ⚠️ {idValidation.studentName} — Not enrolled in this subject
        </Text>
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
        {/* ── Header ─────────────────────────────── */}
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
            <View style={styles.statBox}>
              <Text style={[styles.statNum, { color: '#ef4444' }]}>{notScanned.length}</Text>
              <Text style={styles.statLbl}>Not Scanned</Text>
            </View>
            {scored.length > 0 && (
              <View style={styles.statBox}>
                <Text style={styles.statNum}>{avgPct.toFixed(1)}%</Text>
                <Text style={styles.statLbl}>Average</Text>
              </View>
            )}
          </View>

          {hasUnmatched && (
            <View style={styles.warningBanner}>
              <Text style={styles.warningBannerText}>
                ⚠️ Some IDs could not be matched to enrolled students. Tap 👤 on a row to reassign.
              </Text>
            </View>
          )}

          <TouchableOpacity
            style={styles.exportButton}
            onPress={() => setExportModalVisible(true)}
            disabled={exporting}
          >
            <Text style={styles.exportButtonText}>📥 Export Excel</Text>
          </TouchableOpacity>
        </View>

        {/* ── Scanned results ─────────────────────── */}
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
                      <View style={[
                        styles.progressFill,
                        { width: `${percentage}%` as any, backgroundColor: color },
                      ]} />
                    </View>
                  )}

                  <View style={styles.cardActions}>
                    <TouchableOpacity
                      style={styles.breakdownButton}
                      onPress={() => navigation.navigate('TeacherAssessmentScoreTable', {
                        result: r,
                        assessmentName: assessmentName ?? assessmentUid,
                        teacherUid: effectiveTeacherUid,
                        assessmentUid,
                        subjectUid,
                      })}
                    >
                      <Text style={styles.breakdownButtonText}>📊 View & Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.reassignButton} onPress={() => openReassign(r)}>
                      <Text style={styles.reassignButtonText}>👤</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.deleteSheetButton} onPress={() => handleDeleteSheet(r)}>
                      <Text style={styles.deleteSheetButtonText}>🗑️</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })
          )}
        </View>

        {/* ── Not Yet Scanned ─────────────────────── */}
        {notScanned.length > 0 && (
          <View style={styles.notScannedSection}>
            <View style={styles.notScannedHeader}>
              <Text style={styles.notScannedTitle}>⏳ Not Yet Scanned</Text>
              <View style={styles.notScannedCount}>
                <Text style={styles.notScannedCountText}>{notScanned.length}</Text>
              </View>
            </View>
            <Text style={styles.notScannedSubtitle}>
              These enrolled students have no answer sheet for this assessment yet.
            </Text>
            {notScanned.map(e => (
              <View key={e.studentId} style={styles.notScannedCard}>
                <View style={styles.notScannedAvatar}>
                  <Text style={styles.notScannedAvatarText}>
                    {(e.studentName ?? '?').charAt(0).toUpperCase()}
                  </Text>
                </View>
                <View style={styles.notScannedInfo}>
                  <Text style={styles.notScannedName}>{e.studentName ?? 'Unknown'}</Text>
                  <Text style={styles.notScannedId}>
                    {e.schoolId ? `ID: ${e.schoolId}` : '⚠️ No school ID on record'}
                  </Text>
                </View>
                <View style={styles.notScannedBadge}>
                  <Text style={styles.notScannedBadgeText}>Not scanned</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>

      {/* ── Reassign Student ID Modal ──────────────── */}
      <Modal
        visible={reassignModalVisible}
        transparent
        animationType="slide"
        onRequestClose={closeReassign}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Reassign Student ID</Text>

            {reassignTarget && (
              <View style={styles.infoBox}>
                <Text style={styles.infoName}>
                  {reassignTarget.matchedStudentName ?? 'Unknown Student'}
                </Text>
                <Text style={styles.infoSub}>Current ID: {reassignTarget.studentId}</Text>
              </View>
            )}

            <Text style={styles.fieldLabel}>New Student ID</Text>
            <View style={styles.inputRow}>
              <TextInput
                style={[styles.textInput, { flex: 1, marginBottom: 0 }]}
                value={newStudentId}
                onChangeText={t => {
                  setNewStudentId(t);
                  setIdValidated(false);
                  setIdValidation(null);
                }}
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
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={closeReassign}
                disabled={savingReassign}
              >
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

      {/* ── Delete Sheet Confirmation Modal ──────── */}
      <Modal
        visible={deleteTarget !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setDeleteTarget(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>🗑️ Delete Answer Sheet</Text>

            {deleteTarget && (
              <View style={styles.deleteWarningBox}>
                <Text style={styles.deleteWarningTitle}>
                  {deleteTarget.matchedStudentName ?? 'Unknown Student'}
                </Text>
                <Text style={styles.deleteWarningSub}>ID: {deleteTarget.studentId}</Text>
                <Text style={styles.deleteWarningDesc}>
                  This will permanently delete the student's scanned answer sheet, their score, and all question breakdown data for this assessment.{'\n\n'}This action cannot be undone.
                </Text>
              </View>
            )}

            <View style={[styles.modalButtons, { marginTop: 8 }]}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.saveBtn, { backgroundColor: '#ef4444' }]}
                onPress={confirmDeleteSheet}
                disabled={deleting}
              >
                {deleting
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.saveBtnText}>Delete</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Export Modal ──────────────────────────── */}
      <Modal
        visible={exportModalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setExportModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>📥 Export to Excel</Text>

            <View style={styles.exportInfoBox}>
              <Text style={styles.exportInfoText}>
                {results.length} scanned · {notScanned.length} not scanned
              </Text>
              <Text style={styles.exportInfoSub}>
                Not-scanned students will be included at the bottom.
              </Text>
            </View>

            <Text style={styles.fieldLabel}>Sort Order</Text>

            <TouchableOpacity
              style={[styles.sortOption, exportSortOrder === 'firstName' && styles.sortOptionSelected]}
              onPress={() => setExportSortOrder('firstName')}
            >
              <View style={[styles.sortRadio, exportSortOrder === 'firstName' && styles.sortRadioSelected]} />
              <Text style={[styles.sortOptionText, exportSortOrder === 'firstName' && styles.sortOptionTextSelected]}>
                Alphabetical by First Name
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.sortOption, exportSortOrder === 'lastName' && styles.sortOptionSelected]}
              onPress={() => setExportSortOrder('lastName')}
            >
              <View style={[styles.sortRadio, exportSortOrder === 'lastName' && styles.sortRadioSelected]} />
              <Text style={[styles.sortOptionText, exportSortOrder === 'lastName' && styles.sortOptionTextSelected]}>
                Alphabetical by Last Name
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.sortOption, exportSortOrder === 'studentId' && styles.sortOptionSelected]}
              onPress={() => setExportSortOrder('studentId')}
            >
              <View style={[styles.sortRadio, exportSortOrder === 'studentId' && styles.sortRadioSelected]} />
              <Text style={[styles.sortOptionText, exportSortOrder === 'studentId' && styles.sortOptionTextSelected]}>
                By Student ID (Numeric)
              </Text>
            </TouchableOpacity>

            <View style={[styles.modalButtons, { marginTop: 20 }]}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setExportModalVisible(false)}
                disabled={exporting}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.saveBtn, { backgroundColor: '#16a34a' }]}
                onPress={handleExport}
                disabled={exporting}
              >
                {exporting
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.saveBtnText}>Download</Text>
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

  header: {
    backgroundColor: '#171443', paddingHorizontal: 24,
    paddingVertical: 24, borderBottomWidth: 1, borderBottomColor: '#2a2060',
  },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#ffffff', marginBottom: 4 },
  headerUid: { fontSize: 12, color: '#94a3b8', fontFamily: 'monospace', marginBottom: 16 },
  statsRow: { flexDirection: 'row', gap: 8 },
  statBox: {
    flex: 1, backgroundColor: '#2a2060', borderRadius: 10,
    paddingVertical: 12, alignItems: 'center',
  },
  statNum: { fontSize: 18, fontWeight: 'bold', color: '#22c55e', marginBottom: 2 },
  statLbl: { fontSize: 10, color: '#cdd5df', textAlign: 'center' },
  warningBanner: {
    marginTop: 12, backgroundColor: '#fef3c7',
    borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8,
  },
  warningBannerText: { fontSize: 12, color: '#92400e', lineHeight: 18 },

  listSection: { padding: 16, paddingBottom: 0 },
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
  unmatchedBadge: {
    backgroundColor: '#fef3c7', paddingHorizontal: 5, paddingVertical: 1, borderRadius: 4,
  },
  unmatchedText: { fontSize: 12 },
  schoolId: { fontSize: 13, color: '#64748b', fontFamily: 'monospace', marginBottom: 2 },
  checkedAt: { fontSize: 11, color: '#94a3b8' },
  scoreDisplay: { alignItems: 'flex-end', minWidth: 64 },
  scorePct: { fontSize: 28, fontWeight: 'bold' },
  scoreGrade: { fontSize: 14, fontWeight: '600' },
  pendingBadge: {
    backgroundColor: '#fef3c7', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6,
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
    flex: 2, backgroundColor: '#dbeafe',
    paddingVertical: 10, borderRadius: 8, alignItems: 'center',
  },
  breakdownButtonText: { fontSize: 14, fontWeight: '600', color: '#2563eb' },
  reassignButton: {
    flex: 1, backgroundColor: '#f1f5f9',
    paddingVertical: 10, borderRadius: 8, alignItems: 'center',
  },
  reassignButtonText: { fontSize: 13, fontWeight: '600', color: '#475569' },

  // Not yet scanned section
  notScannedSection: {
    margin: 16, marginTop: 8,
    backgroundColor: '#ffffff', borderRadius: 14, padding: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 6, elevation: 2,
  },
  notScannedHeader: {
    flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6,
  },
  notScannedTitle: { fontSize: 16, fontWeight: 'bold', color: '#1e293b' },
  notScannedCount: {
    backgroundColor: '#fee2e2', paddingHorizontal: 8,
    paddingVertical: 2, borderRadius: 12,
  },
  notScannedCountText: { fontSize: 13, fontWeight: '700', color: '#dc2626' },
  notScannedSubtitle: {
    fontSize: 12, color: '#94a3b8', marginBottom: 12, lineHeight: 18,
  },
  notScannedCard: {
    flexDirection: 'row', alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1, borderTopColor: '#f1f5f9',
  },
  notScannedAvatar: {
    width: 38, height: 38, borderRadius: 19,
    backgroundColor: '#e0e7ff', justifyContent: 'center',
    alignItems: 'center', marginRight: 12,
  },
  notScannedAvatarText: { fontSize: 16, fontWeight: 'bold', color: '#6366f1' },
  notScannedInfo: { flex: 1 },
  notScannedName: { fontSize: 14, fontWeight: '600', color: '#1e293b', marginBottom: 2 },
  notScannedId: { fontSize: 12, color: '#64748b', fontFamily: 'monospace' },
  notScannedBadge: {
    backgroundColor: '#f1f5f9', paddingHorizontal: 8,
    paddingVertical: 3, borderRadius: 6,
  },
  notScannedBadgeText: { fontSize: 11, color: '#94a3b8', fontWeight: '600' },

  // Modal
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
  validateBtn: {
    backgroundColor: '#6366f1', paddingVertical: 14,
    paddingHorizontal: 14, borderRadius: 8,
  },
  validateBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },

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

  // Delete sheet button
  deleteSheetButton: {
    backgroundColor: '#fee2e2', paddingVertical: 10,
    paddingHorizontal: 14, borderRadius: 8, alignItems: 'center',
  },
  deleteSheetButtonText: { fontSize: 16 },

  // Delete warning
  deleteWarningBox: {
    backgroundColor: '#fef2f2', borderRadius: 10,
    borderLeftWidth: 4, borderLeftColor: '#ef4444',
    padding: 14, marginBottom: 8,
  },
  deleteWarningTitle: { fontSize: 15, fontWeight: '700', color: '#1e293b', marginBottom: 2 },
  deleteWarningSub: { fontSize: 12, color: '#64748b', fontFamily: 'monospace', marginBottom: 10 },
  deleteWarningDesc: { fontSize: 13, color: '#7f1d1d', lineHeight: 20 },
  exportButton: {
    marginTop: 14,
    backgroundColor: '#16a34a',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  exportButtonText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#ffffff',
  },
  exportInfoBox: {
    backgroundColor: '#f0fdf4',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  exportInfoText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#166534',
    marginBottom: 2,
  },
  exportInfoSub: {
    fontSize: 12,
    color: '#16a34a',
  },
  sortOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: '#e2e8f0',
    marginBottom: 10,
    backgroundColor: '#ffffff',
    gap: 12,
  },
  sortOptionSelected: {
    borderColor: '#16a34a',
    backgroundColor: '#f0fdf4',
  },
  sortRadio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: '#cbd5e1',
  },
  sortRadioSelected: {
    borderColor: '#16a34a',
    backgroundColor: '#16a34a',
  },
  sortOptionText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#475569',
  },
  sortOptionTextSelected: {
    color: '#166534',
    fontWeight: '600',
  },
});

export default ViewScoresScreen;