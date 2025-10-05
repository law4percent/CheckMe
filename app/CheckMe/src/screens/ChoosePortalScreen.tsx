// src/screens/ChoosePortalScreen.tsx
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
  Image
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../types';
import { LinearGradient } from 'expo-linear-gradient';

type Props = NativeStackScreenProps<RootStackParamList, 'ChoosePortal'>;

const ChoosePortalScreen: React.FC<Props> = ({ navigation }) => {
  const handleTeacherPress = () => {
    navigation.navigate('TeacherLogin');
  };

  const handleStudentPress = () => {
    alert('Student portal coming soon!');
  };

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <StatusBar barStyle="light-content" backgroundColor="#171443" />
      
      <View style={styles.content}>
        {/* Logo Section */}
        <View style={styles.logoContainer}>
          <Image 
            source={require('../../assets/checkme-logo.jpg')} 
            style={styles.logoImage}
            resizeMode="contain"
          />
          {/* Decorative dots */}
          <View style={[styles.dot, styles.dotTopLeft]} />
          <View style={[styles.dot, styles.dotTopRight]} />
          <View style={[styles.dot, styles.dotBottomLeft]} />
          <View style={[styles.dot, styles.dotBottomRight]} />
        </View>

        {/* Buttons */}
        <View style={styles.buttonsContainer}>
          <TouchableOpacity 
            style={styles.buttonWrapper}
            onPress={handleTeacherPress}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={['#84cc16', '#22c55e']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.buttonText}>Teacher Portal</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.buttonWrapper}
            onPress={handleStudentPress}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={['#06b6d4', '#3b82f6']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              <Text style={styles.buttonText}>Student Portal</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#171443'
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40
  },
  logoContainer: {
    position: 'relative',
    marginBottom: 80,
    alignItems: 'center',
    width: 250,
    height: 250
  },
  logoImage: {
    width: '100%',
    height: '100%'
  },
  dot: {
    position: 'absolute',
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#22c55e'
  },
  dotTopLeft: {
    top: 20,
    left: 20
  },
  dotTopRight: {
    top: 20,
    right: 20
  },
  dotBottomLeft: {
    bottom: 20,
    left: 20
  },
  dotBottomRight: {
    bottom: 20,
    right: 20
  },
  buttonsContainer: {
    width: '100%',
    gap: 20
  },
  buttonWrapper: {
    width: '100%',
    borderRadius: 30,
    overflow: 'hidden',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8
  },
  gradientButton: {
    paddingVertical: 18,
    paddingHorizontal: 40,
    alignItems: 'center',
    justifyContent: 'center'
  },
  buttonText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ffffff',
    letterSpacing: 0.5
  }
});

export default ChoosePortalScreen;