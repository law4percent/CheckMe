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

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherSectionSubject'>;

const SectionSubjectScreen: React.FC<Props> = ({ route, navigation }) => {
  const { section } = route.params;
  const { user } = useAuth();

  // State for subjects
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // State for Create Subject Modal
  const [createSubjectModalVisible, setCreateSubjectModalVisible] = useState(false);
  const [newSubjectName, setNewSubjectName] = useState('');

  // State for Edit Subject Modal
  const [editSubjectModalVisible, setEditSubjectModalVisible] = useState(false);
  const [editingSubjectId, setEditingSubjectId] = useState<string | null>(null);
  const [editSubjectName, setEditSubjectName] = useState('');

  // Load subjects on mount
  useEffect(() => {
    if (user?.uid && section.id) {
      loadSubjects();
    }
  }, [user?.uid, section.id]);

  const loadSubjects = async () => {
    if (!user?.uid) return;

    try {
      setLoading(true);
      const fetchedSubjects = await getSectionSubjects(user.uid, section.id);
      setSubjects(fetchedSubjects);
      
      // Update section's subject count if it differs
      if (fetchedSubjects.length !== section.subjectCount) {
        await updateSectionSubjectCount(user.uid, section.id, fetchedSubjects.length);
      }
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

  const handleCreateSubject = () => {
    setNewSubjectName('');
    setCreateSubjectModalVisible(true);
  };

  const handleConfirmCreateSubject = async () => {
    if (!user?.uid) return;

    if (!newSubjectName.trim()) {
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
      });

      setSubjects([newSubject, ...subjects]);
      
      // Update section's subject count
      await updateSectionSubjectCount(user.uid, section.id, subjects.length + 1);

      setCreateSubjectModalVisible(false);
      Alert.alert('Success', `Subject "${newSubjectName}" created!`);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelCreateSubject = () => {
    setNewSubjectName('');
    setCreateSubjectModalVisible(false);
  };

  const handleEditSubject = (subject: Subject) => {
    setEditingSubjectId(subject.id);
    setEditSubjectName(subject.subjectName);
    setEditSubjectModalVisible(true);
  };

  const handleConfirmEditSubject = async () => {
    if (!user?.uid || !editingSubjectId) return;

    if (!editSubjectName.trim()) {
      Alert.alert('Error', 'Please enter a subject name');
      return;
    }

    try {
      setActionLoading(true);

      await updateSubject(user.uid, section.id, editingSubjectId, {
        subjectName: editSubjectName,
      });

      // Update local state
      setSubjects(subjects.map(subject =>
        subject.id === editingSubjectId
          ? {
              ...subject,
              subjectName: editSubjectName.trim(),
              updatedAt: Date.now()
            }
          : subject
      ));

      setEditSubjectModalVisible(false);
      Alert.alert('Success', 'Subject updated successfully!');
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelEditSubject = () => {
    setEditingSubjectId(null);
    setEditSubjectName('');
    setEditSubjectModalVisible(false);
  };

  const handleDeleteSubject = (subject: Subject) => {
    Alert.alert(
      'Delete Subject',
      `Are you sure you want to delete "${subject.subjectName}"?\n\nThis action cannot be undone.`,
      [
        {
          text: 'Cancel',
          style: 'cancel'
        },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            if (!user?.uid) return;

            try {
              setActionLoading(true);

              await deleteSubject(user.uid, section.id, subject.id);

              // Update local state
              const newSubjects = subjects.filter(s => s.id !== subject.id);
              setSubjects(newSubjects);

              // Update section's subject count
              await updateSectionSubjectCount(user.uid, section.id, newSubjects.length);

              Alert.alert('Success', 'Subject deleted successfully!');
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

  const handleSubjectPress = (subject: Subject) => {
    // TODO: Navigate to SubjectDetailScreen (students, attendance, etc.)
    Alert.alert('Coming Soon', `Subject details for "${subject.subjectName}" will be available soon!`);
  };

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
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Section Info Header */}
        <View style={styles.sectionInfoHeader}>
          <Text style={styles.sectionInfoTitle}>
            {section.year}-{section.sectionName}
          </Text>
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
            subjects.map((subject) => (
              <View key={subject.id} style={styles.subjectCard}>
                <TouchableOpacity
                  style={styles.subjectCardContent}
                  onPress={() => handleSubjectPress(subject)}
                  activeOpacity={0.7}
                  disabled={actionLoading}
                >
                  <View>
                    <Text style={styles.subjectCardTitle}>
                      {subject.subjectName}
                    </Text>
                    <Text style={styles.subjectCardDetails}>
                      {subject.studentCount} {subject.studentCount === 1 ? 'enrolled student' : 'enrolled students'}
                    </Text>
                  </View>
                </TouchableOpacity>

                <View style={styles.sectionCardActions}>
                  <TouchableOpacity
                    style={styles.editButton}
                    onPress={() => handleEditSubject(subject)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.editButtonText}>✏️ Edit</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.deleteButton}
                    onPress={() => handleDeleteSubject(subject)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.deleteButtonText}>🗑️ Delete</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      {/* Loading Overlay */}
      {actionLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#22c55e" />
        </View>
      )}

      {/* Create Subject Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={createSubjectModalVisible}
        onRequestClose={handleCancelCreateSubject}
      >
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

              <View style={styles.createSectionActions}>
                <TouchableOpacity
                  style={styles.cancelButton}
                  onPress={handleCancelCreateSubject}
                  disabled={actionLoading}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.confirmButton}
                  onPress={handleConfirmCreateSubject}
                  disabled={actionLoading}
                >
                  <LinearGradient
                    colors={['#84cc16', '#22c55e']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradientButton}
                  >
                    {actionLoading ? (
                      <ActivityIndicator color="#ffffff" />
                    ) : (
                      <Text style={styles.confirmButtonText}>Create</Text>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* Edit Subject Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={editSubjectModalVisible}
        onRequestClose={handleCancelEditSubject}
      >
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

              <View style={styles.createSectionActions}>
                <TouchableOpacity
                  style={styles.cancelButton}
                  onPress={handleCancelEditSubject}
                  disabled={actionLoading}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.confirmButton}
                  onPress={handleConfirmEditSubject}
                  disabled={actionLoading}
                >
                  <LinearGradient
                    colors={['#84cc16', '#22c55e']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradientButton}
                  >
                    {actionLoading ? (
                      <ActivityIndicator color="#ffffff" />
                    ) : (
                      <Text style={styles.confirmButtonText}>Save Changes</Text>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  scrollView: {
    flex: 1
  },
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center'
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#64748b'
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    justifyContent: 'center',
    alignItems: 'center'
  },
  sectionInfoHeader: {
    backgroundColor: '#171443',
    paddingHorizontal: 24,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060'
  },
  sectionInfoTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4
  },
  sectionInfoSubtitle: {
    fontSize: 14,
    color: '#cdd5df'
  },
  manageSections: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 24
  },
  subjectHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16
  },
  subjectTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1e293b'
  },
  createButton: {
    backgroundColor: '#22c55e',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8
  },
  createButtonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 14
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40
  },
  emptyStateIcon: {
    fontSize: 48,
    marginBottom: 16
  },
  emptyStateText: {
    fontSize: 18,
    color: '#64748b',
    fontWeight: '600',
    marginBottom: 8
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#94a3b8'
  },
  subjectCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1
    },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    overflow: 'hidden'
  },
  subjectCardContent: {
    padding: 20
  },
  subjectCardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4
  },
  subjectCardDetails: {
    fontSize: 14,
    color: '#64748b'
  },
  sectionCardActions: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9'
  },
  editButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: '#eff6ff',
    borderRightWidth: 1,
    borderRightColor: '#f1f5f9'
  },
  editButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3b82f6'
  },
  deleteButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: '#fef2f2'
  },
  deleteButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ef4444'
  },
  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderRadius: 20,
    width: '100%',
    maxWidth: 500,
    maxHeight: '80%',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4
    },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 10
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0'
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1e293b'
  },
  modalBody: {
    padding: 20
  },
  modalField: {
    marginBottom: 20
  },
  modalLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 8
  },
  modalInput: {
    fontSize: 16,
    color: '#1e293b',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0'
  },
  createSectionActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    backgroundColor: '#f1f5f9',
    alignItems: 'center'
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#475569'
  },
  confirmButton: {
    flex: 1,
    borderRadius: 10,
    overflow: 'hidden'
  },
  gradientButton: {
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center'
  },
  confirmButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff'
  }
});


export default SectionSubjectScreen;