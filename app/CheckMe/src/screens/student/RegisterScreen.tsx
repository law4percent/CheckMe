// src/screens/student/RegisterScreen.tsx
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
  Image
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import {
  isGmailAddress,
  validatePassword,
  validateUsername
} from '../../utils/validation';
import { isStudentIdTaken } from '../../services/authService';
import { LinearGradient } from 'expo-linear-gradient';

type Props = NativeStackScreenProps<RootStackParamList, 'StudentRegister'>;

const RegisterScreen: React.FC<Props> = ({ navigation }) => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [studentId, setStudentId] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();

  const validateForm = (): string | null => {
    if (!firstName.trim()) return 'First name is required';
    if (!lastName.trim()) return 'Last name is required';
    if (!email.trim()) return 'Email is required';
    if (!isGmailAddress(email)) return 'Only Gmail addresses (@gmail.com) are allowed';

    const usernameCheck = validateUsername(username);
    if (!usernameCheck.isValid) return usernameCheck.message || 'Invalid username';

    if (!studentId.trim()) return 'Student ID is required';
    if (studentId.trim().length < 3) return 'Student ID must be at least 3 characters';

    const passwordCheck = validatePassword(password);
    if (!passwordCheck.isValid) return passwordCheck.message || 'Invalid password';

    if (password !== confirmPassword) return 'Passwords do not match';

    return null;
  };

  const handleRegister = async () => {
    const validationError = validateForm();
    if (validationError) {
      Alert.alert('Validation Error', validationError);
      return;
    }

    try {
      setLoading(true);

      // ── Duplicate school ID check ──────────────
      const taken = await isStudentIdTaken(studentId.trim());
      if (taken) {
        Alert.alert(
          'Student ID Already in Use',
          `The Student ID "${studentId.trim()}" is already registered to another account.\n\nIf you believe this is a mistake, please contact your teacher or school administrator.`
        );
        setLoading(false);
        return;
      }

      await signUp({
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        email: email.trim(),
        password,
        username: username.trim(),
        studentId: studentId.trim(),
      });

      Alert.alert(
        'Success',
        'Account created successfully! Please login with your credentials.',
        [{ text: 'OK', onPress: () => navigation.navigate('StudentLogin') }]
      );
    } catch (error: any) {
      Alert.alert('Registration Failed', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.content}>
            {/* Logo */}
            <View style={styles.logoContainer}>
              <Image
                source={require('../../../assets/checkme-logo.jpg')}
                style={styles.logoImage}
                resizeMode="contain"
              />
              <View style={[styles.dot, styles.dotTopLeft]} />
              <View style={[styles.dot, styles.dotTopRight]} />
              <View style={[styles.dot, styles.dotBottomLeft]} />
              <View style={[styles.dot, styles.dotBottomRight]} />
            </View>

            <Text style={styles.title}>Student Sign Up</Text>

            <View style={styles.form}>
              <TextInput
                style={styles.input}
                placeholder="First Name"
                placeholderTextColor="#94a3b8"
                value={firstName}
                onChangeText={setFirstName}
                autoCapitalize="words"
                editable={!loading}
              />

              <TextInput
                style={styles.input}
                placeholder="Last Name"
                placeholderTextColor="#94a3b8"
                value={lastName}
                onChangeText={setLastName}
                autoCapitalize="words"
                editable={!loading}
              />

              <TextInput
                style={styles.input}
                placeholder="Email (Gmail only)"
                placeholderTextColor="#94a3b8"
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
                editable={!loading}
              />

              <TextInput
                style={styles.input}
                placeholder="Username"
                placeholderTextColor="#94a3b8"
                value={username}
                onChangeText={setUsername}
                autoCapitalize="none"
                editable={!loading}
              />

              {/* Student ID field with note */}
              <View>
                <TextInput
                  style={styles.input}
                  placeholder="Student ID (School-provided)"
                  placeholderTextColor="#94a3b8"
                  value={studentId}
                  onChangeText={setStudentId}
                  keyboardType="numeric"
                  editable={!loading}
                />
                <Text style={styles.fieldHint}>
                  ⚠️ Use the exact ID on your school records. This is used to match your answer sheets.
                </Text>
              </View>

              <TextInput
                style={styles.input}
                placeholder="Password"
                placeholderTextColor="#94a3b8"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
                autoCapitalize="none"
                editable={!loading}
              />

              <TextInput
                style={styles.input}
                placeholder="Confirm Password"
                placeholderTextColor="#94a3b8"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry
                autoCapitalize="none"
                editable={!loading}
              />

              <TouchableOpacity
                style={styles.buttonWrapper}
                onPress={handleRegister}
                disabled={loading}
                activeOpacity={0.8}
              >
                <LinearGradient
                  colors={['#84cc16', '#22c55e']}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.gradientButton}
                >
                  {loading ? (
                    <ActivityIndicator color="#ffffff" />
                  ) : (
                    <Text style={styles.buttonText}>Sign Up</Text>
                  )}
                </LinearGradient>
              </TouchableOpacity>

              <View style={styles.loginContainer}>
                <Text style={styles.loginText}>Already have an account? </Text>
                <TouchableOpacity
                  onPress={() => navigation.navigate('StudentLogin')}
                  disabled={loading}
                >
                  <Text style={styles.loginLink}>Login</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#171443' },
  keyboardView: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: 30 },
  content: { flex: 1, paddingHorizontal: 40, paddingTop: 20, alignItems: 'center' },
  logoContainer: {
    position: 'relative', marginBottom: 30,
    alignItems: 'center', width: 150, height: 150
  },
  logoImage: { width: '100%', height: '100%' },
  dot: {
    position: 'absolute', width: 8, height: 8,
    borderRadius: 4, backgroundColor: '#22c55e'
  },
  dotTopLeft: { top: 10, left: 10 },
  dotTopRight: { top: 10, right: 10 },
  dotBottomLeft: { bottom: 10, left: 10 },
  dotBottomRight: { bottom: 10, right: 10 },
  title: {
    fontSize: 24, fontWeight: 'bold', color: '#ffffff',
    marginBottom: 25, textAlign: 'center'
  },
  form: { width: '100%', gap: 15 },
  input: {
    backgroundColor: '#e2e8f0', borderRadius: 25,
    paddingVertical: 14, paddingHorizontal: 24,
    fontSize: 15, color: '#1e293b'
  },
  fieldHint: {
    fontSize: 11, color: '#94a3b8',
    marginTop: 6, paddingHorizontal: 8, lineHeight: 16
  },
  buttonWrapper: {
    width: '100%', borderRadius: 25, overflow: 'hidden',
    marginTop: 10, elevation: 5,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3, shadowRadius: 8
  },
  gradientButton: {
    paddingVertical: 16, paddingHorizontal: 40,
    alignItems: 'center', justifyContent: 'center'
  },
  buttonText: { fontSize: 18, fontWeight: 'bold', color: '#ffffff', letterSpacing: 0.5 },
  loginContainer: {
    flexDirection: 'row', justifyContent: 'center',
    alignItems: 'center', marginTop: 15
  },
  loginText: { fontSize: 14, color: '#cbd5e1' },
  loginLink: { fontSize: 14, color: '#22c55e', fontWeight: '600' },
});

export default RegisterScreen;