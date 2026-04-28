import React, {useState} from 'react';
import {View, Text, ScrollView, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList} from '../../types';
import Header from '../../components/common/Header';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import {bookingsAPI} from '../../api/bookings';
import {promoAPI} from '../../api/user';
import {useAuth} from '../../context/AuthContext';
import {formatPrice} from '../../utils/formatters';
import Toast from 'react-native-toast-message';

type Props = NativeStackScreenProps<HomeStackParamList, 'Checkout'>;

export default function CheckoutScreen({route, navigation}: Props) {
  const {type, item, amount} = route.params;
  const {user} = useAuth();
  const typedItem = item as {id?: number};
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [promo, setPromo] = useState('');
  const [promoDiscount, setPromoDiscount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [promoLoading, setPromoLoading] = useState(false);

  const finalAmount = amount - promoDiscount;

  const applyPromo = async () => {
    if (!promo.trim()) return;
    setPromoLoading(true);
    try {
      const res = await promoAPI.validate(promo.trim().toUpperCase(), amount);
      setPromoDiscount(res.data.promo.discount_amount);
      Toast.show({type: 'success', text1: '🎉 Promo applied!', text2: `You saved ${formatPrice(res.data.promo.discount_amount)}`});
    } catch (err: unknown) {
      const msg = (err as {response?: {data?: {error?: string}}})?.response?.data?.error || 'Invalid promo code';
      Toast.show({type: 'error', text1: 'Promo failed', text2: msg});
    } finally { setPromoLoading(false); }
  };

  const handleBook = async () => {
    if (!name.trim()) { Toast.show({type: 'error', text1: 'Name required'}); return; }
    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        type: type.toUpperCase() === 'CAB' ? 'FLIGHT' : type.toUpperCase(), // map non-standard types
        customer_name: name.trim(),
        customer_email: user?.email,
        customer_phone: phone.trim(),
        amount: finalAmount,
      };
      if (type === 'FLIGHT' && typedItem.id) payload.flight_id = typedItem.id;
      if (type === 'HOTEL' && typedItem.id) payload.hotel_id = typedItem.id;

      const res = await bookingsAPI.create(payload as Parameters<typeof bookingsAPI.create>[0]);
      navigation.replace('BookingConfirmation', {booking: res.data.booking});
    } catch (err: unknown) {
      const msg = (err as {response?: {data?: {error?: string}}})?.response?.data?.error || 'Booking failed';
      Toast.show({type: 'error', text1: 'Booking failed', text2: msg});
    } finally { setLoading(false); }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Checkout" />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.summary}>
          <Text style={styles.summaryType}>{type}</Text>
          <View style={styles.priceRow}>
            <Text style={styles.summaryLabel}>Amount</Text>
            <Text style={styles.summaryAmount}>{formatPrice(amount)}</Text>
          </View>
          {promoDiscount > 0 && (
            <View style={styles.priceRow}>
              <Text style={styles.discountLabel}>Promo Discount</Text>
              <Text style={styles.discountAmount}>– {formatPrice(promoDiscount)}</Text>
            </View>
          )}
          <View style={[styles.priceRow, styles.totalRow]}>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalAmount}>{formatPrice(finalAmount)}</Text>
          </View>
        </View>

        <Input label="Your Name" value={name} onChangeText={setName} placeholder="Full name" />
        <Input label="Phone (optional)" value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91…" />

        <View style={styles.promoRow}>
          <Input
            label="Promo Code" value={promo} onChangeText={setPromo}
            placeholder="SAVE10, FIRSTTRIP…"
            containerStyle={styles.promoInput}
            autoCapitalize="characters"
          />
          <Button title="Apply" onPress={applyPromo} loading={promoLoading} variant="outline" style={styles.promoBtn} />
        </View>

        <Button title={`Pay ${formatPrice(finalAmount)}`} onPress={handleBook} loading={loading} style={styles.btn} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#fff'},
  content: {padding: 20},
  summary: {backgroundColor: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 20},
  summaryType: {fontSize: 12, fontWeight: '700', color: '#6366f1', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1},
  priceRow: {flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4},
  summaryLabel: {fontSize: 14, color: '#64748b'},
  summaryAmount: {fontSize: 14, fontWeight: '700', color: '#1e293b'},
  discountLabel: {fontSize: 14, color: '#22c55e'},
  discountAmount: {fontSize: 14, fontWeight: '700', color: '#22c55e'},
  totalRow: {borderTopWidth: 1, borderTopColor: '#e2e8f0', paddingTop: 8, marginTop: 4},
  totalLabel: {fontSize: 16, fontWeight: '700', color: '#0f172a'},
  totalAmount: {fontSize: 20, fontWeight: '800', color: '#6366f1'},
  promoRow: {flexDirection: 'row', alignItems: 'flex-end', gap: 8},
  promoInput: {flex: 1},
  promoBtn: {marginBottom: 16, width: 80},
  btn: {marginTop: 8},
});
