import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {trainsAPI} from '../../api/transport';
import {useApi} from '../../hooks/useApi';
import {formatPrice, formatDuration} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'TrainResults'>;

export default function TrainResultsScreen({route}: Props) {
  const {origin, destination, date} = route.params;
  const {data, loading, error, execute} = useApi(trainsAPI.search);

  useEffect(() => { execute({origin, destination, date}); }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={`${origin} → ${destination}`} />
      {loading ? <Loading message="Searching trains…" fullScreen /> :
       error ? <ErrorView message={error} onRetry={() => execute({origin, destination, date})} /> : (
        <FlatList
          data={data?.trains ?? []}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ErrorView message="No trains found." />}
          renderItem={({item}) => (
            <View style={styles.card}>
              <Text style={styles.trainName}>{item.train_name} <Text style={styles.trainNo}>({item.train_no})</Text></Text>
              <Text style={styles.meta}>{item.train_type} · {item.run_days} · {item.distance_km} km · {formatDuration(item.duration_mins)}</Text>
              <View style={styles.timeRow}>
                <Text style={styles.time}>{item.depart_time}</Text>
                <Text style={styles.arrow}> ──── </Text>
                <Text style={styles.time}>{item.arrive_time}</Text>
              </View>
              <View style={styles.classes}>
                {item.classes.map(c => (
                  <View key={c.class} style={styles.classBadge}>
                    <Text style={styles.classLabel}>{c.class}</Text>
                    <Text style={styles.classFare}>{formatPrice(c.fare)}</Text>
                    <Text style={styles.classSeats}>{c.seats_available} avail</Text>
                  </View>
                ))}
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
  list: {padding: 16, gap: 12},
  card: {backgroundColor: '#fff', borderRadius: 14, padding: 16, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2},
  trainName: {fontSize: 16, fontWeight: '700', color: '#0f172a'},
  trainNo: {fontWeight: '400', color: '#64748b'},
  meta: {fontSize: 12, color: '#94a3b8', marginTop: 2, marginBottom: 8},
  timeRow: {flexDirection: 'row', alignItems: 'center'},
  time: {fontSize: 20, fontWeight: '800', color: '#0f172a'},
  arrow: {color: '#cbd5e1', fontSize: 12},
  classes: {flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12},
  classBadge: {backgroundColor: '#f0f9ff', borderRadius: 8, padding: 8, alignItems: 'center', minWidth: 72},
  classLabel: {fontSize: 12, fontWeight: '700', color: '#0369a1'},
  classFare: {fontSize: 14, fontWeight: '800', color: '#6366f1', marginTop: 2},
  classSeats: {fontSize: 10, color: '#22c55e', marginTop: 1},
});
