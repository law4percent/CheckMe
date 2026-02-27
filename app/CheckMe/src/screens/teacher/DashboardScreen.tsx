// src/screens/teacher/DashboardScreen.tsx
import React, { useState, useEffect, useRef } from 'react';
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
  RefreshControl,
  Clipboard,
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
import { updateTeacherProfile, generateTempCode, isEmployeeIdTaken } from '../../services/authService';
import { deleteSectionCascade } from '../../services/assessmentService';
import { RootStackParamList } from '../../types';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<RootStackParamList, 'TeacherDashboard'>;

const TEMP_CODE_DURATION = 30; // seconds

const DashboardScreen: React.FC<Props> = ({ navigation }) => {
  const { user, signOut } = useAuth();

  // ── Sections ────────────────────────────────
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // ── Profile Modal ────────────────────────────
  const [profileModalVisible, setProfileModalVisible] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editFullName, setEditFullName] = useState(user?.fullName || '');
  const [editUsername, setEditUsername] = useState(user?.username || '');
  const [editEmployeeId, setEditEmployeeId] = useState(
    user?.role === 'teacher' ? user.employeeId : ''
  );

  // ── Create Section Modal ─────────────────────
  const [createSectionModalVisible, setCreateSectionModalVisible] = useState(false);
  const [newSectionYear, setNewSectionYear] = useState('');
  const [newSectionName, setNewSectionName] = useState('');

  // ── Edit Section Modal ───────────────────────
  const [editSectionModalVisible, setEditSectionModalVisible] = useState(false);
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [editSectionYear, setEditSectionYear] = useState('');
  const [editSectionName, setEditSectionName] = useState('');

  // ── Section Details Modal ────────────────────
  const [sectionDetailsModalVisible, setSectionDetailsModalVisible] = useState(false);
  const [selectedSectionForDetails, setSelectedSectionForDetails] = useState<Section | null>(null);

  // ── Delete confirmation modal ────────────────
  const [deleteSectionTarget, setDeleteSectionTarget] = useState<Section | null>(null);

  // ── Generate Code ────────────────────────────
  const [codeModalVisible, setCodeModalVisible] = useState(false);
  const [tempCode, setTempCode] = useState<string | null>(null);
  const [codeSecondsLeft, setCodeSecondsLeft] = useState(TEMP_CODE_DURATION);
  const [codeGenerating, setCodeGenerating] = useState(false);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const totalSections = sections.length;

  // ── Load sections ────────────────────────────
  useEffect(() => {
    if (user?.uid) loadSections();
  }, [user?.uid]);

  // ── Cleanup countdown on unmount ─────────────
  useEffect(() => {
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, []);

  const loadSections = async () => {
    if (!user?.uid) return;
    try {
      setLoading(true);
      const fetched = await getTeacherSections(user.uid);
      setSections(fetched);
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

  // ── Sign Out ─────────────────────────────────
  const handleSignOut = async () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
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
    ]);
  };

  // ── Profile ──────────────────────────────────
  const handleOpenProfile = () => {
    setEditFullName(user?.fullName || '');
    setEditUsername(user?.username || '');
    setEditEmployeeId(user?.role === 'teacher' ? user.employeeId : '');
    setIsEditing(false);
    setProfileModalVisible(true);
  };

  const handleSaveProfile = async () => {
    if (!user?.uid) return;

    const currentEmployeeId = user.role === 'teacher' ? user.employeeId : '';
    const newEmployeeId = editEmployeeId.trim();

    // Only check for duplicates if the employee ID actually changed
    if (newEmployeeId.toUpperCase() !== currentEmployeeId.trim().toUpperCase()) {
      try {
        setActionLoading(true);
        const taken = await isEmployeeIdTaken(newEmployeeId);
        if (taken) {
          Alert.alert(
            'Employee ID Already in Use',
            `The Employee ID "${newEmployeeId}" is already registered to another account.\n\nPlease use a different Employee ID or contact your school administrator.`
          );
          setActionLoading(false);
          return;
        }
      } catch {
        // Non-critical — proceed if check fails
      }
    }

    try {
      setActionLoading(true);
      await updateTeacherProfile(user.uid, {
        fullName: editFullName,
        username: editUsername,
        employeeId: newEmployeeId,
      });
      Alert.alert('Success', 'Profile updated successfully!');
      setIsEditing(false);
      setProfileModalVisible(false);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Generate Code ─────────────────────────────
  const startCountdown = () => {
    if (countdownRef.current) clearInterval(countdownRef.current);

    setCodeSecondsLeft(TEMP_CODE_DURATION);

    countdownRef.current = setInterval(() => {
      setCodeSecondsLeft(prev => {
        if (prev <= 1) {
          clearInterval(countdownRef.current!);
          countdownRef.current = null;
          setTempCode(null); // code expired — clear display
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleOpenCodeModal = () => {
    setTempCode(null);
    setCodeSecondsLeft(TEMP_CODE_DURATION);
    if (countdownRef.current) clearInterval(countdownRef.current);
    setCodeModalVisible(true);
  };

  const handleCloseCodeModal = () => {
    if (countdownRef.current) clearInterval(countdownRef.current);
    setTempCode(null);
    setCodeSecondsLeft(TEMP_CODE_DURATION);
    setCodeModalVisible(false);
  };

  const handleGenerateCode = async () => {
    if (!user?.uid || !user?.username) return;

    try {
      setCodeGenerating(true);

      // Stop any existing countdown before generating new code
      if (countdownRef.current) clearInterval(countdownRef.current);

      const code = await generateTempCode(user.uid, user.username);
      setTempCode(code);
      startCountdown();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to generate code');
    } finally {
      setCodeGenerating(false);
    }
  };

  const handleCopyCode = () => {
    if (!tempCode) return;
    Clipboard.setString(tempCode);
    Alert.alert('Copied!', 'Login code copied to clipboard');
  };

  // ── Sections CRUD ─────────────────────────────
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
      setSections(sections.map(s =>
        s.id === editingSectionId
          ? { ...s, year: editSectionYear.trim(), sectionName: editSectionName.trim(), updatedAt: Date.now() }
          : s
      ));
      setEditSectionModalVisible(false);
      Alert.alert('Success', 'Section updated successfully!');
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteSection = (section: Section) => {
    setDeleteSectionTarget(section);
  };

  const confirmDeleteSection = async () => {
    if (!deleteSectionTarget || !user?.uid) return;
    try {
      setActionLoading(true);
      // Cascade: all subjects + assessments + answer keys + sheets + enrollments + section
      await deleteSectionCascade(user.uid, deleteSectionTarget.id);
      setSections(sections.filter(s => s.id !== deleteSectionTarget.id));
      setDeleteSectionTarget(null);
      Alert.alert('Deleted', 'Section and all related data removed.');
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSectionPress = (section: Section) => {
    navigation.navigate('TeacherSectionDashboard', { section });
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  const handleCopyToClipboard = (text: string, label: string) => {
    Clipboard.setString(text);
    Alert.alert('Copied!', `${label} copied to clipboard`);
  };

  // ── Countdown color ───────────────────────────
  const countdownColor =
    codeSecondsLeft > 15 ? '#22c55e' :
    codeSecondsLeft > 5  ? '#f59e0b' : '#ef4444';

  // ── Loading screen ────────────────────────────
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

  // ── Render ────────────────────────────────────
  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={styles.greeting}>Welcome back,</Text>
            <TouchableOpacity onPress={handleOpenProfile} activeOpacity={0.7}>
              <Text style={styles.userName}>{user?.fullName}</Text>
            </TouchableOpacity>
            <Text style={styles.sectionDetails}>
              {totalSections} {totalSections === 1 ? 'section' : 'sections'}
            </Text>
          </View>

          <View style={styles.headerRight}>
            {/* Generate Code Button */}
            <TouchableOpacity
              style={styles.generateCodeButton}
              onPress={handleOpenCodeModal}
            >
              <Text style={styles.generateCodeButtonText}>🔑 Raspi Login</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut}>
              <Text style={styles.signOutText}>Sign Out</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Sections */}
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
            sections.map(section => (
              <View key={section.id} style={styles.sectionCard}>
                <TouchableOpacity
                  style={styles.sectionCardContent}
                  onPress={() => handleSectionPress(section)}
                  activeOpacity={0.7}
                  disabled={actionLoading}
                >
                  <View style={styles.sectionCardContentRow}>
                    <View style={styles.sectionCardInfo}>
                      <Text style={styles.sectionCardTitle}>
                        {section.year}-{section.sectionName}
                      </Text>
                      <Text style={styles.sectionCardDetails}>
                        {section.subjectCount} {section.subjectCount === 1 ? 'subject' : 'subjects'}
                      </Text>
                    </View>
                    <TouchableOpacity
                      style={styles.detailIconButton}
                      onPress={() => {
                        setSelectedSectionForDetails(section);
                        setSectionDetailsModalVisible(true);
                      }}
                      disabled={actionLoading}
                    >
                      <Text style={styles.detailIconText}>ℹ️</Text>
                    </TouchableOpacity>
                  </View>
                </TouchableOpacity>

                <View style={styles.sectionCardActions}>
                  <TouchableOpacity
                    style={styles.iconActionBtn}
                    onPress={() => handleEditSection(section)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.iconActionText}>✏️</Text>
                  </TouchableOpacity>
                  <View style={styles.iconActionDivider} />
                  <TouchableOpacity
                    style={styles.iconActionBtnDanger}
                    onPress={() => handleDeleteSection(section)}
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

      {/* Loading Overlay */}
      {actionLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#22c55e" />
        </View>
      )}

      {/* ── Generate Code Modal ─────────────────── */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={codeModalVisible}
        onRequestClose={handleCloseCodeModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Raspi Login Code</Text>
              <TouchableOpacity style={styles.iconButton} onPress={handleCloseCodeModal}>
                <Text style={styles.iconButtonText}>✕ Close</Text>
              </TouchableOpacity>
            </View>

            <View style={[styles.modalBody, styles.codeModalBody]}>
              <Text style={styles.codeInstructions}>
                Generate a one-time 8-digit code to log in to the Raspberry Pi device.
                The code expires in <Text style={{ fontWeight: 'bold' }}>30 seconds</Text>.
              </Text>

              {tempCode ? (
                <>
                  {/* Code display */}
                  <View style={styles.codeDisplayContainer}>
                    <Text style={styles.codeDisplayText}>{tempCode}</Text>
                  </View>

                  {/* Countdown ring */}
                  <View style={styles.countdownContainer}>
                    <Text style={[styles.countdownText, { color: countdownColor }]}>
                      {codeSecondsLeft}s
                    </Text>
                    <Text style={styles.countdownLabel}>remaining</Text>
                  </View>

                  {/* Expired message */}
                  {codeSecondsLeft === 0 && (
                    <Text style={styles.expiredText}>Code expired. Generate a new one.</Text>
                  )}

                  {/* Action buttons */}
                  <View style={styles.codeActions}>
                    <TouchableOpacity
                      style={[styles.copyCodeButton, codeSecondsLeft === 0 && styles.disabledButton]}
                      onPress={handleCopyCode}
                      disabled={codeSecondsLeft === 0}
                    >
                      <Text style={styles.copyCodeButtonText}>📋 Copy Code</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.regenerateButton}
                      onPress={handleGenerateCode}
                      disabled={codeGenerating}
                    >
                      {codeGenerating ? (
                        <ActivityIndicator color="#ffffff" size="small" />
                      ) : (
                        <Text style={styles.regenerateButtonText}>🔄 New Code</Text>
                      )}
                    </TouchableOpacity>
                  </View>
                </>
              ) : (
                /* No code yet — show generate button */
                <TouchableOpacity
                  style={styles.generateButton}
                  onPress={handleGenerateCode}
                  disabled={codeGenerating}
                >
                  <LinearGradient
                    colors={['#6366f1', '#8b5cf6']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradientButton}
                  >
                    {codeGenerating ? (
                      <ActivityIndicator color="#ffffff" />
                    ) : (
                      <Text style={styles.generateButtonText}>🔑 Generate Code</Text>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
              )}
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Profile Modal ────────────────────────── */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={profileModalVisible}
        onRequestClose={() => setProfileModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Profile Information</Text>
              <View style={styles.modalActions}>
                {!isEditing ? (
                  <>
                    <TouchableOpacity style={styles.iconButton} onPress={() => setIsEditing(true)} disabled={actionLoading}>
                      <Text style={styles.iconButtonText}>✏️ Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.iconButton} onPress={() => setProfileModalVisible(false)} disabled={actionLoading}>
                      <Text style={styles.iconButtonText}>✕ Close</Text>
                    </TouchableOpacity>
                  </>
                ) : (
                  <>
                    <TouchableOpacity style={[styles.iconButton, styles.saveButton]} onPress={handleSaveProfile} disabled={actionLoading}>
                      {actionLoading
                        ? <ActivityIndicator size="small" color="#ffffff" />
                        : <Text style={[styles.iconButtonText, styles.saveButtonText]}>✓ Save</Text>
                      }
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.iconButton} onPress={() => setIsEditing(false)} disabled={actionLoading}>
                      <Text style={styles.iconButtonText}>✕ Cancel</Text>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            </View>

            <ScrollView style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Full Name</Text>
                {isEditing
                  ? <TextInput style={styles.modalInput} value={editFullName} onChangeText={setEditFullName} placeholder="Enter full name" editable={!actionLoading} />
                  : <Text style={styles.modalValue}>{user?.fullName}</Text>
                }
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Email</Text>
                <Text style={[styles.modalValue, styles.readOnlyValue]}>{user?.email}</Text>
                {isEditing && <Text style={styles.helpText}>Email cannot be changed</Text>}
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Username</Text>
                {isEditing
                  ? <TextInput style={styles.modalInput} value={editUsername} onChangeText={setEditUsername} placeholder="Enter username" autoCapitalize="none" editable={!actionLoading} />
                  : <Text style={styles.modalValue}>{user?.username}</Text>
                }
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Employee ID</Text>
                {isEditing
                  ? <TextInput style={styles.modalInput} value={editEmployeeId} onChangeText={setEditEmployeeId} placeholder="Enter employee ID" editable={!actionLoading} />
                  : <Text style={styles.modalValue}>{user?.role === 'teacher' ? user.employeeId : 'N/A'}</Text>
                }
              </View>

              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Role</Text>
                <Text style={[styles.modalValue, styles.readOnlyValue]}>{user?.role}</Text>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* ── Create Section Modal ─────────────────── */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={createSectionModalVisible}
        onRequestClose={() => setCreateSectionModalVisible(false)}
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
                <TouchableOpacity style={styles.cancelButton} onPress={() => setCreateSectionModalVisible(false)} disabled={actionLoading}>
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.confirmButton} onPress={handleConfirmCreateSection} disabled={actionLoading}>
                  <LinearGradient colors={['#84cc16', '#22c55e']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.gradientButton}>
                    {actionLoading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.confirmButtonText}>Create</Text>}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Edit Section Modal ───────────────────── */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={editSectionModalVisible}
        onRequestClose={() => setEditSectionModalVisible(false)}
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
                <TouchableOpacity style={styles.cancelButton} onPress={() => setEditSectionModalVisible(false)} disabled={actionLoading}>
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.confirmButton} onPress={handleConfirmEditSection} disabled={actionLoading}>
                  <LinearGradient colors={['#84cc16', '#22c55e']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.gradientButton}>
                    {actionLoading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.confirmButtonText}>Save Changes</Text>}
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Section Details Modal ────────────────── */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={sectionDetailsModalVisible}
        onRequestClose={() => setSectionDetailsModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Section Details</Text>
              <TouchableOpacity style={styles.iconButton} onPress={() => setSectionDetailsModalVisible(false)}>
                <Text style={styles.iconButtonText}>✕ Close</Text>
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.modalBody}>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Section Name</Text>
                <Text style={styles.modalValue}>
                  {selectedSectionForDetails?.year}-{selectedSectionForDetails?.sectionName}
                </Text>
              </View>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Created At</Text>
                <Text style={styles.modalValue}>
                  {selectedSectionForDetails?.createdAt ? formatDate(selectedSectionForDetails.createdAt) : 'N/A'}
                </Text>
              </View>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Section ID (UID)</Text>
                <View style={styles.uidContainer}>
                  <Text style={[styles.modalValue, styles.monoValue, styles.uidText]}>
                    {selectedSectionForDetails?.id}
                  </Text>
                  <TouchableOpacity
                    style={styles.copyButton}
                    onPress={() => handleCopyToClipboard(selectedSectionForDetails?.id || '', 'Section ID')}
                  >
                    <Text style={styles.copyButtonText}>📋 Copy</Text>
                  </TouchableOpacity>
                </View>
              </View>
              <View style={styles.modalField}>
                <Text style={styles.modalLabel}>Teacher ID (UID)</Text>
                <View style={styles.uidContainer}>
                  <Text style={[styles.modalValue, styles.monoValue, styles.uidText]}>
                    {selectedSectionForDetails?.teacherId}
                  </Text>
                  <TouchableOpacity
                    style={styles.copyButton}
                    onPress={() => handleCopyToClipboard(selectedSectionForDetails?.teacherId || '', 'Teacher ID')}
                  >
                    <Text style={styles.copyButtonText}>📋 Copy</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* ── Delete Section Confirmation Modal ─────── */}
      <Modal
        visible={deleteSectionTarget !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setDeleteSectionTarget(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.deleteModalContent}>
            <Text style={styles.deleteModalTitle}>⚠️ Delete Section</Text>

            {deleteSectionTarget && (
              <View style={styles.deleteWarningBox}>
                <Text style={styles.deleteWarningName}>
                  {deleteSectionTarget.year}-{deleteSectionTarget.sectionName}
                </Text>
                <Text style={styles.deleteWarningDesc}>
                  Deleting this section will permanently remove:
                </Text>
                <View style={styles.deleteConsequenceList}>
                  <Text style={styles.deleteConsequenceItem}>• All subjects in this section</Text>
                  <Text style={styles.deleteConsequenceItem}>• All assessments (quizzes and exams)</Text>
                  <Text style={styles.deleteConsequenceItem}>• All scanned answer keys</Text>
                  <Text style={styles.deleteConsequenceItem}>• All student answer sheets and scores</Text>
                  <Text style={styles.deleteConsequenceItem}>• All student enrollments</Text>
                </View>
                <Text style={styles.deleteWarningNote}>This action cannot be undone.</Text>
              </View>
            )}

            <View style={styles.deleteModalButtons}>
              <TouchableOpacity
                style={styles.deleteCancelBtn}
                onPress={() => setDeleteSectionTarget(null)}
                disabled={actionLoading}
              >
                <Text style={styles.deleteCancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.deleteConfirmBtn}
                onPress={confirmDeleteSection}
                disabled={actionLoading}
              >
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
    backgroundColor: 'rgba(0,0,0,0.3)', justifyContent: 'center', alignItems: 'center'
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
  headerLeft: { flex: 1 },
  headerRight: { alignItems: 'flex-end', gap: 8 },
  greeting: { fontSize: 16, color: '#cdd5df' },
  userName: { fontSize: 24, fontWeight: 'bold', color: '#ffffff', marginTop: 4, textDecorationLine: 'underline' },
  sectionDetails: { fontSize: 14, color: '#cdd5df', marginTop: 2 },
  generateCodeButton: {
    backgroundColor: '#6366f1',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8
  },
  generateCodeButtonText: { color: '#ffffff', fontWeight: '600', fontSize: 13 },
  signOutButton: { backgroundColor: '#fee2e2', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  signOutText: { color: '#dc2626', fontWeight: '600', fontSize: 14 },
  manageSections: { paddingHorizontal: 24, paddingTop: 24, paddingBottom: 24 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  sectionTitle: { fontSize: 22, fontWeight: 'bold', color: '#1e293b' },
  createButton: { backgroundColor: '#22c55e', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  createButtonText: { color: '#ffffff', fontWeight: '600', fontSize: 14 },
  emptyState: { alignItems: 'center', justifyContent: 'center', paddingVertical: 40 },
  emptyStateIcon: { fontSize: 48, marginBottom: 16 },
  emptyStateText: { fontSize: 18, color: '#64748b', fontWeight: '600', marginBottom: 8 },
  emptyStateSubtext: { fontSize: 14, color: '#94a3b8' },
  sectionCard: {
    backgroundColor: '#ffffff', borderRadius: 12, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2, overflow: 'hidden'
  },
  sectionCardContent: { padding: 20 },
  sectionCardContentRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sectionCardInfo: { flex: 1 },
  detailIconButton: { padding: 8, marginLeft: 8 },
  detailIconText: { fontSize: 20 },
  sectionCardTitle: { fontSize: 18, fontWeight: '600', color: '#1e293b', marginBottom: 4 },
  sectionCardDetails: { fontSize: 14, color: '#64748b' },
  sectionCardActions: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: '#f1f5f9', justifyContent: 'flex-end' },
  iconActionBtn: { paddingVertical: 10, paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center', backgroundColor: '#eff6ff' },
  iconActionBtnDanger: { paddingVertical: 10, paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fef2f2' },
  iconActionText: { fontSize: 18 },
  iconActionDivider: { width: 1, backgroundColor: '#f1f5f9' },
  // Delete modal
  deleteModalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, width: '100%', maxWidth: 420, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 10, elevation: 10 },
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

  // ── Code Modal ───────────────────────────────
  codeModalBody: { alignItems: 'center', paddingVertical: 24 },
  codeInstructions: { fontSize: 14, color: '#475569', textAlign: 'center', marginBottom: 24, lineHeight: 22 },
  codeDisplayContainer: {
    backgroundColor: '#171443',
    paddingHorizontal: 32,
    paddingVertical: 20,
    borderRadius: 16,
    marginBottom: 20,
    borderWidth: 2,
    borderColor: '#6366f1'
  },
  codeDisplayText: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#ffffff',
    letterSpacing: 8,
    fontFamily: 'monospace'
  },
  countdownContainer: { alignItems: 'center', marginBottom: 16 },
  countdownText: { fontSize: 36, fontWeight: 'bold' },
  countdownLabel: { fontSize: 14, color: '#64748b', marginTop: 2 },
  expiredText: { fontSize: 14, color: '#ef4444', fontWeight: '600', marginBottom: 16 },
  codeActions: { flexDirection: 'row', gap: 12, width: '100%' },
  copyCodeButton: {
    flex: 1, backgroundColor: '#dbeafe', paddingVertical: 14,
    borderRadius: 10, alignItems: 'center'
  },
  copyCodeButtonText: { fontSize: 15, fontWeight: '600', color: '#2563eb' },
  disabledButton: { opacity: 0.4 },
  regenerateButton: {
    flex: 1, backgroundColor: '#6366f1', paddingVertical: 14,
    borderRadius: 10, alignItems: 'center'
  },
  regenerateButtonText: { fontSize: 15, fontWeight: '600', color: '#ffffff' },
  generateButton: { width: '100%', borderRadius: 12, overflow: 'hidden', marginTop: 8 },
  generateButtonText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },

  // ── Modal shared ─────────────────────────────
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center', alignItems: 'center', padding: 20
  },
  modalContent: {
    backgroundColor: '#ffffff', borderRadius: 20,
    width: '100%', maxWidth: 500, maxHeight: '80%',
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3, shadowRadius: 10, elevation: 10
  },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: 20, paddingBottom: 15,
    borderBottomWidth: 1, borderBottomColor: '#e2e8f0'
  },
  modalTitle: { fontSize: 22, fontWeight: 'bold', color: '#1e293b' },
  modalActions: { flexDirection: 'row', gap: 8 },
  iconButton: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6, backgroundColor: '#f1f5f9' },
  iconButtonText: { fontSize: 14, color: '#475569', fontWeight: '600' },
  saveButton: { backgroundColor: '#22c55e' },
  saveButtonText: { color: '#ffffff' },
  modalBody: { padding: 20 },
  modalField: { marginBottom: 20 },
  modalLabel: { fontSize: 14, fontWeight: '600', color: '#475569', marginBottom: 8 },
  modalValue: { fontSize: 16, color: '#1e293b', paddingVertical: 12, paddingHorizontal: 16, backgroundColor: '#f8fafc', borderRadius: 8 },
  readOnlyValue: { color: '#64748b', fontStyle: 'italic' },
  modalInput: {
    fontSize: 16, color: '#1e293b', paddingVertical: 12, paddingHorizontal: 16,
    backgroundColor: '#ffffff', borderRadius: 8, borderWidth: 1, borderColor: '#e2e8f0'
  },
  helpText: { fontSize: 12, color: '#94a3b8', marginTop: 4, fontStyle: 'italic' },
  monoValue: { fontFamily: 'monospace', fontSize: 12 },
  uidContainer: { flexDirection: 'column', gap: 8 },
  uidText: { flex: 1 },
  copyButton: { backgroundColor: '#22c55e', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 6, alignItems: 'center' },
  copyButtonText: { color: '#ffffff', fontWeight: '600', fontSize: 14 },
  createSectionActions: { flexDirection: 'row', gap: 12, marginTop: 20 },
  cancelButton: { flex: 1, paddingVertical: 14, borderRadius: 10, backgroundColor: '#f1f5f9', alignItems: 'center' },
  cancelButtonText: { fontSize: 16, fontWeight: '600', color: '#475569' },
  confirmButton: { flex: 1, borderRadius: 10, overflow: 'hidden' },
  gradientButton: { paddingVertical: 14, alignItems: 'center', justifyContent: 'center' },
  confirmButtonText: { fontSize: 16, fontWeight: '600', color: '#ffffff' },
});

export default DashboardScreen;