import React, {useState} from 'react';
import {ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import {profileAPI} from '../../api/user';
import Toast from 'react-native-toast-message';

export default function EditProfileScreen() {
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [gender, setGender] = useState('');
  const [nationality, setNationality] = useState('Indian');
  const [loading, setLoading] = useState(false);

  const save = async () => {
    setLoading(true);
    try {
      await profileAPI.update({full_name: fullName, phone, gender, nationality});
      Toast.show({type: 'success', text1: 'Profile updated!'});
    } catch { Toast.show({type: 'error', text1: 'Failed to update profile'}); }
    finally { setLoading(false); }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Edit Profile" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Input label="Full Name" value={fullName} onChangeText={setFullName} placeholder="Your full name" />
        <Input label="Phone" value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91 XXXXX XXXXX" />
        <Input label="Gender" value={gender} onChangeText={setGender} placeholder="Male / Female / Other" />
        <Input label="Nationality" value={nationality} onChangeText={setNationality} placeholder="Indian" />
        <Button title="Save Changes" onPress={save} loading={loading} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({safe: {flex: 1, backgroundColor: '#fff'}, content: {padding: 20}, btn: {marginTop: 8}});
