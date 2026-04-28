import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {insuranceAPI} from '../../api/bookings';
import {useApi} from '../../hooks/useApi';
import {InsurancePlan} from '../../types';
import {formatPrice} from '../../utils/formatters';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

export default function InsuranceScreen() {
  const navigation = useNavigation<Nav>();
  const {data, loading, error, execute} = useApi(insuranceAPI.list);

  useEffect(() => { execute(); }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Travel Insurance" />
      {loading ? <Loading fullScreen message="Loading plans…" /> :
       error ? <ErrorView message={error} onRetry={execute} /> : (
        <FlatList
          data={data?.plans ?? []} keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          renderItem={({item}: {item: InsurancePlan}) => (
            <View style={[styles.card, item.highlighted && styles.cardFeatured]}>
              {item.highlighted && <View style={styles.popularBadge}><Text style={styles.popularText}>Most Popular</Text></View>}
              <Text style={styles.planName}>{item.name}</Text>
              <Text style={styles.tagline}>{item.tagline}</Text>
              <View style={styles.coverage}>
                {item.coverage.map((c, i) => (
                  <Text key={i} style={styles.coverItem}>✅ {c.label}{c.limit ? ` — ${c.limit}` : ''}</Text>
                ))}
              </View>
              <View style={styles.priceRow}>
                <Text style={styles.priceLabel}>{formatPrice(item.price_per_person_per_day)}<Text style={styles.perDay}>/person/day</Text></Text>
                <TouchableOpacity
                  style={styles.selectBtn}
                  onPress={() => navigation.navigate('Checkout', {type: 'INSURANCE', item, amount: item.price_per_person_per_day})}>
                  <Text style={styles.selectText}>Select</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  list: {padding: 16, gap: 16},
  card: {backgroundColor: '#fff', borderRadius: 16, padding: 20, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2, borderWidth: 2, borderColor: 'transparent'},
  cardFeatured: {borderColor: '#6366f1'},
  popularBadge: {backgroundColor: '#6366f1', alignSelf: 'flex-start', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4, marginBottom: 8},
  popularText: {color: '#fff', fontSize: 11, fontWeight: '700'},
  planName: {fontSize: 20, fontWeight: '800', color: '#0f172a'},
  tagline: {fontSize: 13, color: '#64748b', marginTop: 2, marginBottom: 12},
  coverage: {gap: 6, marginBottom: 16},
  coverItem: {fontSize: 13, color: '#374151'},
  priceRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  priceLabel: {fontSize: 18, fontWeight: '800', color: '#6366f1'},
  perDay: {fontSize: 12, fontWeight: '400', color: '#94a3b8'},
  selectBtn: {backgroundColor: '#6366f1', borderRadius: 10, paddingHorizontal: 20, paddingVertical: 10},
  selectText: {color: '#fff', fontWeight: '700', fontSize: 14},
});
