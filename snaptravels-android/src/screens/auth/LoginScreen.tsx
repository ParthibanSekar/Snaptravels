import React, {useState} from 'react';
import {View, Text, ScrollView, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform} from 'react-native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {AuthStackParamList} from '../../types';
import {useAuth} from '../../context/AuthContext';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Toast from 'react-native-toast-message';

type Props = {navigation: NativeStackNavigationProp<AuthStackParamList, 'Login'>};

export default function LoginScreen({navigation}: Props) {
  const {login} = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{email?: string; password?: string}>({});

  const validate = () => {
    const e: typeof errors = {};
    if (!email.trim()) e.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Enter a valid email';
    if (!password) e.password = 'Password is required';
    else if (password.length < 6) e.password = 'Password too short';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleLogin = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
    } catch (err: unknown) {
      const msg = (err as {response?: {data?: {error?: string}}})?.response?.data?.error || 'Login failed';
      Toast.show({type: 'error', text1: 'Login failed', text2: msg});
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.logo}>✈️</Text>
        <Text style={styles.brand}>SnapTravels</Text>
        <Text style={styles.subtitle}>Sign in to your account</Text>

        <View style={styles.form}>
          <Input
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="you@example.com"
            error={errors.email}
          />
          <Input
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="••••••••"
            error={errors.password}
          />
          <Button title="Sign In" onPress={handleLogin} loading={loading} style={styles.btn} />
        </View>

        <TouchableOpacity onPress={() => navigation.navigate('Register')}>
          <Text style={styles.switchText}>
            Don't have an account? <Text style={styles.link}>Sign up</Text>
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: {flex: 1, backgroundColor: '#0f172a'},
  container: {flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: 28},
  logo: {fontSize: 52},
  brand: {fontSize: 30, fontWeight: '800', color: '#fff', marginBottom: 6},
  subtitle: {fontSize: 14, color: '#94a3b8', marginBottom: 36},
  form: {width: '100%', maxWidth: 360},
  btn: {marginTop: 8},
  switchText: {marginTop: 28, fontSize: 14, color: '#94a3b8'},
  link: {color: '#818cf8', fontWeight: '600'},
});
