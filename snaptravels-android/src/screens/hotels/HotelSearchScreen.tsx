import React, {useState} from 'react';
import {View, ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import {toISODate} from '../../utils/formatters';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

export default function HotelSearchScreen() {
  const navigation = useNavigation<Nav>();
  const today = toISODate(new Date());
  const tomorrow = toISODate(new Date(Date.now() + 86400000));
  const [city, setCity] = useState('');
  const [checkin, setCheckin] = useState(today);
  const [checkout, setCheckout] = useState(tomorrow);
  const [guests, setGuests] = useState('2');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const search = () => {
    const e: Record<string, string> = {};
    if (!city.trim()) e.city = 'Enter city / destination';
    if (!checkin) e.checkin = 'Select check-in date';
    if (!checkout) e.checkout = 'Select check-out date';
    setErrors(e);
    if (Object.keys(e).length) return;
    navigation.navigate('HotelResults', {city: city.trim(), checkin, checkout, guests: parseInt(guests) || 2});
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Search Hotels" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Input label="City / Destination" value={city} onChangeText={setCity} placeholder="Goa, Mumbai, Delhi…" error={errors.city} />
        <Input label="Check-in (YYYY-MM-DD)" value={checkin} onChangeText={setCheckin} placeholder={today} error={errors.checkin} />
        <Input label="Check-out (YYYY-MM-DD)" value={checkout} onChangeText={setCheckout} placeholder={tomorrow} error={errors.checkout} />
        <Input label="Guests" value={guests} onChangeText={setGuests} keyboardType="numeric" placeholder="2" />
        <Button title="Search Hotels 🏨" onPress={search} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  btn: {marginTop: 8},
});
