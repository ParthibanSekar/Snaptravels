import React, {useEffect, useState} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView, TextInput} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList, Package} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {packagesAPI} from '../../api/packages';
import {formatPrice} from '../../utils/formatters';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

export default function PackagesScreen() {
  const navigation = useNavigation<Nav>();
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const load = async (destination?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await packagesAPI.list({destination});
      setPackages(res.data.packages);
    } catch (err: unknown) {
      setError((err as {response?: {data?: {error?: string}}})?.response?.data?.error || 'Failed to load packages');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Holiday Packages" />
      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="Search destination…"
          placeholderTextColor="#94a3b8"
          onSubmitEditing={() => load(search.trim() || undefined)}
          returnKeyType="search"
        />
      </View>
      {loading ? <Loading message="Loading packages…" fullScreen /> :
       error ? <ErrorView message={error} onRetry={() => load()} /> : (
        <FlatList
          data={packages}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ErrorView message="No packages found." />}
          renderItem={({item}) => (
            <TouchableOpacity style={styles.card} onPress={() => navigation.navigate('PackageDetail', {slug: item.slug})}>
              <View style={styles.imgPlaceholder}>
                <Text style={styles.imgEmoji}>🌴</Text>
                {item.tag ? <View style={styles.tag}><Text style={styles.tagText}>{item.tag}</Text></View> : null}
              </View>
              <View style={styles.info}>
                <Text style={styles.name} numberOfLines={2}>{item.name}</Text>
                <Text style={styles.dest}>{item.destination} · {item.duration_nights}N</Text>
                <View style={styles.priceRow}>
                  {item.original_price ? <Text style={styles.original}>{formatPrice(item.original_price)}</Text> : null}
                  <Text style={styles.price}>{formatPrice(item.base_price)}</Text>
                  {item.discount_pct > 0 ? <Text style={styles.disc}>{item.discount_pct}% off</Text> : null}
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
  card: {backgroundColor: '#fff', borderRadius: 14, overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2},
  imgPlaceholder: {height: 140, backgroundColor: '#fef3c7', alignItems: 'center', justifyContent: 'center'},
  imgEmoji: {fontSize: 52},
  tag: {position: 'absolute', top: 8, right: 8, backgroundColor: '#ef4444', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3},
  tagText: {color: '#fff', fontSize: 10, fontWeight: '700'},
  info: {padding: 12},
  name: {fontSize: 15, fontWeight: '700', color: '#0f172a'},
  dest: {fontSize: 13, color: '#64748b', marginTop: 2},
  priceRow: {flexDirection: 'row', alignItems: 'center', marginTop: 8, gap: 8},
  original: {fontSize: 13, color: '#94a3b8', textDecorationLine: 'line-through'},
  price: {fontSize: 18, fontWeight: '800', color: '#6366f1'},
  disc: {fontSize: 12, color: '#22c55e', fontWeight: '600'},
});
