import React, {useEffect, useState} from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  FlatList, Image, SafeAreaView,
} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {HomeStackParamList, Destination} from '../../types';
import {useAuth} from '../../context/AuthContext';
import {destinationsAPI} from '../../api/user';
import {formatPrice} from '../../utils/formatters';

type Nav = NativeStackNavigationProp<HomeStackParamList>;

const SERVICES = [
  {id: 'flights', label: 'Flights', emoji: '✈️', screen: 'FlightSearch'},
  {id: 'hotels', label: 'Hotels', emoji: '🏨', screen: 'HotelSearch'},
  {id: 'buses', label: 'Buses', emoji: '🚌', screen: 'BusSearch'},
  {id: 'trains', label: 'Trains', emoji: '🚆', screen: 'TrainSearch'},
  {id: 'cabs', label: 'Cabs', emoji: '🚕', screen: 'CabSearch'},
  {id: 'packages', label: 'Packages', emoji: '🌴', screen: 'Packages'},
  {id: 'activities', label: 'Activities', emoji: '🎯', screen: 'Activities'},
  {id: 'insurance', label: 'Insurance', emoji: '🛡️', screen: 'Insurance'},
] as const;

export default function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const {user} = useAuth();
  const [destinations, setDestinations] = useState<Destination[]>([]);

  useEffect(() => {
    destinationsAPI.popular(8).then(res => setDestinations(res.data.destinations)).catch(() => {});
  }, []);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>{greeting()} 👋</Text>
            <Text style={styles.userEmail}>{user?.email}</Text>
          </View>
          <Text style={styles.logoMini}>✈️</Text>
        </View>

        {/* Hero */}
        <View style={styles.hero}>
          <Text style={styles.heroTitle}>Where to next?</Text>
          <Text style={styles.heroSub}>Flights · Hotels · Buses · Trains · Cabs · Packages</Text>
        </View>

        {/* Service Grid */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Explore Services</Text>
          <View style={styles.grid}>
            {SERVICES.map(svc => (
              <TouchableOpacity
                key={svc.id}
                style={styles.tile}
                onPress={() => navigation.navigate(svc.screen as keyof HomeStackParamList)}>
                <Text style={styles.tileEmoji}>{svc.emoji}</Text>
                <Text style={styles.tileLabel}>{svc.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Popular Destinations */}
        {destinations.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Popular Destinations</Text>
            <FlatList
              data={destinations}
              horizontal
              showsHorizontalScrollIndicator={false}
              keyExtractor={item => item.destination}
              contentContainerStyle={styles.destList}
              renderItem={({item}) => (
                <TouchableOpacity
                  style={styles.destCard}
                  onPress={() => navigation.navigate('Packages')}>
                  <View style={styles.destImg}>
                    <Text style={styles.destEmoji}>🏝️</Text>
                  </View>
                  <Text style={styles.destName}>{item.destination}</Text>
                  <Text style={styles.destPrice}>from {formatPrice(item.starting_price)}</Text>
                </TouchableOpacity>
              )}
            />
          </View>
        )}

        <View style={styles.bottomPad} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: '#f8fafc'},
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: 16, paddingBottom: 8, backgroundColor: '#0f172a',
  },
  greeting: {fontSize: 13, color: '#94a3b8'},
  userEmail: {fontSize: 15, fontWeight: '700', color: '#fff'},
  logoMini: {fontSize: 28},
  hero: {
    backgroundColor: '#0f172a', paddingHorizontal: 20,
    paddingBottom: 28, paddingTop: 4,
  },
  heroTitle: {fontSize: 28, fontWeight: '800', color: '#fff'},
  heroSub: {fontSize: 13, color: '#64748b', marginTop: 4},
  section: {paddingHorizontal: 20, marginTop: 24},
  sectionTitle: {fontSize: 17, fontWeight: '700', color: '#0f172a', marginBottom: 14},
  grid: {flexDirection: 'row', flexWrap: 'wrap', gap: 12},
  tile: {
    width: '22%', aspectRatio: 1, backgroundColor: '#fff', borderRadius: 14,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, shadowOffset: {width: 0, height: 2},
    elevation: 2,
  },
  tileEmoji: {fontSize: 24},
  tileLabel: {fontSize: 11, fontWeight: '600', color: '#374151', marginTop: 4},
  destList: {paddingRight: 8},
  destCard: {
    width: 140, marginRight: 12, backgroundColor: '#fff',
    borderRadius: 12, overflow: 'hidden',
    shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 6, elevation: 2,
  },
  destImg: {height: 90, backgroundColor: '#e0e7ff', alignItems: 'center', justifyContent: 'center'},
  destEmoji: {fontSize: 36},
  destName: {fontSize: 13, fontWeight: '700', color: '#1e293b', paddingHorizontal: 10, paddingTop: 8},
  destPrice: {fontSize: 12, color: '#6366f1', paddingHorizontal: 10, paddingBottom: 10, marginTop: 2},
  bottomPad: {height: 32},
});
