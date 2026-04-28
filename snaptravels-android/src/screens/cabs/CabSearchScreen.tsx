import React, {useState} from 'react';
import {ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

export default function CabSearchScreen() {
  const navigation = useNavigation<Nav>();
  const [pickup, setPickup] = useState('');
  const [drop, setDrop] = useState('');
  const [distance, setDistance] = useState('20');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const search = () => {
    const e: Record<string, string> = {};
    if (!pickup.trim()) e.pickup = 'Enter pickup location';
    if (!drop.trim()) e.drop = 'Enter drop location';
    setErrors(e);
    if (Object.keys(e).length) return;
    navigation.navigate('CabResults', {pickup: pickup.trim(), drop: drop.trim(), distance_km: parseFloat(distance) || 20});
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Book a Cab" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Input label="Pickup Location" value={pickup} onChangeText={setPickup} placeholder="Airport, Hotel, Address…" error={errors.pickup} />
        <Input label="Drop Location" value={drop} onChangeText={setDrop} placeholder="Destination address…" error={errors.drop} />
        <Input label="Estimated Distance (km)" value={distance} onChangeText={setDistance} keyboardType="numeric" placeholder="20" />
        <Button title="See Available Cabs 🚕" onPress={search} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({safe: {flex: 1, backgroundColor: '#fff'}, content: {padding: 20}, btn: {marginTop: 8}});
