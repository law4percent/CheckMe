// src/screens/ChoosePortalScreen.tsx
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'ChoosePortal'>;

const ChoosePortalScreen: React.FC<Props> = ({ navigation }) => {
  const handleTeacherPress = () => {
    navigation.navigate('TeacherLogin');
  };

  const handleStudentPress = () => {
    // TODO: Implement student portal in future phase
    alert('Student portal coming soon!');
  };

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
      
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.appName}>CheckMe</Text>
          <Text style={styles.subtitle}>Choose your portal</Text>
        </View>

        <View style={styles.buttonsContainer}>
          <TouchableOpacity 
            style={styles.portalButton}
            onPress={handleTeacherPress}
            activeOpacity={0.8}
          >
            <Text style={styles.portalIcon}>👨‍🏫</Text>
            <Text style={styles.portalTitle}>Teacher</Text>
            <Text style={styles.portalDescription}>
              Access teacher dashboard and manage your classes
            </Text>
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.portalButton, styles.disabledButton]}
            onPress={handleStudentPress}
            activeOpacity={0.8}
          >
            <Text style={styles.portalIcon}>🎓</Text>
            <Text style={styles.portalTitle}>Student</Text>
            <Text style={styles.portalDescription}>
              Coming soon
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>Version 1.0.0</Text>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  content: {
    flex: 1,
    paddingHorizontal: 24
  },
  header: {
    alignItems: 'center',
    marginTop: 60,
    marginBottom: 40
  },
  appName: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#2563eb',
    marginBottom: 8
  },
  subtitle: {
    fontSize: 18,
    color: '#64748b',
    fontWeight: '500'
  },
  buttonsContainer: {
    flex: 1,
    gap: 20
  },
  portalButton: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2
    },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4
  },
  disabledButton: {
    opacity: 0.6
  },
  portalIcon: {
    fontSize: 64,
    marginBottom: 16
  },
  portalTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 8
  },
  portalDescription: {
    fontSize: 16,
    color: '#64748b',
    textAlign: 'center'
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 20
  },
  footerText: {
    fontSize: 14,
    color: '#94a3b8'
  }
});

export default ChoosePortalScreen;