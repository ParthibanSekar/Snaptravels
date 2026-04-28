import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, Alert, StyleSheet, SafeAreaView} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {ProfileStackParamList, TravelerProfile} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import {travelersAPI} from '../../api/user';
import {useApi} from '../../hooks/useApi';
import Toast from 'react-native-toast-message';
import Button from '../../components/common/Button';

type Nav = NativeStackNavigationProp<ProfileStackParamList>;

export default function TravelersScreen() {
  const navigation = useNavigation<Nav>();
  const {data, loading, error, execute} = useApi(travelersAPI.list);

  useEffect(() => { execute(); }, []);

  const remove = (id: number, name: string) => {
    Alert.alert('Delete Traveler', `Remove ${name}?`, [
      {text: 'Cancel', style: 'cancel'},
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          try { await travelersAPI.delete(id); execute(); } catch {
            Toast.show({type: 'error', text1: 'Failed to delete'});
          }
        },
      },
    ]);
  };

  if (loading) return <Loading fullScreen />;

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Saved Travelers" />
      <FlatList
        data={data?.travelers ?? []} keyExtractor={item => String(item.id)}
        contentContainerStyle={styles.list}
        ListHeaderComponent={<Button title="+ Add Traveler" onPress={() => navigation.navigate('AddTraveler')} variant="outline" style={styles.addBtn} />}
        ListEmptyComponent={<Text style={styles.empty}>No travelers saved. Add one!</Text>}
        renderItem={({item}: {item: TravelerProfile}) => (
          <View style={styles.card}>
            <View style={styles.info}>
              <Text style={styles.name}>{item.full_name} {item.is_primary ? '⭐' : ''}</Text>
              <Text style={styles.meta}>{[item.gender, item.nationality, item.id_type].filter(Boolean).join(' · ')}</Text>
            </View>
            <TouchableOpacity onPress={() => remove(item.id, item.full_name)}>
              <Text style={styles.del}>🗑️</Text>
            </TouchableOpacity>
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  list: {padding: 16, gap: 10},
  addBtn: {marginBottom: 16},
  card: {backgroundColor: '#fff', borderRadius: 12, padding: 14, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 6, elevation: 2},
  info: {flex: 1},
  name: {fontSize: 15, fontWeight: '700', color: '#0f172a'},
  meta: {fontSize: 12, color: '#64748b', marginTop: 2},
  del: {fontSize: 18, paddingLeft: 8},
  empty: {fontSize: 14, color: '#94a3b8', textAlign: 'center', padding: 24},
});
