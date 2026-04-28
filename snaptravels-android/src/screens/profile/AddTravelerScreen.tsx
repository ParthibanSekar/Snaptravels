import React, {useState} from 'react';
import {ScrollView, StyleSheet, SafeAreaView, View, Switch, Text} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import {travelersAPI} from '../../api/user';
import Toast from 'react-native-toast-message';

export default function AddTravelerScreen() {
  const navigation = useNavigation();
  const [name, setName] = useState('');
  const [gender, setGender] = useState('');
  const [nationality, setNationality] = useState('Indian');
  const [idType, setIdType] = useState('');
  const [idNumber, setIdNumber] = useState('');
  const [passport, setPassport] = useState('');
  const [isPrimary, setIsPrimary] = useState(false);
  const [loading, setLoading] = useState(false);

  const save = async () => {
    if (!name.trim()) { Toast.show({type: 'error', text1: 'Name is required'}); return; }
    setLoading(true);
    try {
      await travelersAPI.add({full_name: name.trim(), gender, nationality, id_type: idType, id_number: idNumber, passport_no: passport, is_primary: isPrimary, age: null, date_of_birth: null});
      Toast.show({type: 'success', text1: 'Traveler added!'});
      navigation.goBack();
    } catch { Toast.show({type: 'error', text1: 'Failed to add traveler'}); }
    finally { setLoading(false); }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Add Traveler" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Input label="Full Name *" value={name} onChangeText={setName} placeholder="As on ID / Passport" />
        <Input label="Gender" value={gender} onChangeText={setGender} placeholder="Male / Female / Other" />
        <Input label="Nationality" value={nationality} onChangeText={setNationality} placeholder="Indian" />
        <Input label="ID Type" value={idType} onChangeText={setIdType} placeholder="Aadhaar / PAN / Passport" />
        <Input label="ID Number" value={idNumber} onChangeText={setIdNumber} placeholder="XXXX XXXX XXXX" />
        <Input label="Passport No" value={passport} onChangeText={setPassport} placeholder="A1234567" />
        <View style={styles.row}>
          <Text style={styles.switchLabel}>Set as Primary Traveler</Text>
          <Switch value={isPrimary} onValueChange={setIsPrimary} trackColor={{true: '#6366f1'}} />
        </View>
        <Button title="Save Traveler" onPress={save} loading={loading} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  row: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20},
  switchLabel: {fontSize: 15, color: '#374151', fontWeight: '500'},
  btn: {},
});
