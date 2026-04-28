import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList, Flight} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {flightsAPI} from '../../api/flights';
import {useApi} from '../../hooks/useApi';
import {formatPrice, formatDuration} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'FlightResults'>;

function FlightCard({flight, onPress}: {flight: Flight; onPress: () => void}) {
  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <View style={styles.cardRow}>
        <View>
          <Text style={styles.time}>{flight.departure_time}</Text>
          <Text style={styles.city}>{flight.origin}</Text>
        </View>
        <View style={styles.middle}>
          <Text style={styles.duration}>{formatDuration(flight.duration_mins)}</Text>
          <Text style={styles.dash}>──────</Text>
          <Text style={styles.flightNo}>{flight.flight_number}</Text>
        </View>
        <View style={{alignItems: 'flex-end'}}>
          <Text style={styles.time}>{flight.arrival_time}</Text>
          <Text style={styles.city}>{flight.destination}</Text>
        </View>
      </View>
      <View style={styles.cardFooter}>
        <Text style={styles.airline}>{flight.airline} · {flight.cabin_class}</Text>
        <Text style={styles.price}>{formatPrice(flight.price)}</Text>
      </View>
      <Text style={styles.seats}>{flight.available_seats} seats left</Text>
    </TouchableOpacity>
  );
}

export default function FlightResultsScreen({route, navigation}: Props) {
  const {origin, destination, date, passengers} = route.params;
  const {data, loading, error, execute} = useApi(flightsAPI.search);

  useEffect(() => {
    execute({origin, destination, date, passengers});
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={`${origin} → ${destination}`} />
      {loading ? (
        <Loading message="Searching flights…" fullScreen />
      ) : error ? (
        <ErrorView message={error} onRetry={() => execute({origin, destination, date, passengers})} />
      ) : (
        <FlatList
          data={data?.flights ?? []}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ErrorView message="No flights found for this route." />}
          renderItem={({item}) => (
            <FlightCard flight={item} onPress={() => navigation.navigate('FlightDetail', {flight: item})} />
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  list: {padding: 16, gap: 12},
  card: {
    backgroundColor: '#fff', borderRadius: 14, padding: 16,
    shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2,
  },
  cardRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  time: {fontSize: 20, fontWeight: '800', color: '#0f172a'},
  city: {fontSize: 12, color: '#64748b', marginTop: 2},
  middle: {alignItems: 'center'},
  duration: {fontSize: 12, color: '#94a3b8'},
  dash: {color: '#cbd5e1', fontSize: 10, marginVertical: 2},
  flightNo: {fontSize: 11, color: '#6366f1', fontWeight: '600'},
  cardFooter: {flexDirection: 'row', justifyContent: 'space-between', marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#f1f5f9'},
  airline: {fontSize: 13, color: '#64748b'},
  price: {fontSize: 18, fontWeight: '800', color: '#6366f1'},
  seats: {fontSize: 11, color: '#22c55e', marginTop: 4},
});
