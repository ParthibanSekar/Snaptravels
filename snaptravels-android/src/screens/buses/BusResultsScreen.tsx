import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList, Bus} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {busesAPI} from '../../api/transport';
import {useApi} from '../../hooks/useApi';
import {formatPrice, formatDuration} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'BusResults'>;

export default function BusResultsScreen({route, navigation}: Props) {
  const {origin, destination, date} = route.params;
  const {data, loading, error, execute} = useApi(busesAPI.search);

  useEffect(() => { execute({origin, destination, date}); }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={`${origin} → ${destination}`} />
      {loading ? <Loading message="Searching buses…" fullScreen /> :
       error ? <ErrorView message={error} onRetry={() => execute({origin, destination, date})} /> : (
        <FlatList
          data={data?.buses ?? []}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ErrorView message="No buses found." />}
          renderItem={({item}) => (
            <TouchableOpacity style={styles.card} onPress={() => {}}>
              <View style={styles.row}>
                <View>
                  <Text style={styles.time}>{item.depart_time}</Text>
                  <Text style={styles.label}>{item.origin}</Text>
                </View>
                <View style={styles.mid}>
                  <Text style={styles.dur}>{formatDuration(item.duration_mins)}</Text>
                  <Text style={styles.busType}>{item.bus_type}</Text>
                </View>
                <View style={{alignItems: 'flex-end'}}>
                  <Text style={styles.time}>{item.arrive_time}</Text>
                  <Text style={styles.label}>{item.destination}</Text>
                </View>
              </View>
              <View style={styles.footer}>
                <Text style={styles.operator}>{item.operator} · {item.seats_left} seats</Text>
                <Text style={styles.price}>{formatPrice(item.price)}</Text>
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
  row: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  time: {fontSize: 20, fontWeight: '800', color: '#0f172a'},
  label: {fontSize: 12, color: '#64748b'},
  mid: {alignItems: 'center'},
  dur: {fontSize: 12, color: '#94a3b8'},
  busType: {fontSize: 11, color: '#6366f1', fontWeight: '600'},
  footer: {flexDirection: 'row', justifyContent: 'space-between', marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#f1f5f9'},
  operator: {fontSize: 13, color: '#64748b'},
  price: {fontSize: 18, fontWeight: '800', color: '#6366f1'},
});
