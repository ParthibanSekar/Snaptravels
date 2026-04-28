import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {cabsAPI} from '../../api/transport';
import {useApi} from '../../hooks/useApi';
import {formatPrice} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'CabResults'>;

export default function CabResultsScreen({route, navigation}: Props) {
  const {pickup, drop, distance_km} = route.params;
  const {data, loading, error, execute} = useApi(cabsAPI.search);

  useEffect(() => { execute({pickup, drop, distance_km}); }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={`${pickup} → ${drop}`} />
      {loading ? <Loading message="Finding cabs…" fullScreen /> :
       error ? <ErrorView message={error} onRetry={() => execute({pickup, drop, distance_km})} /> : (
        <FlatList
          data={data?.cabs ?? []}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ErrorView message="No cabs available." />}
          renderItem={({item}) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() => navigation.navigate('Checkout', {type: 'CAB', item, amount: item.estimated_fare})}>
              <View style={styles.row}>
                <Text style={styles.emoji}>🚕</Text>
                <View style={styles.info}>
                  <Text style={styles.vehicle}>{item.vehicle_type} — {item.brand}</Text>
                  <Text style={styles.meta}>{item.capacity} seats · {item.ac ? 'AC' : 'Non-AC'}</Text>
                  <Text style={styles.base}>Base: {formatPrice(item.base_amount)} for {item.base_km} km</Text>
                </View>
                <View style={styles.fareBox}>
                  <Text style={styles.estLabel}>Est. Fare</Text>
                  <Text style={styles.fare}>{formatPrice(item.estimated_fare)}</Text>
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
  list: {padding: 16, gap: 12},
  card: {backgroundColor: '#fff', borderRadius: 14, padding: 16, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2},
  row: {flexDirection: 'row', alignItems: 'center'},
  emoji: {fontSize: 36, marginRight: 12},
  info: {flex: 1},
  vehicle: {fontSize: 15, fontWeight: '700', color: '#0f172a'},
  meta: {fontSize: 12, color: '#64748b', marginTop: 2},
  base: {fontSize: 12, color: '#94a3b8', marginTop: 2},
  fareBox: {alignItems: 'flex-end'},
  estLabel: {fontSize: 10, color: '#94a3b8'},
  fare: {fontSize: 20, fontWeight: '800', color: '#6366f1'},
});
