import React, {useEffect} from 'react';
import {View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {HomeStackParamList, Hotel} from '../../types';
import Header from '../../components/common/Header';
import Loading from '../../components/common/Loading';
import ErrorView from '../../components/common/ErrorView';
import {hotelsAPI} from '../../api/hotels';
import {useApi} from '../../hooks/useApi';
import {formatPrice} from '../../utils/formatters';

type Props = NativeStackScreenProps<HomeStackParamList, 'HotelResults'>;

function StarRating({rating}: {rating: number}) {
  return (
    <Text style={styles.stars}>
      {'★'.repeat(Math.round(rating))}{'☆'.repeat(5 - Math.round(rating))}
      {' '}{rating.toFixed(1)}
    </Text>
  );
}

function HotelCard({hotel, onPress}: {hotel: Hotel; onPress: () => void}) {
  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <View style={styles.imgPlaceholder}>
        <Text style={styles.imgEmoji}>🏨</Text>
      </View>
      <View style={styles.info}>
        <Text style={styles.name} numberOfLines={1}>{hotel.name}</Text>
        <Text style={styles.city}>{hotel.city}</Text>
        <StarRating rating={hotel.rating} />
        <View style={styles.footer}>
          <Text style={styles.price}>{formatPrice(hotel.price_per_night)}<Text style={styles.perNight}>/night</Text></Text>
        </View>
      </View>
    </TouchableOpacity>
  );
}

export default function HotelResultsScreen({route, navigation}: Props) {
  const {city, checkin, checkout, guests} = route.params;
  const {data, loading, error, execute} = useApi(hotelsAPI.search);

  useEffect(() => {
    execute({city, checkin, checkout, guests});
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header title={`Hotels in ${city}`} />
      {loading ? (
        <Loading message="Searching hotels…" fullScreen />
      ) : error ? (
        <ErrorView message={error} onRetry={() => execute({city, checkin, checkout, guests})} />
      ) : (
        <FlatList
          data={data?.hotels ?? []}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<ErrorView message="No hotels found in this city." />}
          renderItem={({item}) => (
            <HotelCard hotel={item} onPress={() => navigation.navigate('HotelDetail', {hotel: item})} />
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
    backgroundColor: '#fff', borderRadius: 14, overflow: 'hidden',
    flexDirection: 'row',
    shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 2,
  },
  imgPlaceholder: {width: 90, backgroundColor: '#e0e7ff', alignItems: 'center', justifyContent: 'center'},
  imgEmoji: {fontSize: 32},
  info: {flex: 1, padding: 12},
  name: {fontSize: 15, fontWeight: '700', color: '#0f172a'},
  city: {fontSize: 12, color: '#64748b', marginTop: 2},
  stars: {fontSize: 12, color: '#f59e0b', marginTop: 4},
  footer: {flexDirection: 'row', justifyContent: 'flex-end', marginTop: 8},
  price: {fontSize: 18, fontWeight: '800', color: '#6366f1'},
  perNight: {fontSize: 12, fontWeight: '400', color: '#94a3b8'},
});
