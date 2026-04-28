import React, {useEffect} from 'react';
import {View, Text, FlatList, StyleSheet, SafeAreaView} from 'react-native';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {rewardsAPI} from '../../api/user';
import {useApi} from '../../hooks/useApi';
import {PointsTransaction} from '../../types';
import {relativeTime} from '../../utils/formatters';

const TIER_COLOR: Record<string, string> = {Silver: '#94a3b8', Gold: '#f59e0b', Platinum: '#8b5cf6'};

export default function RewardsScreen() {
  const {data, loading, error, execute} = useApi(rewardsAPI.get);

  useEffect(() => { execute(); }, []);

  const rewards = data?.rewards;
  const transactions = data?.transactions ?? [];

  return (
    <SafeAreaView style={styles.safe}>
      <Header title="Rewards & Points" />
      {loading ? <Loading fullScreen /> :
       error ? <ErrorView message={error} onRetry={execute} /> : (
        <FlatList
          data={transactions} keyExtractor={item => String(item.id)}
          ListHeaderComponent={rewards ? (
            <View>
              <View style={[styles.card, {borderColor: TIER_COLOR[rewards.tier]}]}>
                <Text style={[styles.tier, {color: TIER_COLOR[rewards.tier]}]}>{rewards.tier} Member</Text>
                <Text style={styles.points}>{rewards.points.toLocaleString()}</Text>
                <Text style={styles.pointsLabel}>Available Points</Text>
                <Text style={styles.lifetime}>Lifetime: {rewards.lifetime_points.toLocaleString()} pts</Text>
                {rewards.points_to_next_tier > 0 && (
                  <Text style={styles.next}>{rewards.points_to_next_tier} pts to {rewards.next_tier}</Text>
                )}
              </View>
              <Text style={styles.historyTitle}>Transaction History</Text>
            </View>
          ) : null}
          ListEmptyComponent={<Text style={styles.noTx}>No transactions yet</Text>}
          renderItem={({item}: {item: PointsTransaction}) => (
            <View style={styles.txRow}>
              <Text style={styles.txEmoji}>{item.type === 'EARN' ? '⬆️' : '⬇️'}</Text>
              <View style={styles.txInfo}>
                <Text style={styles.txDesc}>{item.description ?? item.type}</Text>
                <Text style={styles.txTime}>{relativeTime(item.created_at)}</Text>
              </View>
              <Text style={[styles.txPoints, {color: item.type === 'EARN' ? '#22c55e' : '#ef4444'}]}>
                {item.type === 'EARN' ? '+' : '-'}{Math.abs(item.points)} pts
              </Text>
            </View>
          )}
          contentContainerStyle={styles.list}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  list: {padding: 16},
  card: {backgroundColor: '#1e1b4b', borderRadius: 16, padding: 24, alignItems: 'center', marginBottom: 24, borderWidth: 2},
  tier: {fontSize: 14, fontWeight: '700', letterSpacing: 2},
  points: {fontSize: 48, fontWeight: '800', color: '#fff', marginTop: 8},
  pointsLabel: {fontSize: 14, color: '#a5b4fc', marginTop: -4},
  lifetime: {fontSize: 12, color: '#818cf8', marginTop: 8},
  next: {fontSize: 12, color: '#c7d2fe', marginTop: 4},
  historyTitle: {fontSize: 16, fontWeight: '700', color: '#0f172a', marginBottom: 12},
  noTx: {fontSize: 14, color: '#94a3b8', textAlign: 'center', padding: 16},
  txRow: {flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 10, padding: 12, marginBottom: 8},
  txEmoji: {fontSize: 20, marginRight: 12},
  txInfo: {flex: 1},
  txDesc: {fontSize: 14, color: '#0f172a', fontWeight: '500'},
  txTime: {fontSize: 12, color: '#94a3b8', marginTop: 2},
  txPoints: {fontSize: 15, fontWeight: '700'},
});
