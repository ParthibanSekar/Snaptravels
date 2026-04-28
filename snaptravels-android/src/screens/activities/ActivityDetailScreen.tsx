import React, {useEffect} from 'react';
import {View, Text, ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Button from '../../components/common/Button';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {activitiesAPI} from '../../api/packages';
import {useApi} from '../../hooks/useApi';
import {formatPrice} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'ActivityDetail'>;

export default function ActivityDetailScreen({route, navigation}: Props) {
  const {id} = route.params;
  const {data, loading, error, execute} = useApi(activitiesAPI.get);

  useEffect(() => { execute(id); }, [id]);

  const act = data?.activity;
  if (loading) return <Loading fullScreen message="Loading activity…" />;
  if (error || !act) return <ErrorView message={error ?? 'Activity not found'} />;

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={act.name} />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.hero}><Text style={styles.heroEmoji}>🎯</Text></View>
        <Text style={styles.name}>{act.name}</Text>
        <Text style={styles.meta}>{act.city} · {act.category} · {act.duration_label}</Text>
        <Text style={styles.rating}>⭐ {act.rating.toFixed(1)} ({act.review_count} reviews)</Text>
        {act.description ? <Text style={styles.desc}>{act.description}</Text> : null}
        {act.includes.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>What's Included</Text>
            {act.includes.map((item, i) => <Text key={i} style={styles.bullet}>✅ {item}</Text>)}
          </View>
        )}
        <View style={styles.priceBox}>
          {act.original_price ? <Text style={styles.original}>{formatPrice(act.original_price)}</Text> : null}
          <View style={styles.priceRow}>
            <Text style={styles.priceLabel}>Per Person</Text>
            <Text style={styles.price}>{formatPrice(act.price_per_person)}</Text>
          </View>
          <Text style={styles.persons}>{act.min_persons}–{act.max_persons} persons</Text>
        </View>
        <Button title="Book Activity" onPress={() => navigation.navigate('Checkout', {type: 'ACTIVITY', item: act, amount: act.price_per_person})} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  hero: {height: 160, backgroundColor: '#fce7f3', borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginBottom: 16},
  heroEmoji: {fontSize: 64},
  name: {fontSize: 22, fontWeight: '800', color: '#0f172a'},
  meta: {fontSize: 13, color: '#64748b', marginTop: 4},
  rating: {fontSize: 14, color: '#f59e0b', marginTop: 6, marginBottom: 12},
  desc: {fontSize: 14, color: '#374151', lineHeight: 22, marginBottom: 16},
  section: {marginBottom: 16},
  sectionTitle: {fontSize: 15, fontWeight: '700', color: '#0f172a', marginBottom: 8},
  bullet: {fontSize: 14, color: '#374151', lineHeight: 24},
  priceBox: {backgroundColor: '#fdf2f8', borderRadius: 12, padding: 16, marginBottom: 16},
  original: {fontSize: 14, color: '#94a3b8', textDecorationLine: 'line-through'},
  priceRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  priceLabel: {fontSize: 15, color: '#9d174d', fontWeight: '600'},
  price: {fontSize: 26, fontWeight: '800', color: '#6366f1'},
  persons: {fontSize: 12, color: '#94a3b8', marginTop: 4},
});
