import React from 'react';
import {View, Text, ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Button from '../../components/common/Button';
import {formatPrice} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'HotelDetail'>;

export default function HotelDetailScreen({route, navigation}: Props) {
  const {hotel} = route.params;
  return (
    <SafeAreaView style={styles.safe}>
      <Header title={hotel.name} />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.imgPlaceholder}>
          <Text style={styles.imgEmoji}>🏨</Text>
        </View>
        <Text style={styles.name}>{hotel.name}</Text>
        <Text style={styles.city}>{hotel.city}</Text>
        <Text style={styles.stars}>{'★'.repeat(Math.round(hotel.rating))} {hotel.rating.toFixed(1)}</Text>
        {hotel.description ? <Text style={styles.desc}>{hotel.description}</Text> : null}
        {hotel.amenities ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Amenities</Text>
            <Text style={styles.amenities}>{hotel.amenities}</Text>
          </View>
        ) : null}
        <View style={styles.priceRow}>
          <Text style={styles.priceLabel}>Price per Night</Text>
          <Text style={styles.price}>{formatPrice(hotel.price_per_night)}</Text>
        </View>
        <Button
          title="Book Now"
          onPress={() => navigation.navigate('Checkout', {type: 'HOTEL', item: hotel, amount: hotel.price_per_night})}
          style={styles.btn}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  imgPlaceholder: {height: 180, backgroundColor: '#e0e7ff', borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginBottom: 16},
  imgEmoji: {fontSize: 64},
  name: {fontSize: 22, fontWeight: '800', color: '#0f172a'},
  city: {fontSize: 14, color: '#64748b', marginTop: 4},
  stars: {fontSize: 16, color: '#f59e0b', marginTop: 6},
  desc: {fontSize: 14, color: '#374151', lineHeight: 22, marginTop: 12},
  section: {marginTop: 16},
  sectionTitle: {fontSize: 15, fontWeight: '700', color: '#0f172a', marginBottom: 6},
  amenities: {fontSize: 13, color: '#64748b'},
  priceRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, marginBottom: 16, backgroundColor: '#f0fdf4', padding: 16, borderRadius: 12},
  priceLabel: {fontSize: 15, color: '#166534', fontWeight: '600'},
  price: {fontSize: 26, fontWeight: '800', color: '#6366f1'},
  btn: {},
});
