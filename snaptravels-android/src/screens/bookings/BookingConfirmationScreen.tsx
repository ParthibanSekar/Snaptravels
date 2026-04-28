import React from 'react';
import {View, Text, StyleSheet, SafeAreaView, TouchableOpacity} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Button from '../../components/common/Button';
import {formatPrice, formatDateTime} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'BookingConfirmation'>;

export default function BookingConfirmationScreen({route, navigation}: Props) {
  const {booking} = route.params;
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.check}>✅</Text>
        <Text style={styles.title}>Booking Confirmed!</Text>
        <Text style={styles.sub}>Your booking has been placed successfully.</Text>
        <View style={styles.card}>
          <Row label="Booking Code" value={booking.booking_code} highlight />
          <Row label="Status" value={booking.status} />
          <Row label="Amount" value={formatPrice(booking.total_amount)} />
          <Row label="Booked On" value={formatDateTime(booking.created_at)} />
        </View>
        <Button title="View All Bookings" onPress={() => navigation.navigate('Home')} style={styles.btn} />
        <TouchableOpacity onPress={() => navigation.popToTop()}>
          <Text style={styles.back}>Back to Home</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

function Row({label, value, highlight}: {label: string; value: string; highlight?: boolean}) {
  return (
    <View style={s.row}>
      <Text style={s.label}>{label}</Text>
      <Text style={[s.value, highlight && s.highlight]}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  row: {flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#f1f5f9'},
  label: {fontSize: 14, color: '#64748b'},
  value: {fontSize: 14, fontWeight: '600', color: '#1e293b'},
  highlight: {color: '#6366f1', fontSize: 16, fontWeight: '800'},
});

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {flex: 1, alignItems: 'center', justifyContent: 'center', padding: 28},
  check: {fontSize: 72, marginBottom: 16},
  title: {fontSize: 26, fontWeight: '800', color: '#0f172a'},
  sub: {fontSize: 14, color: '#64748b', marginTop: 6, marginBottom: 28, textAlign: 'center'},
  card: {width: '100%', backgroundColor: '#f8fafc', borderRadius: 14, padding: 16, marginBottom: 28},
  btn: {width: '100%'},
  back: {marginTop: 16, fontSize: 14, color: '#6366f1', fontWeight: '600'},
});
