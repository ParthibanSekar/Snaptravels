import React, {useState} from 'react';
import {View, Text, ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import {toISODate} from '../../utils/formatters';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

export default function FlightSearchScreen() {
  const navigation = useNavigation<Nav>();
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState(toISODate(new Date()));
  const [passengers, setPassengers] = useState('1');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const search = () => {
    const e: Record<string, string> = {};
    if (!origin.trim()) e.origin = 'Enter origin city';
    if (!destination.trim()) e.destination = 'Enter destination city';
    if (!date) e.date = 'Select travel date';
    setErrors(e);
    if (Object.keys(e).length) return;
    navigation.navigate('FlightResults', {
      origin: origin.trim(),
      destination: destination.trim(),
      date,
      passengers: parseInt(passengers, 10) || 1,
    });
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Search Flights" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Input label="From" value={origin} onChangeText={setOrigin} placeholder="Delhi, Chennai…" error={errors.origin} />
        <Input label="To" value={destination} onChangeText={setDestination} placeholder="Mumbai, Goa…" error={errors.destination} />
        <Input label="Travel Date (YYYY-MM-DD)" value={date} onChangeText={setDate} placeholder="2026-05-01" error={errors.date} />
        <Input label="Passengers" value={passengers} onChangeText={setPassengers} keyboardType="numeric" placeholder="1" />
        <Button title="Search Flights ✈️" onPress={search} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  btn: {marginTop: 8},
});
