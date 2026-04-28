import React from 'react';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {MainTabParamList, HomeStackParamList, BookingsStackParamList, ProfileStackParamList} from '../types';

// Tab screens
import HomeScreen from '../screens/home/HomeScreen';
import BookingsListScreen from '../screens/bookings/BookingsListScreen';
import BookingDetailScreen from '../screens/bookings/BookingDetailScreen';
import WishlistScreen from '../screens/wishlist/WishlistScreen';
import NotificationsScreen from '../screens/notifications/NotificationsScreen';

// Profile stack
import ProfileHomeScreen from '../screens/profile/ProfileHomeScreen';
import EditProfileScreen from '../screens/profile/EditProfileScreen';
import TravelersScreen from '../screens/profile/TravelersScreen';
import AddTravelerScreen from '../screens/profile/AddTravelerScreen';
import RewardsScreen from '../screens/profile/RewardsScreen';
import PriceAlertsScreen from '../screens/profile/PriceAlertsScreen';
import ChangePasswordScreen from '../screens/profile/ChangePasswordScreen';

// Home/search stack screens
import FlightSearchScreen from '../screens/flights/FlightSearchScreen';
import FlightResultsScreen from '../screens/flights/FlightResultsScreen';
import FlightDetailScreen from '../screens/flights/FlightDetailScreen';
import HotelSearchScreen from '../screens/hotels/HotelSearchScreen';
import HotelResultsScreen from '../screens/hotels/HotelResultsScreen';
import HotelDetailScreen from '../screens/hotels/HotelDetailScreen';
import BusSearchScreen from '../screens/buses/BusSearchScreen';
import BusResultsScreen from '../screens/buses/BusResultsScreen';
import TrainSearchScreen from '../screens/trains/TrainSearchScreen';
import TrainResultsScreen from '../screens/trains/TrainResultsScreen';
import CabSearchScreen from '../screens/cabs/CabSearchScreen';
import CabResultsScreen from '../screens/cabs/CabResultsScreen';
import PackagesScreen from '../screens/packages/PackagesScreen';
import PackageDetailScreen from '../screens/packages/PackageDetailScreen';
import ActivitiesScreen from '../screens/activities/ActivitiesScreen';
import ActivityDetailScreen from '../screens/activities/ActivityDetailScreen';
import InsuranceScreen from '../screens/insurance/InsuranceScreen';
import CheckoutScreen from '../screens/bookings/CheckoutScreen';
import BookingConfirmationScreen from '../screens/bookings/BookingConfirmationScreen';

const Tab = createBottomTabNavigator<MainTabParamList>();
const HomeStack = createNativeStackNavigator<HomeStackParamList>();
const BookingsStack = createNativeStackNavigator<BookingsStackParamList>();
const ProfileStack = createNativeStackNavigator<ProfileStackParamList>();

function HomeStackNavigator() {
  return (
    <HomeStack.Navigator screenOptions={{headerShown: false}}>
      <HomeStack.Screen name="Home" component={HomeScreen} />
      <HomeStack.Screen name="FlightSearch" component={FlightSearchScreen} />
      <HomeStack.Screen name="FlightResults" component={FlightResultsScreen} />
      <HomeStack.Screen name="FlightDetail" component={FlightDetailScreen} />
      <HomeStack.Screen name="HotelSearch" component={HotelSearchScreen} />
      <HomeStack.Screen name="HotelResults" component={HotelResultsScreen} />
      <HomeStack.Screen name="HotelDetail" component={HotelDetailScreen} />
      <HomeStack.Screen name="BusSearch" component={BusSearchScreen} />
      <HomeStack.Screen name="BusResults" component={BusResultsScreen} />
      <HomeStack.Screen name="TrainSearch" component={TrainSearchScreen} />
      <HomeStack.Screen name="TrainResults" component={TrainResultsScreen} />
      <HomeStack.Screen name="CabSearch" component={CabSearchScreen} />
      <HomeStack.Screen name="CabResults" component={CabResultsScreen} />
      <HomeStack.Screen name="Packages" component={PackagesScreen} />
      <HomeStack.Screen name="PackageDetail" component={PackageDetailScreen} />
      <HomeStack.Screen name="Activities" component={ActivitiesScreen} />
      <HomeStack.Screen name="ActivityDetail" component={ActivityDetailScreen} />
      <HomeStack.Screen name="Insurance" component={InsuranceScreen} />
      <HomeStack.Screen name="Checkout" component={CheckoutScreen} />
      <HomeStack.Screen name="BookingConfirmation" component={BookingConfirmationScreen} />
    </HomeStack.Navigator>
  );
}

function BookingsStackNavigator() {
  return (
    <BookingsStack.Navigator screenOptions={{headerShown: false}}>
      <BookingsStack.Screen name="BookingsList" component={BookingsListScreen} />
      <BookingsStack.Screen name="BookingDetail" component={BookingDetailScreen} />
    </BookingsStack.Navigator>
  );
}

function ProfileStackNavigator() {
  return (
    <ProfileStack.Navigator screenOptions={{headerShown: false}}>
      <ProfileStack.Screen name="ProfileHome" component={ProfileHomeScreen} />
      <ProfileStack.Screen name="EditProfile" component={EditProfileScreen} />
      <ProfileStack.Screen name="Travelers" component={TravelersScreen} />
      <ProfileStack.Screen name="AddTraveler" component={AddTravelerScreen} />
      <ProfileStack.Screen name="Rewards" component={RewardsScreen} />
      <ProfileStack.Screen name="PriceAlerts" component={PriceAlertsScreen} />
      <ProfileStack.Screen name="ChangePassword" component={ChangePasswordScreen} />
    </ProfileStack.Navigator>
  );
}

export default function MainNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#6366f1',
        tabBarInactiveTintColor: '#64748b',
        tabBarStyle: {
          backgroundColor: '#ffffff',
          borderTopColor: '#e2e8f0',
          height: 60,
          paddingBottom: 8,
        },
        tabBarLabelStyle: {fontSize: 11, fontWeight: '600'},
      }}>
      <Tab.Screen
        name="HomeTab"
        component={HomeStackNavigator}
        options={{title: 'Explore', tabBarIcon: ({color}) => null}}
      />
      <Tab.Screen
        name="BookingsTab"
        component={BookingsStackNavigator}
        options={{title: 'Bookings', tabBarIcon: ({color}) => null}}
      />
      <Tab.Screen
        name="WishlistTab"
        component={WishlistScreen}
        options={{title: 'Wishlist', tabBarIcon: ({color}) => null}}
      />
      <Tab.Screen
        name="NotificationsTab"
        component={NotificationsScreen}
        options={{title: 'Alerts', tabBarIcon: ({color}) => null}}
      />
      <Tab.Screen
        name="ProfileTab"
        component={ProfileStackNavigator}
        options={{title: 'Profile', tabBarIcon: ({color}) => null}}
      />
    </Tab.Navigator>
  );
}
