import React, {useEffect, useState} from 'react';
import {View, Text, FlatList, TouchableOpacity, Modal, StyleSheet, SafeAreaView, ScrollView, Alert} from 'react-native';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import {priceAlertsAPI} from '../../api/user';
import {useApi} from '../../hooks/useApi';
import {PriceAlert} from '../../types';
import {formatPrice, formatDate} from '../../utils/formatters';
import Toast from 'react-native-toast-message';

export default function PriceAlertsScreen() {
  const {data, loading, execute} = useApi(priceAlertsAPI.list);
  const [showForm, setShowForm] = useState(false);
  const [type, setType] = useState('FLIGHT');
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [city, setCity] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { execute(); }, []);

  const save = async () => {
    if (!targetPrice) { Toast.show({type: 'error', text1: 'Target price required'}); return; }
    setSaving(true);
    try {
      await priceAlertsAPI.create({alert_type: type, origin: origin || undefined, destination: destination || undefined, city: city || undefined, target_price: parseFloat(targetPrice)});
      Toast.show({type: 'success', text1: 'Price alert created!'});
      setShowForm(false);
      execute();
    } catch { Toast.show({type: 'error', text1: 'Failed to create alert'}); }
    finally { setSaving(false); }
  };

  const remove = (id: number) => {
    Alert.alert('Delete Alert', 'Remove this price alert?', [
      {text: 'Cancel', style: 'cancel'},
      {text: 'Delete', style: 'destructive', onPress: async () => { await priceAlertsAPI.delete(id); execute(); }},
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Price Alerts" />
      {loading ? <Loading fullScreen /> : (
        <FlatList
          data={data?.alerts ?? []} keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListHeaderComponent={<Button title="+ New Alert" onPress={() => setShowForm(true)} variant="outline" style={styles.addBtn} />}
          ListEmptyComponent={<Text style={styles.empty}>No price alerts. Create one to get notified!</Text>}
          renderItem={({item}: {item: PriceAlert}) => (
            <View style={styles.card}>
              <View style={styles.info}>
                <Text style={styles.type}>{item.alert_type} {item.triggered ? '🔔' : '⏳'}</Text>
                <Text style={styles.route}>{item.origin ? `${item.origin} → ${item.destination}` : item.city}</Text>
                <Text style={styles.target}>Target: {formatPrice(item.target_price)}</Text>
                <Text style={styles.created}>{formatDate(item.created_at)}</Text>
              </View>
              <TouchableOpacity onPress={() => remove(item.id)}>
                <Text style={styles.del}>🗑️</Text>
              </TouchableOpacity>
            </View>
          )}
        />
      )}
      <Modal visible={showForm} animationType="slide" presentationStyle="pageSheet">
        <SafeAreaView style={styles.modal}>
          <Header title="New Price Alert" />
          <ScrollView contentContainerStyle={styles.formContent} keyboardShouldPersistTaps="handled">
            <View style={styles.typeRow}>
              {['FLIGHT', 'HOTEL'].map(t => (
                <TouchableOpacity key={t} style={[styles.typeBtn, type === t && styles.typeBtnActive]} onPress={() => setType(t)}>
                  <Text style={[styles.typeBtnText, type === t && styles.typeBtnTextActive]}>{t}</Text>
                </TouchableOpacity>
              ))}
            </View>
            {type === 'FLIGHT' ? (
              <>
                <Input label="Origin" value={origin} onChangeText={setOrigin} placeholder="Delhi" />
                <Input label="Destination" value={destination} onChangeText={setDestination} placeholder="Goa" />
              </>
            ) : (
              <Input label="City" value={city} onChangeText={setCity} placeholder="Mumbai" />
            )}
            <Input label="Target Price (₹)" value={targetPrice} onChangeText={setTargetPrice} keyboardType="numeric" placeholder="5000" />
            <Button title="Create Alert" onPress={save} loading={saving} style={styles.btn} />
            <Button title="Cancel" onPress={() => setShowForm(false)} variant="secondary" style={styles.cancelBtn} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  list: {padding: 16, gap: 10},
  addBtn: {marginBottom: 16},
  card: {backgroundColor: '#fff', borderRadius: 12, padding: 14, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 6, elevation: 2},
  info: {flex: 1},
  type: {fontSize: 12, fontWeight: '700', color: '#6366f1', textTransform: 'uppercase'},
  route: {fontSize: 15, fontWeight: '700', color: '#0f172a', marginTop: 2},
  target: {fontSize: 13, color: '#374151', marginTop: 2},
  created: {fontSize: 11, color: '#94a3b8', marginTop: 2},
  del: {fontSize: 18, paddingLeft: 8},
  empty: {fontSize: 14, color: '#94a3b8', textAlign: 'center', padding: 24},
  modal: {flex: 1, backgroundColor: '#fff'},
  formContent: {padding: 20},
  typeRow: {flexDirection: 'row', gap: 12, marginBottom: 16},
  typeBtn: {flex: 1, padding: 12, borderRadius: 10, borderWidth: 1.5, borderColor: '#e2e8f0', alignItems: 'center'},
  typeBtnActive: {borderColor: '#6366f1', backgroundColor: '#eef2ff'},
  typeBtnText: {fontSize: 14, fontWeight: '700', color: '#94a3b8'},
  typeBtnTextActive: {color: '#6366f1'},
  btn: {},
  cancelBtn: {marginTop: 10},
});
