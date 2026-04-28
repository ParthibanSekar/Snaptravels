import React, {useState} from 'react';
import {ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import {toISODate} from '../../utils/formatters';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

export default function TrainSearchScreen() {
  const navigation = useNavigation<Nav>();
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState(toISODate(new Date()));
  const [errors, setErrors] = useState<Record<string, string>>({});

  const search = () => {
    const e: Record<string, string> = {};
    if (!origin.trim()) e.origin = 'Enter origin';
    if (!destination.trim()) e.destination = 'Enter destination';
    setErrors(e);
    if (Object.keys(e).length) return;
    navigation.navigate('TrainResults', {origin: origin.trim(), destination: destination.trim(), date});
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Search Trains" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Input label="From" value={origin} onChangeText={setOrigin} placeholder="Chennai, Delhi…" error={errors.origin} />
        <Input label="To" value={destination} onChangeText={setDestination} placeholder="Mumbai, Bangalore…" error={errors.destination} />
        <Input label="Travel Date (YYYY-MM-DD)" value={date} onChangeText={setDate} placeholder={toISODate(new Date())} />
        <Button title="Search Trains 🚆" onPress={search} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({safe: {flex: 1, backgroundColor: '#fff'}, content: {padding: 20}, btn: {marginTop: 8}});
