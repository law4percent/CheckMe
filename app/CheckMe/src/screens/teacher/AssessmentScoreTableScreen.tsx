// src/screens/teacher/AssessmentScoreTableScreen.tsx
import React, { useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
  FlatList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, QuestionBreakdown } from '../../types';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherAssessmentScoreTable'>;

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const IMAGE_WIDTH = SCREEN_WIDTH - 48; // full-width with padding

const AssessmentScoreTableScreen: React.FC<Props> = ({ route }) => {
  const { result, assessmentName } = route.params;
  const flatListRef = useRef<FlatList>(null);

  // Sort breakdown keys Q1, Q2 ... Qn numerically
  const questionKeys = Object.keys(result.breakdown).sort((a, b) => {
    const numA = parseInt(a.replace(/\D/g, ''), 10);
    const numB = parseInt(b.replace(/\D/g, ''), 10);
    return numA - numB;
  });

  const pct =
    result.total_questions > 0
      ? Math.round((result.total_score / result.total_questions) * 100)
      : 0;

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

  const resultIcon = (checking_result: boolean | 'pending') => {
    if (checking_result === 'pending') return { icon: '⏳', color: '#f59e0b', label: 'Pending' };
    if (checking_result === true) return { icon: '✓', color: '#22c55e', label: 'Correct' };
    return { icon: '✗', color: '#ef4444', label: 'Wrong' };
  };

  const displayName = result.matchedStudentName ?? 'Unknown Student';
  const color = scoreColor(pct);

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView style={styles.scrollView}>

        {/* ── Student summary header ───────────────── */}
        <View style={styles.header}>
          <View style={styles.headerTop}>
            <View style={styles.headerInfo}>
              <Text style={styles.studentName}>{displayName}</Text>
              <Text style={styles.schoolId}>ID: {result.studentId}</Text>
              {!result.matchedStudentName && (
                <View style={styles.unmatchedBadge}>
                  <Text style={styles.unmatchedText}>⚠️ Unmatched ID</Text>
                </View>
              )}
              <Text style={styles.assessmentLabel}>{assessmentName}</Text>
            </View>

            <View style={styles.scoreCircle}>
              <Text style={[styles.scoreCirclePct, { color }]}>{pct}%</Text>
              <Text style={[styles.scoreCircleGrade, { color }]}>{gradeLabel(pct)}</Text>
            </View>
          </View>

          <View style={styles.scoreSummaryRow}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryNum}>{result.total_score}</Text>
              <Text style={styles.summaryLbl}>Score</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryItem}>
              <Text style={styles.summaryNum}>{result.total_questions}</Text>
              <Text style={styles.summaryLbl}>Total</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryItem}>
              <Text style={styles.summaryNum}>
                {questionKeys.filter(k => result.breakdown[k]?.checking_result === true).length}
              </Text>
              <Text style={styles.summaryLbl}>Correct</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryItem}>
              <Text style={[styles.summaryNum, { color: '#ef4444' }]}>
                {questionKeys.filter(k => result.breakdown[k]?.checking_result === false).length}
              </Text>
              <Text style={styles.summaryLbl}>Wrong</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryItem}>
              <Text style={[styles.summaryNum, { color: '#f59e0b' }]}>
                {questionKeys.filter(k => result.breakdown[k]?.checking_result === 'pending').length}
              </Text>
              <Text style={styles.summaryLbl}>Pending</Text>
            </View>
          </View>

          {!result.is_final_score && (
            <View style={styles.pendingBanner}>
              <Text style={styles.pendingBannerText}>
                ⏳ Score is pending — essay questions have not yet been graded
              </Text>
            </View>
          )}
        </View>

        {/* ── Cloudinary image gallery ─────────────── */}
        {result.image_urls.length > 0 && (
          <View style={styles.gallerySection}>
            <Text style={styles.sectionTitle}>
              📷 Answer Sheet Images ({result.image_urls.length})
            </Text>
            <FlatList
              ref={flatListRef}
              data={result.image_urls}
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
                    Page {index + 1} of {result.image_urls.length}
                  </Text>
                </View>
              )}
              snapToInterval={IMAGE_WIDTH + 12}
              decelerationRate="fast"
            />
          </View>
        )}

        {/* ── Per-question breakdown ───────────────── */}
        <View style={styles.breakdownSection}>
          <Text style={styles.sectionTitle}>
            📝 Question Breakdown
          </Text>

          {/* Table header */}
          <View style={styles.tableHeader}>
            <Text style={[styles.thCell, styles.colQ]}>Q</Text>
            <Text style={[styles.thCell, styles.colAnswer]}>Student Answer</Text>
            <Text style={[styles.thCell, styles.colAnswer]}>Correct Answer</Text>
            <Text style={[styles.thCell, styles.colResult]}>Result</Text>
          </View>

          {questionKeys.length === 0 ? (
            <View style={styles.emptyBreakdown}>
              <Text style={styles.emptyBreakdownText}>No breakdown data available</Text>
            </View>
          ) : (
            questionKeys.map((key, index) => {
              const entry: QuestionBreakdown = result.breakdown[key];
              const { icon, color: resultColor, label } = resultIcon(entry.checking_result);
              const isEven = index % 2 === 0;

              return (
                <View
                  key={key}
                  style={[
                    styles.tableRow,
                    isEven ? styles.tableRowEven : styles.tableRowOdd,
                    entry.checking_result === true && styles.tableRowCorrect,
                    entry.checking_result === false && styles.tableRowWrong,
                    entry.checking_result === 'pending' && styles.tableRowPending,
                  ]}
                >
                  <Text style={[styles.tdCell, styles.colQ, styles.qLabel]}>{key}</Text>
                  <Text
                    style={[
                      styles.tdCell,
                      styles.colAnswer,
                      entry.checking_result === false && styles.wrongAnswer,
                    ]}
                    numberOfLines={2}
                  >
                    {entry.student_answer || '—'}
                  </Text>
                  <Text style={[styles.tdCell, styles.colAnswer, styles.correctAnswerText]} numberOfLines={2}>
                    {entry.correct_answer || '—'}
                  </Text>
                  <View style={[styles.colResult, styles.resultCell]}>
                    <Text style={[styles.resultIcon, { color: resultColor }]}>{icon}</Text>
                    <Text style={[styles.resultLabel, { color: resultColor }]}>{label}</Text>
                  </View>
                </View>
              );
            })
          )}
        </View>

        {/* ── Metadata footer ──────────────────────── */}
        <View style={styles.metaSection}>
          <Text style={styles.metaTitle}>Scan Details</Text>
          <View style={styles.metaRow}>
            <Text style={styles.metaKey}>Checked by</Text>
            <Text style={styles.metaVal}>{result.checked_by || '—'}</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaKey}>Checked at</Text>
            <Text style={styles.metaVal}>
              {result.checked_at
                ? new Date(result.checked_at).toLocaleString()
                : '—'}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaKey}>Last updated</Text>
            <Text style={styles.metaVal}>
              {result.updated_at
                ? new Date(result.updated_at).toLocaleString()
                : '—'}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaKey}>Final score</Text>
            <Text style={[styles.metaVal, { color: result.is_final_score ? '#22c55e' : '#f59e0b', fontWeight: '700' }]}>
              {result.is_final_score ? 'Yes' : 'No (Pending)'}
            </Text>
          </View>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
};

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
    borderRadius: 12, paddingVertical: 12,
  },
  summaryItem: { flex: 1, alignItems: 'center' },
  summaryNum: { fontSize: 18, fontWeight: 'bold', color: '#ffffff', marginBottom: 2 },
  summaryLbl: { fontSize: 10, color: '#94a3b8' },
  summaryDivider: { width: 1, backgroundColor: '#475569', marginVertical: 4 },
  pendingBanner: {
    marginTop: 12, backgroundColor: '#fef3c7',
    borderRadius: 8, padding: 10,
  },
  pendingBannerText: { fontSize: 13, color: '#92400e', fontWeight: '600' },

  // Gallery
  gallerySection: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 8 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#1e293b', marginBottom: 12 },
  imageWrapper: {
    width: IMAGE_WIDTH,
    marginRight: 12,
    backgroundColor: '#1e293b',
    borderRadius: 12,
    overflow: 'hidden',
  },
  sheetImage: { width: IMAGE_WIDTH, height: IMAGE_WIDTH * 1.35 },
  imagePageLabel: {
    textAlign: 'center', color: '#94a3b8', fontSize: 12,
    paddingVertical: 8, backgroundColor: '#1e293b',
  },

  // Breakdown table
  breakdownSection: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 8 },
  tableHeader: {
    flexDirection: 'row', backgroundColor: '#1e293b',
    paddingVertical: 10, paddingHorizontal: 8,
    borderTopLeftRadius: 8, borderTopRightRadius: 8,
  },
  thCell: { fontSize: 12, fontWeight: '700', color: '#ffffff' },
  tableRow: {
    flexDirection: 'row', paddingVertical: 10,
    paddingHorizontal: 8, alignItems: 'center',
    borderBottomWidth: 1, borderBottomColor: '#e2e8f0',
  },
  tableRowEven: { backgroundColor: '#ffffff' },
  tableRowOdd: { backgroundColor: '#f8fafc' },
  tableRowCorrect: { borderLeftWidth: 3, borderLeftColor: '#22c55e' },
  tableRowWrong: { borderLeftWidth: 3, borderLeftColor: '#ef4444' },
  tableRowPending: { borderLeftWidth: 3, borderLeftColor: '#f59e0b' },
  tdCell: { fontSize: 13, color: '#1e293b' },
  colQ: { width: 36, fontWeight: '700', color: '#6366f1' },
  colAnswer: { flex: 1, paddingHorizontal: 6 },
  colResult: { width: 64 },
  qLabel: { fontFamily: 'monospace' },
  wrongAnswer: { color: '#ef4444', textDecorationLine: 'line-through' },
  correctAnswerText: { color: '#16a34a', fontWeight: '600' },
  resultCell: { alignItems: 'center' },
  resultIcon: { fontSize: 16, fontWeight: 'bold' },
  resultLabel: { fontSize: 10, fontWeight: '600', marginTop: 1 },
  emptyBreakdown: {
    backgroundColor: '#ffffff', paddingVertical: 32,
    alignItems: 'center', borderBottomLeftRadius: 8, borderBottomRightRadius: 8,
  },
  emptyBreakdownText: { fontSize: 14, color: '#94a3b8' },

  // Meta footer
  metaSection: {
    marginHorizontal: 24, marginVertical: 20,
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
  metaVal: { fontSize: 13, color: '#1e293b', fontWeight: '500', maxWidth: '60%', textAlign: 'right' },
});

export default AssessmentScoreTableScreen;