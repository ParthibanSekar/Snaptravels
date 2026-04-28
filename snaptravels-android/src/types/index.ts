// ============================================================
//  SnapTravels — Shared TypeScript Types
// ============================================================

export interface User {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

// ── Flights ──────────────────────────────────────────────────
export interface Flight {
  id: number;
  airline: string;
  flight_number: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  depart_date: string | null;
  price: number;
  duration_mins: number;
  available_seats: number;
  cabin_class: string;
}

// ── Hotels ───────────────────────────────────────────────────
export interface Hotel {
  id: number;
  name: string;
  city: string;
  rating: number;
  price_per_night: number;
  amenities: string;
  image_path: string | null;
  description: string | null;
}

// ── Buses ────────────────────────────────────────────────────
export interface Bus {
  id: number;
  bus_no: string;
  operator: string;
  origin: string;
  destination: string;
  depart_time: string;
  arrive_time: string;
  duration_mins: number;
  bus_type: string;
  price: number;
  seats_left: number;
  amenities: string[];
}

// ── Trains ───────────────────────────────────────────────────
export interface TrainClass {
  class: 'SL' | '3A' | '2A' | '1A';
  fare: number;
  seats_available: number;
}

export interface Train {
  id: number;
  train_no: string;
  train_name: string;
  train_type: string;
  run_days: string;
  origin: string;
  destination: string;
  depart_time: string;
  arrive_time: string;
  duration_mins: number;
  distance_km: number;
  classes: TrainClass[];
}

// ── Cabs ─────────────────────────────────────────────────────
export interface Cab {
  id: number;
  vehicle_type: string;
  brand: string;
  base_fare: number;
  base_km: number;
  base_amount: number;
  capacity: number;
  ac: boolean;
  image_path: string | null;
  estimated_fare: number;
}

// ── Packages ─────────────────────────────────────────────────
export interface Package {
  id: number;
  name: string;
  slug: string;
  destination: string;
  country: string;
  tag: string | null;
  description: string | null;
  duration_nights: number;
  base_price: number;
  original_price: number | null;
  discount_pct: number;
  image_path: string | null;
  includes_flight: boolean;
  includes_hotel: boolean;
  includes_meals: boolean;
  includes_transfers: boolean;
  max_persons: number;
  bookings_today: number;
  highlights?: string[];
  itinerary?: ItineraryDay[];
}

export interface ItineraryDay {
  day: number;
  title: string;
  activities: string[];
}

// ── Activities ───────────────────────────────────────────────
export interface Activity {
  id: number;
  name: string;
  city: string;
  category: string;
  description: string | null;
  price_per_person: number;
  original_price: number | null;
  discount_pct: number;
  duration_hours: number;
  duration_label: string;
  min_persons: number;
  max_persons: number;
  rating: number;
  review_count: number;
  image_path: string | null;
  includes: string[];
}

// ── Insurance ────────────────────────────────────────────────
export interface CoverageItem {
  label: string;
  limit?: string;
}

export interface InsurancePlan {
  id: number;
  name: string;
  description: string | null;
  price_per_person_per_day: number;
  medical_cover: number;
  trip_cancellation: boolean;
  baggage_loss: boolean;
  flight_delay: boolean;
  adventure_sports: boolean;
  highlighted: boolean;
  tagline: string;
  color: string;
  coverage: CoverageItem[];
}

// ── Bookings ─────────────────────────────────────────────────
export interface BookingItem {
  type: string;
  title: string;
  amount: number;
  details: string | null;
  flight?: Partial<Flight>;
  hotel?: Partial<Hotel>;
}

export interface Booking {
  id: number;
  booking_code: string;
  status: string;
  total_amount: number;
  currency: string;
  created_at: string;
  customer_name: string;
  customer_email: string;
  customer_phone?: string;
  items: BookingItem[];
}

// ── Wishlist ──────────────────────────────────────────────────
export interface WishlistItem {
  id: number;
  item_type: 'FLIGHT' | 'HOTEL' | 'PACKAGE' | 'ACTIVITY';
  ref_id: number;
  created_at: string;
  detail?: Record<string, unknown>;
}

// ── Reviews ───────────────────────────────────────────────────
export interface Review {
  id: number;
  rating: number;
  stars: string;
  title: string | null;
  comment: string | null;
  verified_booking: boolean;
  created_at: string;
  user: string;
}

// ── Notifications ─────────────────────────────────────────────
export interface Notification {
  id: number;
  type: 'BOOKING' | 'CANCELLATION' | 'OFFER' | 'INFO';
  title: string;
  message: string | null;
  link: string | null;
  read: boolean;
  created_at: string;
}

// ── Traveler Profiles ─────────────────────────────────────────
export interface TravelerProfile {
  id: number;
  full_name: string;
  gender: string | null;
  age: number | null;
  date_of_birth: string | null;
  nationality: string;
  id_type: string | null;
  id_number: string | null;
  passport_no: string | null;
  is_primary: boolean;
}

// ── Rewards ───────────────────────────────────────────────────
export interface PointsTransaction {
  id: number;
  points: number;
  type: 'EARN' | 'REDEEM';
  description: string | null;
  created_at: string;
}

export interface Rewards {
  points: number;
  lifetime_points: number;
  tier: 'Silver' | 'Gold' | 'Platinum';
  next_tier: string;
  points_to_next_tier: number;
}

// ── Price Alerts ──────────────────────────────────────────────
export interface PriceAlert {
  id: number;
  alert_type: 'FLIGHT' | 'HOTEL';
  origin: string | null;
  destination: string | null;
  city: string | null;
  target_price: number;
  triggered: boolean;
  created_at: string;
}

// ── Popular Destinations ──────────────────────────────────────
export interface Destination {
  destination: string;
  image_path: string | null;
  starting_price: number;
  package_count?: number;
  hotel_count?: number;
}

// ── Navigation ────────────────────────────────────────────────
export type RootStackParamList = {
  Splash: undefined;
  Auth: undefined;
  Main: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

export type MainTabParamList = {
  HomeTab: undefined;
  BookingsTab: undefined;
  WishlistTab: undefined;
  NotificationsTab: undefined;
  ProfileTab: undefined;
};

export type HomeStackParamList = {
  Home: undefined;
  FlightSearch: undefined;
  FlightResults: {origin: string; destination: string; date: string; passengers: number};
  FlightDetail: {flight: Flight};
  HotelSearch: undefined;
  HotelResults: {city: string; checkin: string; checkout: string; guests: number};
  HotelDetail: {hotel: Hotel};
  BusSearch: undefined;
  BusResults: {origin: string; destination: string; date: string};
  BusDetail: {bus: Bus};
  TrainSearch: undefined;
  TrainResults: {origin: string; destination: string; date: string};
  TrainDetail: {train: Train};
  CabSearch: undefined;
  CabResults: {pickup: string; drop: string; distance_km: number};
  CabDetail: {cab: Cab};
  Packages: undefined;
  PackageDetail: {slug: string};
  Activities: undefined;
  ActivityDetail: {id: number};
  Insurance: undefined;
  InsuranceDetail: {plan: InsurancePlan};
  Checkout: {type: string; item: unknown; amount: number};
  BookingConfirmation: {booking: Booking};
};

export type BookingsStackParamList = {
  BookingsList: undefined;
  BookingDetail: {bookingId: number};
};

export type ProfileStackParamList = {
  ProfileHome: undefined;
  EditProfile: undefined;
  Travelers: undefined;
  AddTraveler: undefined;
  Rewards: undefined;
  PriceAlerts: undefined;
  ChangePassword: undefined;
};
