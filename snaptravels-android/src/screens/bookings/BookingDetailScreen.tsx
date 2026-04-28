import React, {useEffect, useState} from 'react';
import {View, Text, ScrollView, StyleSheet, SafeAreaView, Alert} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {BookingsStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Button from '../../components/common/Button';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {bookingsAPI} from '../../api/bookings';
import {useApi} from '../../hooks/useApi';
import {formatPrice, formatDateTime, statusColor} from '../../utils/formatters';
import Toast from 'react-native-toast-message';

type Props = NativeStackScreenProps<BookingsStackParamList, 'BookingDetail'>;

export default function BookingDetailScreen({route, navigation}: Props) {
  const {bookingId} = route.params;
  const {data, loading, error, execute} = useApi(bookingsAPI.get);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => { execute(bookingId); }, [bookingId]);

  const handleCancel = () => {
    Alert.alert('Cancel Booking', 'Are you sure you want to cancel this booking?', [
      {text: 'No', style: 'cancel'},
      {
        text: 'Yes, Cancel',
        style: 'destructive',
        onPress: async () => {
          setCancelling(true);
          try {
            await bookingsAPI.cancel(bookingId);
            Toast.show({type: 'success', text1: 'Booking cancelled'});
            execute(bookingId);
          } catch {
            Toast.show({type: 'error', text1: 'Failed to cancel booking'});
          } finally { setCancelling(false); }
        },
      },
    ]);
  };

  const booking = data?.booking;
  if (loading) return <Loading fullScreen />;
  if (error || !booking) return <ErrorView message={error ?? 'Booking not found'} />;

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={booking.booking_code} />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={[styles.statusBar, {backgroundColor: statusColor(booking.status) + '20'}]}>
          <Text style={[styles.status, {color: statusColor(booking.status)}]}>{booking.status}</Text>
        </View>
        {[
          ['Booking Code', booking.booking_code],
          ['Customer', booking.customer_name],
          ['Email', booking.customer_email],
          ['Phone', booking.customer_phone ?? '—'],
          ['Total Amount', formatPrice(booking.total_amount)],
          ['Booked On', formatDateTime(booking.created_at)],
        ].map(([label, value]) => (
          <View key={label} style={styles.row}>
            <Text style={styles.label}>{label}</Text>
            <Text style={styles.value}>{value}</Text>
          </View>
        ))}
        {booking.items.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Items</Text>
            {booking.items.map((item, i) => (
              <View key={i} style={styles.itemCard}>
                <Text style={styles.itemType}>{item.type}</Text>
                <Text style={styles.itemTitle}>{item.title}</Text>
                <Text style={styles.itemAmount}>{formatPrice(item.amount)}</Text>
              </View>
            ))}
          </View>
        )}
        {booking.status === 'CONFIRMED' && (
          <Button
            title="Cancel Booking"
            variant="danger"
            onPress={handleCancel}
            loading={cancelling}
            style={styles.cancelBtn}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  statusBar: {padding: 12, borderRadius: 10, alignItems: 'center', marginBottom: 16},
  status: {fontSize: 15, fontWeight: '800'},
  row: {flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#f1f5f9'},
  label: {fontSize: 14, color: '#64748b'},
  value: {fontSize: 14, fontWeight: '600', color: '#1e293b', flex: 1, textAlign: 'right'},
  section: {marginTop: 20},
  sectionTitle: {fontSize: 16, fontWeight: '700', color: '#0f172a', marginBottom: 10},
  itemCard: {backgroundColor: '#f8fafc', borderRadius: 10, padding: 12, marginBottom: 8},
  itemType: {fontSize: 11, fontWeight: '700', color: '#6366f1', textTransform: 'uppercase'},
  itemTitle: {fontSize: 14, color: '#0f172a', fontWeight: '600', marginTop: 2},
  itemAmount: {fontSize: 16, fontWeight: '800', color: '#374151', marginTop: 4},
  cancelBtn: {marginTop: 24},
});
