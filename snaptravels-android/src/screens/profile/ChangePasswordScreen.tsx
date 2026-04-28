import React, {useState} from 'react';
import {ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import {authAPI} from '../../api/auth';
import Toast from 'react-native-toast-message';

export default function ChangePasswordScreen() {
  const navigation = useNavigation();
  const [current, setCurrent] = useState('');
  const [newPass, setNewPass] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);

  const save = async () => {
    if (!current || !newPass || !confirm) { Toast.show({type: 'error', text1: 'All fields required'}); return; }
    if (newPass.length < 8) { Toast.show({type: 'error', text1: 'Password must be 8+ characters'}); return; }
    if (newPass !== confirm) { Toast.show({type: 'error', text1: 'Passwords do not match'}); return; }
    setLoading(true);
    try {
      await authAPI.changePassword(current, newPass);
      Toast.show({type: 'success', text1: 'Password changed!'});
      navigation.goBack();
    } catch (err: unknown) {
      const msg = (err as {response?: {data?: {error?: string}}})?.response?.data?.error || 'Failed';
      Toast.show({type: 'error', text1: msg});
    } finally { setLoading(false); }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Change Password" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Input label="Current Password" value={current} onChangeText={setCurrent} secureTextEntry placeholder="Current password" />
        <Input label="New Password" value={newPass} onChangeText={setNewPass} secureTextEntry placeholder="At least 8 characters" />
        <Input label="Confirm New Password" value={confirm} onChangeText={setConfirm} secureTextEntry placeholder="Repeat new password" />
        <Button title="Change Password" onPress={save} loading={loading} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({safe: {flex: 1, backgroundColor: '#fff'}, content: {padding: 20}, btn: {marginTop: 8}});
