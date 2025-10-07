// src/screens/teacher/DashboardScreen.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Modal,
  TextInput,
  ActivityIndicator,
  RefreshControl
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../contexts/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';
import {
  createSection,
  getTeacherSections,
  updateSection,
  deleteSection,
  Section
} from '../../services/sectionService';
import { updateTeacherProfile } from '../../services/authService';

const DashboardScreen: React.FC = () => {
  const { user, signOut } = useAuth();
  
  // State for Profile Modal
  const [profileModalVisible, setProfileModalVisible] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  
  // State for Create Section Modal
  const [createSectionModalVisible, setCreateSectionModalVisible] = useState(false);
  const [newSectionYear, setNewSectionYear] = useState('');
  const [newSectionName, setNewSectionName] = useState('');
  
  // State for Edit Section Modal
  const [editSectionModalVisible, setEditSectionModalVisible] = useState(false);
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [editSectionYear, setEditSectionYear] = useState('');
  const [editSectionName, setEditSectionName] = useState('');
  
  // State for Edit Profile
  const [editFullName, setEditFullName] = useState(user?.fullName || '');
  const [editUsername, setEditUsername] = useState(user?.username || '');
  const [editEmployeeId, setEditEmployeeId] = useState(
    user?.role === 'teacher' ? user.employeeId : ''
  );
  
  // State for Sections
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  
  const totalSections = sections.length;

  // Load sections on mount
  useEffect(() => {
    if (user?.uid) {
      loadSections();
    }
  }, [user?.uid]);

  const loadSections = async () => {
    if (!user?.uid) return;
    
    try {
      setLoading(true);
      const fetchedSections = await getTeacherSections(user.uid);
      setSections(fetchedSections);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadSections();
    setRefreshing(false);
  };

  const handleSignOut = async () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        {
          text: 'Cancel',
          style: 'cancel'
        },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: async () => {
            try {
              await signOut();
            } catch (error: any) {
              Alert.alert('Error', error.message);
            }
          }
        }
      ]
    );
  };

  const handleOpenProfile = () => {
    setEditFullName(user?.fullName || '');
    setEditUsername(user?.username || '');
    setEditEmployeeId(user?.role === 'teacher' ? user.employeeId : '');
    setIsEditing(false);
    setProfileModalVisible(true);
  };

  const handleCloseProfile = () => {
    setProfileModalVisible(false);
    setIsEditing(false);
  };

  const handleSaveProfile = async () => {
    if (!user?.uid) return;

    try {
      setActionLoading(true);
      
      await updateTeacherProfile(user.uid, {
        fullName: editFullName,
        username: editUsername,
        employeeId: editEmployeeId
      });

      Alert.alert('Success', 'Profile updated successfully!');
      setIsEditing(false);
      setProfileModalVisible(false);
      
      // Note: Changes will show after app restart or you can reload user context
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateSection = () => {
    setNewSectionYear('');
    setNewSectionName('');
    setCreateSectionModalVisible(true);
  };

  const handleConfirmCreateSection = async () => {
    if (!user?.uid) return;
    
    if (!newSectionYear.trim() || !newSectionName.trim()) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    try {
      setActionLoading(true);
      
      const newSection = await createSection({
        year: newSectionYear,
        sectionName: newSectionName,
        teacherId: user.uid
      });

      setSections([newSection, ...sections]);
      setCreateSectionModalVisible(false);
      Alert.alert('Success', `Section ${newSectionYear}-${newSectionName} created!`);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelCreateSection = () => {
    setNewSectionYear('');
    setNewSectionName('');
    setCreateSectionModalVisible(false);
  };

  const handleEditSection = (section: Section) => {
    setEditingSectionId(section.id);
    setEditSectionYear(section.year);
    setEditSectionName(section.sectionName);
    setEditSectionModalVisible(true);
  };

  const handleConfirmEditSection = async () => {
    if (!user?.uid || !editingSectionId) return;
    
    if (!editSectionYear.trim() || !editSectionName.trim()) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    try {
      setActionLoading(true);
      
      await updateSection(user.uid, editingSectionId, {
        year: editSectionYear,
        sectionName: editSectionName
      });

      // Update local state
      setSections(sections.map(section => 
        section.id === editingSectionId
          ? { 
              ...section, 
              year: editSectionYear.trim(), 
              sectionName: editSectionName.trim(),
              updatedAt: Date.now()
            }
          : section
      ));

      setEditSectionModalVisible(false);
      Alert.alert('Success', 'Section updated successfully!');
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelEditSection = () => {
    setEditingSectionId(null);
    setEditSectionYear('');
    setEditSectionName('');
    setEditSectionModalVisible(false);
  };

  const handleDeleteSection = (section: Section) => {
    Alert.alert(
      'Delete Section',
      `Are you sure you want to delete ${section.year}-${section.sectionName}?\n\nThis action cannot be undone.`,
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
              
              await deleteSection(user.uid, section.id);
              
              // Update local state
              setSections(sections.filter(s => s.id !== section.id));
              
              Alert.alert('Success', 'Section deleted successfully!');
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

  const handleSectionPress = (section: Section) => {
    // TODO: Navigate to section details
    Alert.alert(
      `${section.year}-${section.sectionName}`,
      `This section has ${section.subjectCount} subjects\n\nCreated: ${new Date(section.createdAt).toLocaleDateString()}`
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#22c55e" />
          <Text style={styles.loadingText}>Loading sections...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <ScrollView 
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Welcome back,</Text>
            <TouchableOpacity onPress={handleOpenProfile} activeOpacity={0.7}>
              <Text style={styles.userName}>{user?.fullName}</Text>
            </TouchableOpacity>
            <Text style={styles.sectionDetails}>
              {totalSections} {totalSections === 1 ? 'section' : 'sections'}
            </Text>
          </View>
          <TouchableOpacity 
            style={styles.signOutButton}
            onPress={handleSignOut}
          >
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>

        {/* Manage Sections */}
        <View style={styles.manageSections}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Your Sections</Text>
            <TouchableOpacity 
              style={styles.createButton}
              onPress={handleCreateSection}
              disabled={actionLoading}
            >
              <Text style={styles.createButtonText}>+ Create Section</Text>
            </TouchableOpacity>
          </View>

          {sections.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateIcon}>📚</Text>
              <Text style={styles.emptyStateText}>No sections yet</Text>
              <Text style={styles.emptyStateSubtext}>Create your first section to get started</Text>
            </View>
          ) : (
            sections.map((section) => (
              <View key={section.id} style={styles.sectionCard}>
                <TouchableOpacity 
                  style={styles.sectionCardContent}
                  onPress={() => handleSectionPress(section)}
                  activeOpacity={0.7}
                  disabled={actionLoading}
                >
                  <View>
                    <Text style={styles.sectionCardTitle}>
                      {section.year}-{section.sectionName}
                    </Text>
                    <Text style={styles.sectionCardDetails}>
                      {section.subjectCount} {section.subjectCount === 1 ? 'subject' : 'subjects'}
                    </Text>
                  </View>
                </TouchableOpacity>
                
                {/* Action Buttons */}
                <View style={styles.sectionCardActions}>
                  <TouchableOpacity 
                    style={styles.editButton}
                    onPress={() => handleEditSection(section)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.editButtonText}>✏️ Edit</Text>
                  </TouchableOpacity>
                  <TouchableOpacity 
                    style={styles.deleteButton}
                    onPress={() => handleDeleteSection(section)}
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

      {/* Profile Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={profileModalVisible}
        onRequestClose={handleCloseProfile}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Profile Information</Text>
              <View style={styles.modalActions}>
                {!isEditing ? (
                  <>
                    <TouchableOpacity 
                      style={styles.iconButton}
                      onPress={() => setIsEditing(true)}
                      disabled={actionLoading}
                    >
                      <Text style={styles.iconButtonText}>✏️ Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity 
                      style={styles.iconButton}
                      onPress={handleCloseProfile}
                      disabled={actionLoading}
                    >
                      <Text style={styles.iconButtonText}>✕ Close</Text>
                    </TouchableOpacity>
                  </>
                ) : (
                  <>
                    <TouchableOpacity 
                      style={[styles.iconButton, styles.saveButton]}
                      onPress={handleSaveProfile}
                      disabled={actionLoading}
                    >
                      {actionLoading ? (
                        <ActivityIndicator size="small" color="#ffffff" />
                      ) : (
                        <Text style={[styles.iconButtonText, styles.saveButtonText]}>
                          ✓ Save
                        </Text>
                      )}
                    </TouchableOpacity>
                    <TouchableOpacity 
                      style={styles.iconButton}
                      onPress={() => setIsEditing(false)}
                      disabled={actionLoading}
                    >
                      <Text style={styles.iconButtonText}>✕ Cancel</Text>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            </View>

            <ScrollView style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Full Name</Text>
                {isEditing ? (
                  <TextInput
                    style={styles.modalInput}
                    value={editFullName}
                    onChangeText={setEditFullName}
                    placeholder="Enter full name"
                    editable={!actionLoading}
                  />
                ) : (
                  <Text style={styles.modalValue}>{user?.fullName}</Text>
                )}
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Email</Text>
                <Text style={[styles.modalValue, styles.readOnlyValue]}>
                  {user?.email}
                </Text>
                {isEditing && (
                  <Text style={styles.helpText}>Email cannot be changed</Text>
                )}
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Username</Text>
                {isEditing ? (
                  <TextInput
                    style={styles.modalInput}
                    value={editUsername}
                    onChangeText={setEditUsername}
                    placeholder="Enter username"
                    autoCapitalize="none"
                    editable={!actionLoading}
                  />
                ) : (
                  <Text style={styles.modalValue}>{user?.username}</Text>
                )}
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Employee ID</Text>
                {isEditing ? (
                  <TextInput
                    style={styles.modalInput}
                    value={editEmployeeId}
                    onChangeText={setEditEmployeeId}
                    placeholder="Enter employee ID"
                    editable={!actionLoading}
                  />
                ) : (
                  <Text style={styles.modalValue}>
                    {user?.role === 'teacher' ? user.employeeId : 'N/A'}
                  </Text>
                )}
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Role</Text>
                <Text style={[styles.modalValue, styles.readOnlyValue]}>
                  {user?.role}
                </Text>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Create Section Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={createSectionModalVisible}
        onRequestClose={handleCancelCreateSection}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Create New Section</Text>
            </View>

            <View style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Year Level</Text>
                <TextInput
                  style={styles.modalInput}
                  value={newSectionYear}
                  onChangeText={setNewSectionYear}
                  placeholder="e.g., 12"
                  keyboardType="numeric"
                  maxLength={2}
                  editable={!actionLoading}
                />
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Section Name</Text>
                <TextInput
                  style={styles.modalInput}
                  value={newSectionName}
                  onChangeText={setNewSectionName}
                  placeholder="e.g., Heart"
                  autoCapitalize="words"
                  editable={!actionLoading}
                />
              </View>

              <View style={styles.createSectionActions}>
                <TouchableOpacity 
                  style={styles.cancelButton}
                  onPress={handleCancelCreateSection}
                  disabled={actionLoading}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={styles.confirmButton}
                  onPress={handleConfirmCreateSection}
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

      {/* Edit Section Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={editSectionModalVisible}
        onRequestClose={handleCancelEditSection}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit Section</Text>
            </View>

            <View style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Year Level</Text>
                <TextInput
                  style={styles.modalInput}
                  value={editSectionYear}
                  onChangeText={setEditSectionYear}
                  placeholder="e.g., 12"
                  keyboardType="numeric"
                  maxLength={2}
                  editable={!actionLoading}
                />
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Section Name</Text>
                <TextInput
                  style={styles.modalInput}
                  value={editSectionName}
                  onChangeText={setEditSectionName}
                  placeholder="e.g., Heart"
                  autoCapitalize="words"
                  editable={!actionLoading}
                />
              </View>

              <View style={styles.createSectionActions}>
                <TouchableOpacity 
                  style={styles.cancelButton}
                  onPress={handleCancelEditSection}
                  disabled={actionLoading}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={styles.confirmButton}
                  onPress={handleConfirmEditSection}
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
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  scrollView: {
    flex: 1
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 20,
    backgroundColor: '#171443',
    borderBottomWidth: 1,
    borderBottomColor: '#2a2060'
  },
  greeting: {
    fontSize: 16,
    color: '#cdd5df'
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginTop: 4,
    textDecorationLine: 'underline'
  },
  sectionDetails: {
    fontSize: 14,
    color: '#cdd5df',
    marginTop: 2
  },
  signOutButton: {
    backgroundColor: '#fee2e2',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8
  },
  signOutText: {
    color: '#dc2626',
    fontWeight: '600',
    fontSize: 14
  },
  manageSections: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 24
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16
  },
  sectionTitle: {
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
  sectionCard: {
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
  sectionCardContent: {
    padding: 20
  },
  sectionCardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4
  },
  sectionCardDetails: {
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
  modalActions: {
    flexDirection: 'row',
    gap: 8
  },
  iconButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: '#f1f5f9'
  },
  iconButtonText: {
    fontSize: 14,
    color: '#475569',
    fontWeight: '600'
  },
  saveButton: {
    backgroundColor: '#22c55e'
  },
  saveButtonText: {
    color: '#ffffff'
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
  modalValue: {
    fontSize: 16,
    color: '#1e293b',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#f8fafc',
    borderRadius: 8
  },
  readOnlyValue: {
    color: '#64748b',
    fontStyle: 'italic'
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
  helpText: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 4,
    fontStyle: 'italic'
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

export default DashboardScreen;