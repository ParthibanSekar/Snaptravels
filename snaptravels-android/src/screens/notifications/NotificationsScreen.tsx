import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import Button from '../../components/common/Button';
import {notificationsAPI} from '../../api/user';
import {useApi} from '../../hooks/useApi';
import {Notification} from '../../types';
import {relativeTime} from '../../utils/formatters';
import Toast from 'react-native-toast-message';

const TYPE_EMOJI: Record<string, string> = {BOOKING: '🎫', CANCELLATION: '❌', OFFER: '🎉', INFO: 'ℹ️'};

export default function NotificationsScreen() {
  const {data, loading, error, execute} = useApi(notificationsAPI.list);

  useEffect(() => { execute(); }, []);

  const markAllRead = async () => {
    try {
      await notificationsAPI.markAllRead();
      Toast.show({type: 'success', text1: 'All notifications marked as read'});
      execute();
    } catch { Toast.show({type: 'error', text1: 'Failed'}); }
  };

  const markRead = async (id: number) => {
    try {
      await notificationsAPI.markRead(id);
      execute();
    } catch {}
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Header
        title="Notifications"
        showBack={false}
        rightComponent={
          data?.unread_count ? (
            <TouchableOpacity onPress={markAllRead}>
              <Text style={styles.markAll}>Clear</Text>
            </TouchableOpacity>
          ) : undefined
        }
      />
      {loading ? <Loading fullScreen /> :
       error ? <ErrorView message={error} onRetry={execute} /> : (
        <FlatList
          data={data?.notifications ?? []} keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyEmoji}>🔔</Text>
              <Text style={styles.emptyTitle}>No notifications</Text>
              <Text style={styles.emptySub}>You're all caught up!</Text>
            </View>
          }
          renderItem={({item}: {item: Notification}) => (
            <TouchableOpacity
              style={[styles.item, !item.read && styles.itemUnread]}
              onPress={() => markRead(item.id)}>
              <Text style={styles.typeEmoji}>{TYPE_EMOJI[item.type] ?? '🔔'}</Text>
              <View style={styles.info}>
                <Text style={styles.title}>{item.title}</Text>
                {item.message ? <Text style={styles.message} numberOfLines={2}>{item.message}</Text> : null}
                <Text style={styles.time}>{relativeTime(item.created_at)}</Text>
              </View>
              {!item.read && <View style={styles.dot} />}
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  list: {padding: 12},
  markAll: {fontSize: 13, color: '#6366f1', fontWeight: '600'},
  item: {flexDirection: 'row', padding: 14, backgroundColor: '#fff', marginBottom: 8, borderRadius: 12, alignItems: 'flex-start'},
  itemUnread: {backgroundColor: '#eef2ff'},
  typeEmoji: {fontSize: 22, marginRight: 12, marginTop: 2},
  info: {flex: 1},
  title: {fontSize: 14, fontWeight: '700', color: '#0f172a'},
  message: {fontSize: 13, color: '#64748b', marginTop: 2, lineHeight: 18},
  time: {fontSize: 11, color: '#94a3b8', marginTop: 4},
  dot: {width: 8, height: 8, borderRadius: 4, backgroundColor: '#6366f1', marginTop: 6, marginLeft: 4},
  empty: {alignItems: 'center', paddingTop: 80},
  emptyEmoji: {fontSize: 56, marginBottom: 16},
  emptyTitle: {fontSize: 18, fontWeight: '700', color: '#0f172a'},
  emptySub: {fontSize: 14, color: '#94a3b8'},
});
