import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, Alert, StyleSheet, SafeAreaView} from 'react-native';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {wishlistAPI} from '../../api/user';
import {useApi} from '../../hooks/useApi';
import {WishlistItem} from '../../types';
import {formatDate} from '../../utils/formatters';
import Toast from 'react-native-toast-message';

const TYPE_EMOJI: Record<string, string> = {FLIGHT: '✈️', HOTEL: '🏨', PACKAGE: '🌴', ACTIVITY: '🎯'};

export default function WishlistScreen() {
  const {data, loading, error, execute} = useApi(wishlistAPI.list);

  useEffect(() => { execute(); }, []);

  const remove = (id: number) => {
    Alert.alert('Remove from Wishlist', 'Remove this item from your wishlist?', [
      {text: 'Cancel', style: 'cancel'},
      {
        text: 'Remove',
        style: 'destructive',
        onPress: async () => {
          try {
            await wishlistAPI.remove(id);
            Toast.show({type: 'success', text1: 'Removed from wishlist'});
            execute();
          } catch { Toast.show({type: 'error', text1: 'Failed to remove'}); }
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="My Wishlist" showBack={false} />
      {loading ? <Loading fullScreen /> :
       error ? <ErrorView message={error} onRetry={execute} /> : (
        <FlatList
          data={data?.wishlist ?? []} keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emoji}>❤️</Text>
              <Text style={styles.emptyTitle}>Your wishlist is empty</Text>
              <Text style={styles.emptySub}>Save flights, hotels and packages for later!</Text>
            </View>
          }
          renderItem={({item}: {item: WishlistItem}) => (
            <View style={styles.card}>
              <Text style={styles.typeEmoji}>{TYPE_EMOJI[item.item_type] ?? '📌'}</Text>
              <View style={styles.info}>
                <Text style={styles.type}>{item.item_type}</Text>
                {item.detail && (
                  <Text style={styles.detail} numberOfLines={1}>
                    {(item.detail as Record<string, unknown>).name as string ||
                     (item.detail as Record<string, unknown>).airline as string ||
                     `ID: ${item.ref_id}`}
                  </Text>
                )}
                <Text style={styles.date}>{formatDate(item.created_at)}</Text>
              </View>
              <TouchableOpacity onPress={() => remove(item.id)} hitSlop={{top: 10, bottom: 10, left: 10, right: 10}}>
                <Text style={styles.removeBtn}>✕</Text>
              </TouchableOpacity>
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
  card: {backgroundColor: '#fff', borderRadius: 14, padding: 16, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2},
  typeEmoji: {fontSize: 32, marginRight: 12},
  info: {flex: 1},
  type: {fontSize: 11, fontWeight: '700', color: '#6366f1', textTransform: 'uppercase'},
  detail: {fontSize: 15, fontWeight: '600', color: '#0f172a', marginTop: 2},
  date: {fontSize: 12, color: '#94a3b8', marginTop: 2},
  removeBtn: {fontSize: 18, color: '#ef4444', paddingLeft: 8},
  empty: {alignItems: 'center', paddingTop: 80},
  emoji: {fontSize: 56, marginBottom: 16},
  emptyTitle: {fontSize: 18, fontWeight: '700', color: '#0f172a'},
  emptySub: {fontSize: 14, color: '#94a3b8', marginTop: 4, textAlign: 'center'},
});
