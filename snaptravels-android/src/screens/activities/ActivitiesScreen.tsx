import React, {useEffect, useState} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView, TextInput} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList, Activity} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {activitiesAPI} from '../../api/packages';
import {formatPrice} from '../../utils/formatters';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

export default function ActivitiesScreen() {
  const navigation = useNavigation<Nav>();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [city, setCity] = useState('');

  const load = async (c?: string) => {
    setLoading(true); setError(null);
    try {
      const res = await activitiesAPI.list({city: c});
      setActivities(res.data.activities);
    } catch { setError('Failed to load activities'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Activities & Experiences" />
      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput} value={city} onChangeText={setCity}
          placeholder="Filter by city…" placeholderTextColor="#94a3b8"
          onSubmitEditing={() => load(city.trim() || undefined)} returnKeyType="search"
        />
      </View>
      {loading ? <Loading fullScreen message="Loading activities…" /> :
       error ? <ErrorView message={error} onRetry={load} /> : (
        <FlatList
          data={activities} keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ErrorView message="No activities found." />}
          renderItem={({item}) => (
            <TouchableOpacity style={styles.card} onPress={() => navigation.navigate('ActivityDetail', {id: item.id})}>
              <View style={styles.imgPlaceholder}><Text style={styles.imgEmoji}>🎯</Text></View>
              <View style={styles.info}>
                <Text style={styles.name} numberOfLines={2}>{item.name}</Text>
                <Text style={styles.meta}>{item.city} · {item.category} · {item.duration_label}</Text>
                <Text style={styles.rating}>⭐ {item.rating.toFixed(1)} ({item.review_count})</Text>
                <View style={styles.priceRow}>
                  {item.original_price ? <Text style={styles.original}>{formatPrice(item.original_price)}</Text> : null}
                  <Text style={styles.price}>{formatPrice(item.price_per_person)}<Text style={styles.perPax}>/person</Text></Text>
                </View>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  searchBar: {padding: 12, backgroundColor: '#fff'},
  searchInput: {backgroundColor: '#f1f5f9', borderRadius: 10, padding: 10, fontSize: 14, color: '#1e293b'},
  list: {padding: 16, gap: 12},
  card: {backgroundColor: '#fff', borderRadius: 14, overflow: 'hidden', flexDirection: 'row', shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2},
  imgPlaceholder: {width: 90, backgroundColor: '#fce7f3', alignItems: 'center', justifyContent: 'center'},
  imgEmoji: {fontSize: 32},
  info: {flex: 1, padding: 12},
  name: {fontSize: 14, fontWeight: '700', color: '#0f172a'},
  meta: {fontSize: 12, color: '#64748b', marginTop: 2},
  rating: {fontSize: 12, color: '#f59e0b', marginTop: 4},
  priceRow: {flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4},
  original: {fontSize: 11, color: '#94a3b8', textDecorationLine: 'line-through'},
  price: {fontSize: 16, fontWeight: '800', color: '#6366f1'},
  perPax: {fontSize: 11, fontWeight: '400', color: '#94a3b8'},
});
