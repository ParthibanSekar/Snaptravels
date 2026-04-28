import React from 'react';
import {View, Text, ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Button from '../../components/common/Button';
import {formatPrice, formatDuration} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'FlightDetail'>;

export default function FlightDetailScreen({route, navigation}: Props) {
  const {flight} = route.params;

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Flight Details" />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.hero}>
          <Text style={styles.airline}>{flight.airline}</Text>
          <Text style={styles.flightNo}>{flight.flight_number}</Text>
        </View>
        <View style={styles.routeRow}>
          <View style={styles.routePoint}>
            <Text style={styles.time}>{flight.departure_time}</Text>
            <Text style={styles.city}>{flight.origin}</Text>
          </View>
          <View style={styles.routeMid}>
            <Text style={styles.duration}>{formatDuration(flight.duration_mins)}</Text>
            <Text style={styles.dash}>────────</Text>
            <Text style={styles.direct}>Direct</Text>
          </View>
          <View style={[styles.routePoint, {alignItems: 'flex-end'}]}>
            <Text style={styles.time}>{flight.arrival_time}</Text>
            <Text style={styles.city}>{flight.destination}</Text>
          </View>
        </View>
        <View style={styles.details}>
          {[
            ['Date', flight.depart_date ?? '—'],
            ['Cabin', flight.cabin_class],
            ['Seats Available', String(flight.available_seats)],
            ['Duration', formatDuration(flight.duration_mins)],
          ].map(([label, value]) => (
            <View key={label} style={styles.row}>
              <Text style={styles.label}>{label}</Text>
              <Text style={styles.value}>{value}</Text>
            </View>
          ))}
        </View>
        <View style={styles.priceRow}>
          <Text style={styles.priceLabel}>Total Price</Text>
          <Text style={styles.price}>{formatPrice(flight.price)}</Text>
        </View>
        <Button
          title="Book Now"
          onPress={() => navigation.navigate('Checkout', {type: 'FLIGHT', item: flight, amount: flight.price})}
          style={styles.btn}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  hero: {alignItems: 'center', paddingVertical: 16},
  airline: {fontSize: 22, fontWeight: '800', color: '#0f172a'},
  flightNo: {fontSize: 14, color: '#6366f1', fontWeight: '600', marginTop: 4},
  routeRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 20, borderTopWidth: 1, borderBottomWidth: 1, borderColor: '#f1f5f9', marginBottom: 20},
  routePoint: {flex: 1},
  time: {fontSize: 28, fontWeight: '800', color: '#0f172a'},
  city: {fontSize: 13, color: '#64748b'},
  routeMid: {alignItems: 'center'},
  duration: {fontSize: 12, color: '#94a3b8'},
  dash: {color: '#cbd5e1', fontSize: 10},
  direct: {fontSize: 11, color: '#22c55e', fontWeight: '600'},
  details: {gap: 12},
  row: {flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#f8fafc'},
  label: {fontSize: 14, color: '#64748b'},
  value: {fontSize: 14, fontWeight: '600', color: '#1e293b'},
  priceRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 24, marginBottom: 20, backgroundColor: '#f0f9ff', padding: 16, borderRadius: 12},
  priceLabel: {fontSize: 16, color: '#0369a1', fontWeight: '600'},
  price: {fontSize: 26, fontWeight: '800', color: '#6366f1'},
  btn: {marginTop: 4},
});
