import React from 'react';
import {View, Text, ScrollView, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {ProfileStackParamList} from '../../types';
import Header from '../../components/common/Header';
import {useAuth} from '../../context/AuthContext';
import Toast from 'react-native-toast-message';

type Nav = NativeStackNavigationProp<ProfileStackParamList>;

const MENU_ITEMS = [
  {id: 'EditProfile', label: 'Edit Profile', emoji: '👤', screen: 'EditProfile'},
  {id: 'Travelers', label: 'Saved Travelers', emoji: '👨‍👩‍👧‍👦', screen: 'Travelers'},
  {id: 'Rewards', label: 'Rewards & Points', emoji: '⭐', screen: 'Rewards'},
  {id: 'PriceAlerts', label: 'Price Alerts', emoji: '🔔', screen: 'PriceAlerts'},
  {id: 'ChangePassword', label: 'Change Password', emoji: '🔒', screen: 'ChangePassword'},
] as const;

export default function ProfileHomeScreen() {
  const navigation = useNavigation<Nav>();
  const {user, logout} = useAuth();

  const handleLogout = async () => {
    try { await logout(); } catch {}
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Profile" showBack={false} />
      <ScrollView>
        <View style={styles.avatar}>
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarText}>{user?.email.charAt(0).toUpperCase()}</Text>
          </View>
          <Text style={styles.email}>{user?.email}</Text>
          <Text style={styles.role}>{user?.role === 'admin' ? '🛡️ Admin' : '✈️ Traveller'}</Text>
        </View>
        <View style={styles.menu}>
          {MENU_ITEMS.map(item => (
            <TouchableOpacity
              key={item.id}
              style={styles.menuItem}
              onPress={() => navigation.navigate(item.screen)}>
              <Text style={styles.menuEmoji}>{item.emoji}</Text>
              <Text style={styles.menuLabel}>{item.label}</Text>
              <Text style={styles.arrow}>›</Text>
            </TouchableOpacity>
          ))}
        </View>
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  avatar: {alignItems: 'center', paddingVertical: 28, backgroundColor: '#0f172a'},
  avatarCircle: {width: 72, height: 72, borderRadius: 36, backgroundColor: '#6366f1', alignItems: 'center', justifyContent: 'center', marginBottom: 12},
  avatarText: {fontSize: 28, fontWeight: '800', color: '#fff'},
  email: {fontSize: 16, fontWeight: '600', color: '#fff'},
  role: {fontSize: 13, color: '#94a3b8', marginTop: 4},
  menu: {backgroundColor: '#fff', marginTop: 16, borderTopWidth: 1, borderBottomWidth: 1, borderColor: '#e2e8f0'},
  menuItem: {flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#f1f5f9'},
  menuEmoji: {fontSize: 20, marginRight: 14},
  menuLabel: {flex: 1, fontSize: 15, color: '#1e293b'},
  arrow: {fontSize: 20, color: '#94a3b8'},
  logoutBtn: {margin: 24, backgroundColor: '#fff', borderRadius: 12, padding: 16, alignItems: 'center', borderWidth: 1.5, borderColor: '#ef4444'},
  logoutText: {fontSize: 15, fontWeight: '700', color: '#ef4444'},
});
