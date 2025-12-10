// src/navigation/AppNavigator.tsx
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../contexts/AuthContext';
import { RootStackParamList } from '../types';

// Screens
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
          // User is authenticated - show dashboard based on role
          <>
            {user.role === 'teacher' ? (
              <>
                {/* FIXED: Main dashboard should be first */}
                <Stack.Screen
                  name="TeacherDashboard"
                  component={TeacherDashboardScreen}
                  options={{ headerShown: false }}
                />
                <Stack.Screen
                  name="TeacherSectionDashboard"
                  component={SectionDashboardScreen}
                  options={{
                    headerShown: true,
                    title: 'Section Dashboard',
                    headerBackTitle: 'Back',
                    headerStyle: {
                      backgroundColor: '#171443',
                    },
                    headerTintColor: '#fff',
                    headerTitleStyle: {
                      fontWeight: 'bold',
                    },
                  }}
                />
                <Stack.Screen
                  name="TeacherSubjectDashboard"
                  component={SubjectDashboardScreen}
                  options={{
                    headerShown: true,
                    title: 'Subject Dashboard',
                    headerBackTitle: 'Back',
                    headerStyle: {
                      backgroundColor: '#171443',
                    },
                    headerTintColor: '#fff',
                    headerTitleStyle: {
                      fontWeight: 'bold',
                    },
                  }}
                />
                {/* FIXED: ViewScores should come after the screens that navigate to it */}
                <Stack.Screen
                  name="ViewScores"
                  component={ViewScoresScreen}
                  options={{
                    headerShown: true,
                    title: 'Assessment Results',
                    headerBackTitle: 'Back',
                    headerStyle: {
                      backgroundColor: '#171443',
                    },
                    headerTintColor: '#fff',
                    headerTitleStyle: {
                      fontWeight: 'bold',
                    },
                  }}
                />
                <Stack.Screen
                  name="TeacherAssessmentScoreTable"
                  component={AssessmentScoreTableScreen}
                  options={{
                    headerShown: true,
                    title: 'Assessment Scores',
                    headerBackTitle: 'Back',
                    headerStyle: {
                      backgroundColor: '#171443',
                    },
                    headerTintColor: '#fff',
                    headerTitleStyle: {
                      fontWeight: 'bold',
                    },
                  }}
                />
              </>
            ) : (
              <>
                <Stack.Screen
                  name="StudentDashboard"
                  component={StudentDashboardScreen}
                  options={{ headerShown: false }}
                />
              </>
            )}
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
              component={TeacherLoginScreen}
              options={{
                headerShown: true,
                title: 'Teacher Login',
                headerBackTitle: 'Back'
              }}
            />
            <Stack.Screen
              name="TeacherRegister"
              component={TeacherRegisterScreen}
              options={{
                headerShown: true,
                title: 'Teacher Registration',
                headerBackTitle: 'Back'
              }}
            />
            <Stack.Screen
              name="StudentLogin"
              component={StudentLoginScreen}
              options={{
                headerShown: true,
                title: 'Student Login',
                headerBackTitle: 'Back'
              }}
            />
            <Stack.Screen
              name="StudentRegister"
              component={StudentRegisterScreen}
              options={{
                headerShown: true,
                title: 'Student Registration',
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