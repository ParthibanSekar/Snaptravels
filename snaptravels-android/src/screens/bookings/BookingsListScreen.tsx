import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {BookingsStackParamList, Booking} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {bookingsAPI} from '../../api/bookings';
import {useApi} from '../../hooks/useApi';
import {formatPrice, formatDate, statusColor} from '../../utils/formatters';

type Nav = NativeStackNavigationProp<BookingsStackParamList>;

export default function BookingsListScreen() {
  const navigation = useNavigation<Nav>();
  const {data, loading, error, execute} = useApi(bookingsAPI.list);

  useEffect(() => { execute(); }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="My Bookings" showBack={false} />
      {loading ? <Loading fullScreen message="Loading bookings…" /> :
       error ? <ErrorView message={error} onRetry={execute} /> : (
        <FlatList
          data={data?.bookings ?? []} keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyEmoji}>🎫</Text>
              <Text style={styles.emptyText}>No bookings yet</Text>
              <Text style={styles.emptySub}>Start your journey with SnapTravels!</Text>
            </View>
          }
          renderItem={({item}: {item: Booking}) => (
            <TouchableOpacity style={styles.card} onPress={() => navigation.navigate('BookingDetail', {bookingId: item.id})}>
              <View style={styles.header}>
                <Text style={styles.code}>{item.booking_code}</Text>
                <View style={[styles.statusBadge, {backgroundColor: statusColor(item.status) + '20'}]}>
                  <Text style={[styles.statusText, {color: statusColor(item.status)}]}>{item.status}</Text>
                </View>
              </View>
              <Text style={styles.customer}>{item.customer_name}</Text>
              <View style={styles.footer}>
                <Text style={styles.date}>{formatDate(item.created_at)}</Text>
                <Text style={styles.amount}>{formatPrice(item.total_amount)}</Text>
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
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6},
  code: {fontSize: 15, fontWeight: '800', color: '#6366f1'},
  statusBadge: {borderRadius: 20, paddingHorizontal: 10, paddingVertical: 3},
  statusText: {fontSize: 11, fontWeight: '700'},
  customer: {fontSize: 14, color: '#374151'},
  footer: {flexDirection: 'row', justifyContent: 'space-between', marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#f1f5f9'},
  date: {fontSize: 13, color: '#94a3b8'},
  amount: {fontSize: 16, fontWeight: '800', color: '#0f172a'},
  empty: {alignItems: 'center', paddingTop: 80},
  emptyEmoji: {fontSize: 56, marginBottom: 16},
  emptyText: {fontSize: 18, fontWeight: '700', color: '#0f172a'},
  emptySub: {fontSize: 14, color: '#94a3b8', marginTop: 4},
});
