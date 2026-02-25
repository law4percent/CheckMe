// src/navigation/AppNavigator.tsx
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../contexts/AuthContext';
import { RootStackParamList } from '../types';

import ChoosePortalScreen from '../screens/ChoosePortalScreen';
import TeacherLoginScreen from '../screens/teacher/LoginScreen';
import TeacherRegisterScreen from '../screens/teacher/RegisterScreen';
import TeacherDashboardScreen from '../screens/teacher/DashboardScreen';
import SectionDashboardScreen from '../screens/teacher/SectionDashboardScreen';
import SubjectDashboardScreen from '../screens/teacher/SubjectDashboardScreen';
import AssessmentScoreTableScreen from '../screens/teacher/AssessmentScoreTableScreen';
import StudentLoginScreen from '../screens/student/LoginScreen';
import StudentRegisterScreen from '../screens/student/RegisterScreen';
import StudentDashboardScreen from '../screens/student/DashboardScreen';
import ViewScoresScreen from '../screens/teacher/ViewScoresScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

const headerStyle = {
  backgroundColor: '#171443',
};
const headerCommon = {
  headerShown: true,
  headerBackTitle: 'Back',
  headerStyle,
  headerTintColor: '#fff',
  headerTitleStyle: { fontWeight: 'bold' as const },
};

const AppNavigator: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) return null;

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false, animation: 'slide_from_right' }}>
        {user ? (
          user.role === 'teacher' ? (
            <>
              <Stack.Screen name="TeacherDashboard" component={TeacherDashboardScreen} />
              <Stack.Screen
                name="TeacherSectionDashboard"
                component={SectionDashboardScreen}
                options={{ ...headerCommon, title: 'Section Dashboard' }}
              />
              <Stack.Screen
                name="TeacherSubjectDashboard"
                component={SubjectDashboardScreen}
                options={{ ...headerCommon, title: 'Subject Dashboard' }}
              />
              <Stack.Screen
                name="ViewScores"
                component={ViewScoresScreen}
                options={{ ...headerCommon, title: 'Assessment Results' }}
              />
              <Stack.Screen
                name="TeacherAssessmentScoreTable"
                component={AssessmentScoreTableScreen}
                options={{ ...headerCommon, title: 'Student Breakdown' }}
              />
            </>
          ) : (
            <Stack.Screen name="StudentDashboard" component={StudentDashboardScreen} />
          )
        ) : (
          <>
            <Stack.Screen name="ChoosePortal" component={ChoosePortalScreen} />
            <Stack.Screen
              name="TeacherLogin"
              component={TeacherLoginScreen}
              options={{ headerShown: true, title: 'Teacher Login', headerBackTitle: 'Back' }}
            />
            <Stack.Screen
              name="TeacherRegister"
              component={TeacherRegisterScreen}
              options={{ headerShown: true, title: 'Teacher Registration', headerBackTitle: 'Back' }}
            />
            <Stack.Screen
              name="StudentLogin"
              component={StudentLoginScreen}
              options={{ headerShown: true, title: 'Student Login', headerBackTitle: 'Back' }}
            />
            <Stack.Screen
              name="StudentRegister"
              component={StudentRegisterScreen}
              options={{ headerShown: true, title: 'Student Registration', headerBackTitle: 'Back' }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;