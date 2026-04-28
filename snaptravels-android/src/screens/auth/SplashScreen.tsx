import React from 'react';
import {View, Text, StyleSheet, ActivityIndicator} from 'react-native';

export default function SplashScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.logo}>✈️</Text>
      <Text style={styles.brand}>SnapTravels</Text>
      <Text style={styles.tagline}>Your journey starts here</Text>
      <ActivityIndicator color="#6366f1" style={styles.spinner} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#0f172a'},
  logo: {fontSize: 64, marginBottom: 16},
  brand: {fontSize: 36, fontWeight: '800', color: '#fff', letterSpacing: -0.5},
  tagline: {fontSize: 15, color: '#94a3b8', marginTop: 8, marginBottom: 40},
  spinner: {marginTop: 24},
});
