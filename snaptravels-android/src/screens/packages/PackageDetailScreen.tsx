import React, {useEffect} from 'react';
import {View, Text, ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Button from '../../components/common/Button';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {packagesAPI} from '../../api/packages';
import {useApi} from '../../hooks/useApi';
import {formatPrice} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'PackageDetail'>;

export default function PackageDetailScreen({route, navigation}: Props) {
  const {slug} = route.params;
  const {data, loading, error, execute} = useApi(packagesAPI.get);

  useEffect(() => { execute(slug); }, [slug]);

  const pkg = data?.package;

  if (loading) return <Loading fullScreen message="Loading package…" />;
  if (error || !pkg) return <ErrorView message={error ?? 'Package not found'} />;

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={pkg.name} />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.hero}>
          <Text style={styles.heroEmoji}>🌴</Text>
          {pkg.tag ? <View style={styles.tag}><Text style={styles.tagText}>{pkg.tag}</Text></View> : null}
        </View>
        <Text style={styles.name}>{pkg.name}</Text>
        <Text style={styles.dest}>{pkg.destination}, {pkg.country} · {pkg.duration_nights} nights</Text>
        {pkg.description ? <Text style={styles.desc}>{pkg.description}</Text> : null}

        <View style={styles.includes}>
          {pkg.includes_flight && <Text style={styles.incl}>✈️ Flights</Text>}
          {pkg.includes_hotel && <Text style={styles.incl}>🏨 Hotels</Text>}
          {pkg.includes_meals && <Text style={styles.incl}>🍽️ Meals</Text>}
          {pkg.includes_transfers && <Text style={styles.incl}>🚗 Transfers</Text>}
        </View>

        {pkg.highlights && pkg.highlights.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Highlights</Text>
            {pkg.highlights.map((h, i) => (
              <Text key={i} style={styles.bullet}>• {h}</Text>
            ))}
          </View>
        )}

        {pkg.itinerary && pkg.itinerary.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Itinerary</Text>
            {pkg.itinerary.map((day: {day: number; title: string; activities: string[]}, i: number) => (
              <View key={i} style={styles.day}>
                <Text style={styles.dayTitle}>Day {day.day}: {day.title}</Text>
                {day.activities?.map((a, j) => <Text key={j} style={styles.activity}>• {a}</Text>)}
              </View>
            ))}
          </View>
        )}

        <View style={styles.priceBox}>
          {pkg.original_price ? <Text style={styles.original}>{formatPrice(pkg.original_price)}</Text> : null}
          <View style={styles.priceRow}>
            <Text style={styles.priceLabel}>Price per person</Text>
            <Text style={styles.price}>{formatPrice(pkg.base_price)}</Text>
          </View>
          {pkg.discount_pct > 0 ? <Text style={styles.savings}>You save {pkg.discount_pct}%!</Text> : null}
        </View>
        <Text style={styles.bookingsBadge}>🔥 {pkg.bookings_today} people booked today</Text>
        <Button
          title="Book This Package"
          onPress={() => navigation.navigate('Checkout', {type: 'PACKAGE', item: pkg, amount: pkg.base_price})}
          style={styles.btn}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  hero: {height: 160, backgroundColor: '#fef3c7', borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginBottom: 16},
  heroEmoji: {fontSize: 64},
  tag: {position: 'absolute', top: 10, right: 10, backgroundColor: '#ef4444', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4},
  tagText: {color: '#fff', fontWeight: '700', fontSize: 11},
  name: {fontSize: 22, fontWeight: '800', color: '#0f172a'},
  dest: {fontSize: 14, color: '#64748b', marginTop: 4, marginBottom: 12},
  desc: {fontSize: 14, color: '#374151', lineHeight: 22, marginBottom: 16},
  includes: {flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16},
  incl: {fontSize: 13, backgroundColor: '#f0fdf4', color: '#166534', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20},
  section: {marginBottom: 20},
  sectionTitle: {fontSize: 16, fontWeight: '700', color: '#0f172a', marginBottom: 8},
  bullet: {fontSize: 14, color: '#374151', lineHeight: 22},
  day: {marginBottom: 12, paddingLeft: 12, borderLeftWidth: 2, borderLeftColor: '#6366f1'},
  dayTitle: {fontSize: 14, fontWeight: '700', color: '#0f172a'},
  activity: {fontSize: 13, color: '#64748b', lineHeight: 20},
  priceBox: {backgroundColor: '#f0f9ff', borderRadius: 12, padding: 16, marginBottom: 12},
  original: {fontSize: 14, color: '#94a3b8', textDecorationLine: 'line-through'},
  priceRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  priceLabel: {fontSize: 15, color: '#0369a1', fontWeight: '600'},
  price: {fontSize: 26, fontWeight: '800', color: '#6366f1'},
  savings: {fontSize: 12, color: '#22c55e', fontWeight: '600', marginTop: 4},
  bookingsBadge: {fontSize: 13, color: '#92400e', marginBottom: 16},
  btn: {},
});
