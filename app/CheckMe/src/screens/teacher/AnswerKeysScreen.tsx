// src/screens/teacher/AnswerKeysScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator,
  RefreshControl, TouchableOpacity, Alert, TextInput, Modal,
  Image, Dimensions, FlatList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import {
  getAnswerKeysForSubject,
  updateAnswerKeyAnswer,
  deleteAnswerKey,
  rescoreAnswerSheets,
  getAnswerSheetCount,
  AnswerKeyListItem,
  AnswerKeyEntry,
} from '../../services/answerSheetService';

type Props = NativeStackScreenProps<RootStackParamList, 'AnswerKeys'>;

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const formatDate = (ts: number) => {
  if (!ts) return '—';
  return new Date(ts).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

const answerBadgeColor = (answer: string) => {
  if (answer === 'essay_answer')      return { bg: '#ede9fe', text: '#7c3aed' };
  if (answer === 'missing_question')  return { bg: '#fee2e2', text: '#b91c1c' };
  if (answer === 'unreadable')        return { bg: '#fef3c7', text: '#b45309' };
  if (answer === 'missing_answer')    return { bg: '#f1f5f9', text: '#94a3b8' };
  return { bg: '#dcfce7', text: '#166534' };
};

const AnswerKeysScreen: React.FC<Props> = ({ route }) => {
  const { teacherUid, subjectUid, subjectName } = route.params;

  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [items, setItems]           = useState<AnswerKeyListItem[]>([]);
  const [expandedUid, setExpandedUid] = useState<string | null>(null);

  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingKey, setEditingKey]             = useState<AnswerKeyEntry | null>(null);
  const [editingQuestion, setEditingQuestion]   = useState<string>('');
  const [editingOldAnswer, setEditingOldAnswer] = useState<string>('');
  const [editAnswer, setEditAnswer]             = useState<string>('');
  const [savingEdit, setSavingEdit]             = useState(false);

  const [imageModalVisible, setImageModalVisible] = useState(false);
  const [imageModalUrls, setImageModalUrls]       = useState<string[]>([]);
  const [imageModalIndex, setImageModalIndex]     = useState(0);

  const loadItems = useCallback(async () => {
    try {
      const data = await getAnswerKeysForSubject(teacherUid, subjectUid);
      setItems(data);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to load answer keys');
    }
  }, [teacherUid, subjectUid]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await loadItems();
      setLoading(false);
    })();
  }, [loadItems]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadItems();
    setRefreshing(false);
  };

  const handleDelete = async (entry: AnswerKeyEntry) => {
    const sheetCount = await getAnswerSheetCount(teacherUid, entry.assessmentUid);
    let msg =
      `Delete the answer key for "${entry.assessmentName}" (${entry.assessmentUid})?\n\n` +
      `This cannot be undone. You will need to re-scan the answer key paper with the Raspi.`;
    if (sheetCount > 0) {
      msg += `\n\n⚠️ ${sheetCount} student answer sheet${sheetCount > 1 ? 's' : ''} exist under this assessment. ` +
        `Deleting the key does NOT delete those sheets, but scores will no longer have a key to compare against.`;
    }
    Alert.alert('🗑️ Delete Answer Key', msg, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          try {
            await deleteAnswerKey(teacherUid, entry.assessmentUid);
            await loadItems();
            if (expandedUid === entry.assessmentUid) setExpandedUid(null);
            Alert.alert('Deleted', `Answer key for "${entry.assessmentName}" removed.`);
          } catch (error: any) {
            Alert.alert('Error', error.message || 'Failed to delete answer key');
          }
        },
      },
    ]);
  };

  const openEditAnswer = (entry: AnswerKeyEntry, questionKey: string) => {
    setEditingKey(entry);
    setEditingQuestion(questionKey);
    setEditingOldAnswer(entry.answers[questionKey] ?? '');
    setEditAnswer(entry.answers[questionKey] ?? '');
    setEditModalVisible(true);
  };

  const closeEditAnswer = () => {
    setEditModalVisible(false);
    setEditingKey(null);
    setEditingQuestion('');
    setEditingOldAnswer('');
    setEditAnswer('');
  };

  const handleSaveAnswer = async () => {
    if (!editingKey) return;
    const trimmed = editAnswer.trim();
    if (!trimmed) { Alert.alert('Invalid', 'Answer cannot be empty.'); return; }
    if (trimmed === editingOldAnswer) { closeEditAnswer(); return; }

    const sheetCount = await getAnswerSheetCount(teacherUid, editingKey.assessmentUid);

    const doSave = async (rescore: boolean) => {
      try {
        setSavingEdit(true);
        await updateAnswerKeyAnswer(teacherUid, editingKey.assessmentUid, editingQuestion, trimmed);
        if (rescore && sheetCount > 0) {
          const updatedAnswers = { ...editingKey.answers, [editingQuestion]: trimmed };
          const rescored = await rescoreAnswerSheets(teacherUid, editingKey.assessmentUid, updatedAnswers);
          Alert.alert('Saved & Re-scored',
            `${editingQuestion} updated: "${editingOldAnswer}" → "${trimmed}"\n\n` +
            `${rescored} answer sheet${rescored !== 1 ? 's' : ''} re-scored.`);
        } else {
          Alert.alert('Saved', `${editingQuestion} updated: "${editingOldAnswer}" → "${trimmed}"`);
        }
        closeEditAnswer();
        await loadItems();
      } catch (error: any) {
        Alert.alert('Error', error.message || 'Failed to save answer');
      } finally {
        setSavingEdit(false);
      }
    };

    if (sheetCount > 0) {
      Alert.alert('⚠️ Answer Key Modified',
        `Changing ${editingQuestion} from "${editingOldAnswer}" to "${trimmed}".\n\n` +
        `${sheetCount} student answer sheet${sheetCount > 1 ? 's' : ''} already exist for this assessment.\n\n` +
        `Recommendation: It is safer to re-scan all student answer sheets with the Raspi ` +
        `to ensure accuracy. Auto re-scoring uses the existing OCR data which may have errors.\n\n` +
        `Do you want to automatically re-score existing sheets now?`,
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Save Only',       style: 'default',     onPress: () => doSave(false) },
          { text: 'Save & Re-score', style: 'destructive', onPress: () => doSave(true)  },
        ]
      );
    } else {
      await doSave(false);
    }
  };

  const openImageViewer = (urls: string[], startIndex: number = 0) => {
    setImageModalUrls(urls);
    setImageModalIndex(startIndex);
    setImageModalVisible(true);
  };

  const closeImageViewer = () => {
    setImageModalVisible(false);
    setImageModalUrls([]);
    setImageModalIndex(0);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#22c55e" />
          <Text style={styles.loadingText}>Loading answer keys...</Text>
        </View>
      </SafeAreaView>
    );
  }

  const withKey    = items.filter(i => i.hasAnswerKey).length;
  const withoutKey = items.filter(i => !i.hasAnswerKey).length;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Answer Keys</Text>
          <Text style={styles.headerSubtitle}>{subjectName}</Text>
          <View style={styles.statsRow}>
            <View style={styles.statBox}>
              <Text style={styles.statNum}>{items.length}</Text>
              <Text style={styles.statLbl}>Total</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statNum, { color: '#22c55e' }]}>{withKey}</Text>
              <Text style={styles.statLbl}>Scanned</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={[styles.statNum, { color: '#ef4444' }]}>{withoutKey}</Text>
              <Text style={styles.statLbl}>Missing</Text>
            </View>
          </View>
        </View>

        <View style={styles.listSection}>
          {items.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>🗝️</Text>
              <Text style={styles.emptyTitle}>No assessments yet</Text>
              <Text style={styles.emptySubtitle}>Create an assessment in the subject dashboard first.</Text>
            </View>
          ) : (
            items.map(item => {
              const isExpanded = expandedUid === item.assessmentUid;

              if (!item.hasAnswerKey) {
                return (
                  <View key={item.assessmentUid} style={[styles.card, styles.cardMissing]}>
                    <View style={styles.cardHeader}>
                      <View style={styles.cardTitleGroup}>
                        <Text style={styles.cardName}>{item.assessmentName}</Text>
                        <Text style={styles.cardUid}>{item.assessmentUid}</Text>
                      </View>
                      <View style={styles.missingBadge}>
                        <Text style={styles.missingBadgeText}>❌ Not Scanned</Text>
                      </View>
                    </View>
                    <Text style={styles.missingHint}>
                      Scan this assessment's answer key paper with the Raspi to populate it here.
                    </Text>
                  </View>
                );
              }

              const entry       = item as AnswerKeyEntry;
              const questionKeys = Object.keys(entry.answers);
              const imageUrls   = entry.imageUrls ?? [];
              const hasImages   = imageUrls.length > 0;

              return (
                <View key={entry.assessmentUid} style={styles.card}>
                  <TouchableOpacity
                    style={styles.cardHeader}
                    onPress={() => setExpandedUid(isExpanded ? null : entry.assessmentUid)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.cardTitleGroup}>
                      <Text style={styles.cardName}>{entry.assessmentName}</Text>
                      <Text style={styles.cardUid}>{entry.assessmentUid}</Text>
                      <Text style={styles.cardMeta}>
                        {entry.totalQuestions} questions  ·  Updated {formatDate(entry.updatedAt)}
                      </Text>
                    </View>
                    <View style={styles.cardHeaderRight}>
                      <View style={styles.scannedBadge}>
                        <Text style={styles.scannedBadgeText}>✅ Scanned</Text>
                      </View>
                      {hasImages && (
                        <View style={styles.imageBadge}>
                          <Text style={styles.imageBadgeText}>🖼 {imageUrls.length}</Text>
                        </View>
                      )}
                      <Text style={styles.expandChevron}>{isExpanded ? '▲' : '▼'}</Text>
                    </View>
                  </TouchableOpacity>

                  {isExpanded && (
                    <View style={styles.expandedBody}>

                      {/* Scanned Images */}
                      {hasImages && (
                        <View style={styles.imagesSection}>
                          <Text style={styles.imagesSectionTitle}>📄 Scanned Answer Key Images</Text>
                          <ScrollView
                            horizontal
                            showsHorizontalScrollIndicator={false}
                            contentContainerStyle={styles.imagesScrollContent}
                          >
                            {imageUrls.map((url: string, index: number) => (
                              <TouchableOpacity
                                key={index}
                                style={styles.imageThumbnailWrapper}
                                onPress={() => openImageViewer(imageUrls, index)}
                                activeOpacity={0.8}
                              >
                                <Image
                                  source={{ uri: url }}
                                  style={styles.imageThumbnail}
                                  resizeMode="cover"
                                />
                                <View style={styles.imageThumbnailOverlay}>
                                  <Text style={styles.imageThumbnailLabel}>Page {index + 1}</Text>
                                  <Text style={styles.imageThumbnailZoom}>🔍</Text>
                                </View>
                              </TouchableOpacity>
                            ))}
                          </ScrollView>
                          <Text style={styles.imageTapHint}>Tap an image to view full screen</Text>
                        </View>
                      )}

                      {/* Answer table */}
                      <View style={styles.tableHeader}>
                        <Text style={[styles.tableHeaderCell, styles.colQ]}>Q</Text>
                        <Text style={[styles.tableHeaderCell, styles.colAnswer]}>Correct Answer</Text>
                        <Text style={[styles.tableHeaderCell, styles.colEdit]}>Edit</Text>
                      </View>

                      {questionKeys.map(q => {
                        const answer = entry.answers[q];
                        const badge  = answerBadgeColor(answer);
                        return (
                          <View key={q} style={styles.tableRow}>
                            <Text style={[styles.tableCell, styles.colQ, styles.qLabel]}>{q}</Text>
                            <View style={[styles.tableCell, styles.colAnswer]}>
                              <View style={[styles.answerBadge, { backgroundColor: badge.bg }]}>
                                <Text style={[styles.answerBadgeText, { color: badge.text }]}>{answer}</Text>
                              </View>
                            </View>
                            <View style={[styles.tableCell, styles.colEdit, { alignItems: 'center' }]}>
                              <TouchableOpacity style={styles.editAnswerBtn} onPress={() => openEditAnswer(entry, q)}>
                                <Text style={styles.editAnswerBtnText}>✏️</Text>
                              </TouchableOpacity>
                            </View>
                          </View>
                        );
                      })}

                      {questionKeys.some(q =>
                        ['unreadable', 'missing_question', 'missing_answer'].includes(entry.answers[q])
                      ) && (
                        <View style={styles.flagBanner}>
                          <Text style={styles.flagBannerText}>
                            ⚠️ Some answers are flagged (unreadable / missing). Review and correct them before scanning student sheets.
                          </Text>
                        </View>
                      )}

                      <TouchableOpacity style={styles.deleteKeyBtn} onPress={() => handleDelete(entry)}>
                        <Text style={styles.deleteKeyBtnText}>🗑️ Delete Answer Key</Text>
                      </TouchableOpacity>
                    </View>
                  )}
                </View>
              );
            })
          )}
        </View>
      </ScrollView>

      {/* Edit Answer Modal */}
      <Modal visible={editModalVisible} transparent animationType="slide" onRequestClose={closeEditAnswer}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Answer</Text>
            {editingKey && (
              <View style={styles.modalInfoBox}>
                <Text style={styles.modalInfoName}>{editingKey.assessmentName}</Text>
                <Text style={styles.modalInfoSub}>{editingKey.assessmentUid}  ·  {editingQuestion}</Text>
              </View>
            )}
            <View style={styles.answerCompare}>
              <View style={styles.answerCompareItem}>
                <Text style={styles.compareLabel}>Current</Text>
                <View style={[styles.answerBadge, { backgroundColor: answerBadgeColor(editingOldAnswer).bg }]}>
                  <Text style={[styles.answerBadgeText, { color: answerBadgeColor(editingOldAnswer).text }]}>{editingOldAnswer}</Text>
                </View>
              </View>
              <Text style={styles.compareArrow}>→</Text>
              <View style={styles.answerCompareItem}>
                <Text style={styles.compareLabel}>New</Text>
                <View style={[styles.answerBadge, { backgroundColor: editAnswer ? answerBadgeColor(editAnswer).bg : '#f1f5f9' }]}>
                  <Text style={[styles.answerBadgeText, { color: editAnswer ? answerBadgeColor(editAnswer).text : '#94a3b8' }]}>{editAnswer || '…'}</Text>
                </View>
              </View>
            </View>
            <Text style={styles.fieldLabel}>New Correct Answer</Text>
            <TextInput
              style={styles.textInput}
              value={editAnswer}
              onChangeText={setEditAnswer}
              placeholder="e.g. A, B, TRUE, FALSE, or essay_answer"
              autoCapitalize="characters"
              editable={!savingEdit}
            />
            <View style={styles.modalHints}>
              <Text style={styles.hintText}>Common values: A  B  C  D  TRUE  FALSE  essay_answer</Text>
            </View>
            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.cancelBtn} onPress={closeEditAnswer} disabled={savingEdit}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.saveBtn} onPress={handleSaveAnswer} disabled={savingEdit}>
                {savingEdit ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.saveBtnText}>Save</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Full-screen Image Viewer */}
      <Modal
        visible={imageModalVisible}
        transparent
        animationType="fade"
        onRequestClose={closeImageViewer}
        statusBarTranslucent
      >
        <View style={styles.imageViewerOverlay}>
          <TouchableOpacity style={styles.imageViewerClose} onPress={closeImageViewer}>
            <Text style={styles.imageViewerCloseText}>✕</Text>
          </TouchableOpacity>
          <Text style={styles.imageViewerCounter}>
            {imageModalIndex + 1} / {imageModalUrls.length}
          </Text>
          <FlatList
            data={imageModalUrls}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            initialScrollIndex={imageModalIndex}
            getItemLayout={(_, index) => ({
              length: SCREEN_WIDTH,
              offset: SCREEN_WIDTH * index,
              index,
            })}
            onMomentumScrollEnd={(e) => {
              const index = Math.round(e.nativeEvent.contentOffset.x / SCREEN_WIDTH);
              setImageModalIndex(index);
            }}
            keyExtractor={(_, index) => index.toString()}
            renderItem={({ item: url }) => (
              <View style={styles.imageViewerPage}>
                <Image source={{ uri: url }} style={styles.imageViewerImage} resizeMode="contain" />
              </View>
            )}
          />
          {imageModalUrls.length > 1 && (
            <View style={styles.imageViewerDots}>
              {imageModalUrls.map((_, i) => (
                <View key={i} style={[styles.imageViewerDot, i === imageModalIndex && styles.imageViewerDotActive]} />
              ))}
            </View>
          )}
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
  header: { backgroundColor: '#171443', paddingHorizontal: 24, paddingVertical: 24, borderBottomWidth: 1, borderBottomColor: '#2a2060' },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#ffffff', marginBottom: 2 },
  headerSubtitle: { fontSize: 14, color: '#94a3b8', marginBottom: 16 },
  statsRow: { flexDirection: 'row', gap: 10 },
  statBox: { flex: 1, backgroundColor: '#2a2060', borderRadius: 10, paddingVertical: 12, alignItems: 'center' },
  statNum: { fontSize: 22, fontWeight: 'bold', color: '#22c55e', marginBottom: 2 },
  statLbl: { fontSize: 11, color: '#cdd5df' },
  listSection: { padding: 16 },
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#64748b', marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: '#94a3b8', textAlign: 'center', paddingHorizontal: 32 },
  card: { backgroundColor: '#ffffff', borderRadius: 14, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 6, elevation: 3, overflow: 'hidden' },
  cardMissing: { borderWidth: 1, borderColor: '#fecaca', borderStyle: 'dashed' },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', padding: 16 },
  cardTitleGroup: { flex: 1, marginRight: 12 },
  cardName: { fontSize: 16, fontWeight: 'bold', color: '#1e293b', marginBottom: 2 },
  cardUid: { fontSize: 12, color: '#6366f1', fontFamily: 'monospace', marginBottom: 4 },
  cardMeta: { fontSize: 12, color: '#94a3b8' },
  cardHeaderRight: { alignItems: 'flex-end', gap: 8 },
  scannedBadge: { backgroundColor: '#dcfce7', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  scannedBadgeText: { fontSize: 12, color: '#16a34a', fontWeight: '600' },
  missingBadge: { backgroundColor: '#fee2e2', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  missingBadgeText: { fontSize: 12, color: '#b91c1c', fontWeight: '600' },
  imageBadge: { backgroundColor: '#e0f2fe', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  imageBadgeText: { fontSize: 12, color: '#0369a1', fontWeight: '600' },
  missingHint: { fontSize: 13, color: '#94a3b8', paddingHorizontal: 16, paddingBottom: 16, lineHeight: 18 },
  expandChevron: { fontSize: 12, color: '#94a3b8', marginTop: 4 },
  expandedBody: { borderTopWidth: 1, borderTopColor: '#f1f5f9', paddingHorizontal: 16, paddingBottom: 16 },
  imagesSection: { marginTop: 14, marginBottom: 4 },
  imagesSectionTitle: { fontSize: 13, fontWeight: '700', color: '#475569', marginBottom: 10 },
  imagesScrollContent: { gap: 10, paddingRight: 4 },
  imageThumbnailWrapper: { width: 120, height: 160, borderRadius: 10, overflow: 'hidden', borderWidth: 1, borderColor: '#e2e8f0' },
  imageThumbnail: { width: '100%', height: '100%' },
  imageThumbnailOverlay: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: 'rgba(0,0,0,0.45)', paddingHorizontal: 8, paddingVertical: 5, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  imageThumbnailLabel: { fontSize: 11, color: '#ffffff', fontWeight: '600' },
  imageThumbnailZoom: { fontSize: 13 },
  imageTapHint: { fontSize: 11, color: '#94a3b8', marginTop: 6, fontStyle: 'italic' },
  tableHeader: { flexDirection: 'row', backgroundColor: '#f8fafc', borderRadius: 8, paddingVertical: 8, paddingHorizontal: 4, marginTop: 12, marginBottom: 4 },
  tableHeaderCell: { fontSize: 12, fontWeight: '700', color: '#475569' },
  tableRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6, paddingHorizontal: 4, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  tableCell: { justifyContent: 'center' },
  colQ: { width: 44 },
  colAnswer: { flex: 1 },
  colEdit: { width: 44 },
  qLabel: { fontSize: 14, fontWeight: '600', color: '#475569' },
  answerBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6, alignSelf: 'flex-start' },
  answerBadgeText: { fontSize: 13, fontWeight: '600' },
  editAnswerBtn: { backgroundColor: '#f1f5f9', padding: 6, borderRadius: 6, alignItems: 'center' },
  editAnswerBtnText: { fontSize: 15 },
  flagBanner: { marginTop: 12, backgroundColor: '#fef3c7', borderRadius: 8, borderLeftWidth: 4, borderLeftColor: '#f59e0b', paddingHorizontal: 12, paddingVertical: 8 },
  flagBannerText: { fontSize: 12, color: '#92400e', lineHeight: 18 },
  deleteKeyBtn: { marginTop: 14, backgroundColor: '#fef2f2', paddingVertical: 12, borderRadius: 8, alignItems: 'center', borderWidth: 1, borderColor: '#fecaca' },
  deleteKeyBtnText: { fontSize: 14, fontWeight: '600', color: '#dc2626' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.55)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  modalContent: { backgroundColor: '#ffffff', borderRadius: 16, padding: 24, width: '100%', maxWidth: 400 },
  modalTitle: { fontSize: 20, fontWeight: 'bold', color: '#1e293b', marginBottom: 16, textAlign: 'center' },
  modalInfoBox: { backgroundColor: '#f8fafc', borderRadius: 10, padding: 12, marginBottom: 16 },
  modalInfoName: { fontSize: 15, fontWeight: '600', color: '#1e293b', marginBottom: 2 },
  modalInfoSub: { fontSize: 12, color: '#64748b', fontFamily: 'monospace' },
  answerCompare: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12, marginBottom: 16 },
  answerCompareItem: { alignItems: 'center', gap: 4 },
  compareLabel: { fontSize: 11, color: '#94a3b8', fontWeight: '600' },
  compareArrow: { fontSize: 20, color: '#cbd5e1', marginTop: 16 },
  fieldLabel: { fontSize: 14, fontWeight: '600', color: '#475569', marginBottom: 8 },
  textInput: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8, paddingHorizontal: 14, paddingVertical: 12, fontSize: 16, color: '#1e293b', marginBottom: 8 },
  modalHints: { backgroundColor: '#f8fafc', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, marginBottom: 16 },
  hintText: { fontSize: 12, color: '#64748b' },
  modalButtons: { flexDirection: 'row', gap: 12 },
  cancelBtn: { flex: 1, paddingVertical: 13, borderRadius: 8, backgroundColor: '#f1f5f9', alignItems: 'center' },
  cancelBtnText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  saveBtn: { flex: 1, paddingVertical: 13, borderRadius: 8, backgroundColor: '#22c55e', alignItems: 'center' },
  saveBtnText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },
  imageViewerOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.95)', justifyContent: 'center', alignItems: 'center' },
  imageViewerClose: { position: 'absolute', top: 52, right: 20, zIndex: 10, backgroundColor: 'rgba(255,255,255,0.15)', width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  imageViewerCloseText: { color: '#ffffff', fontSize: 18, fontWeight: 'bold' },
  imageViewerCounter: { position: 'absolute', top: 60, alignSelf: 'center', zIndex: 10, color: '#ffffff', fontSize: 14, fontWeight: '600', opacity: 0.8 },
  imageViewerPage: { width: SCREEN_WIDTH, height: SCREEN_HEIGHT, justifyContent: 'center', alignItems: 'center', paddingVertical: 80, paddingHorizontal: 12 },
  imageViewerImage: { width: '100%', height: '100%' },
  imageViewerDots: { position: 'absolute', bottom: 48, flexDirection: 'row', gap: 8, alignSelf: 'center' },
  imageViewerDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.35)' },
  imageViewerDotActive: { backgroundColor: '#ffffff', width: 20 },
});

export default AnswerKeysScreen;