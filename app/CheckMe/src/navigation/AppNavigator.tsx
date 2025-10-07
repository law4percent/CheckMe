// src/navigation/AppNavigator.tsx
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../contexts/AuthContext';
import { RootStackParamList } from '../types';

// Screens
import ChoosePortalScreen from '../screens/ChoosePortalScreen';
import LoginScreen from '../screens/teacher/LoginScreen';
import RegisterScreen from '../screens/teacher/RegisterScreen';
import DashboardScreen from '../screens/teacher/DashboardScreen';
import SectionSubjectScreen from '../screens/teacher/SectionSubjectScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

const AppNavigator: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    // You can return a loading screen component here
    return null;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          animation: 'slide_from_right'
        }}
      >
        {user ? (
          // User is authenticated - show dashboard
          <>
            <Stack.Screen 
              name="TeacherDashboard" // ERROR Type '"TeacherDashboard"' is not assignable to type '"TeacherSectionSubject"'.
              component={DashboardScreen}
              options={{ headerShown: false }}
            />
            <Stack.Screen 
              name="TeacherSectionSubject" // ERROR Type '"TeacherSectionSubject"' is not assignable to type 'keyof RootStackParamList'.
              component={SectionSubjectScreen}
              options={{ 
                headerShown: true, 
                title: 'Section > Subjects',
                headerBackTitle: 'Back' 
              }}
            />
          </>
        ) : (
          // User is not authenticated - show auth flow
          <>
            <Stack.Screen 
              name="ChoosePortal" 
              component={ChoosePortalScreen}
              options={{ headerShown: false }}
            />
            <Stack.Screen 
              name="TeacherLogin" 
              component={LoginScreen}
              options={{ 
                headerShown: true,
                title: 'Teacher Login',
                headerBackTitle: 'Back'
              }}
            />
            <Stack.Screen 
              name="TeacherRegister" 
              component={RegisterScreen}
              options={{ 
                headerShown: true,
                title: 'Teacher Registration',
                headerBackTitle: 'Back'
              }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;