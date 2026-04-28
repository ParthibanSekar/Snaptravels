# SnapTravels Android

React Native (TypeScript) app for [snaptravels.online](https://snaptravels.online).

## Features

- ✈️ Flights search & booking
- 🏨 Hotels search & booking
- 🚌 Buses search
- 🚆 Trains search (class-wise fares)
- 🚕 Cab fare estimator & booking
- 🌴 Holiday Packages (list, detail, book)
- 🎯 Activities & Experiences
- 🛡️ Travel Insurance plans
- 🎫 Booking history & cancellation
- ❤️ Wishlist (Flights, Hotels, Packages, Activities)
- 🔔 Notifications (with unread badge)
- ⭐ Rewards & Loyalty Points
- 💸 Price Alerts (Flight & Hotel)
- 🎟️ Promo Code validation at checkout
- 👥 Saved Traveler Profiles
- 👤 Profile edit, change password
- 🌍 Popular Destinations on Home

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | React Native 0.73 |
| Language | TypeScript |
| Navigation | React Navigation 6 (Stack + Bottom Tabs) |
| HTTP | Axios with JWT interceptors |
| Auth Storage | AsyncStorage |
| UI | Custom components (no third-party UI kit) |
| State | React Context + useReducer (Auth) |

## Project Structure

```
snaptravels-android/
├── App.tsx                 # Root: providers + AppNavigator
├── index.js
├── src/
│   ├── api/               # Axios API modules (one per domain)
│   │   ├── client.ts      # Base Axios instance + JWT interceptor
│   │   ├── auth.ts
│   │   ├── flights.ts
│   │   ├── hotels.ts
│   │   ├── transport.ts   # Buses, Trains, Cabs
│   │   ├── packages.ts    # Packages + Activities
│   │   ├── bookings.ts    # Bookings + Insurance
│   │   └── user.ts        # Profile, Travelers, Rewards, Wishlist,
│   │                        Reviews, Notifications, Promos, PriceAlerts
│   ├── context/
│   │   └── AuthContext.tsx  # JWT auth with AsyncStorage persistence
│   ├── hooks/
│   │   └── useApi.ts       # Generic API hook (loading/error/data)
│   ├── navigation/
│   │   ├── AppNavigator.tsx   # Root switch: Auth vs Main
│   │   ├── AuthNavigator.tsx  # Login + Register
│   │   └── MainNavigator.tsx  # 5-tab + nested stacks
│   ├── screens/
│   │   ├── auth/           SplashScreen, LoginScreen, RegisterScreen
│   │   ├── home/           HomeScreen (service grid + popular destinations)
│   │   ├── flights/        FlightSearch, FlightResults, FlightDetail
│   │   ├── hotels/         HotelSearch, HotelResults, HotelDetail
│   │   ├── buses/          BusSearch, BusResults
│   │   ├── trains/         TrainSearch, TrainResults
│   │   ├── cabs/           CabSearch, CabResults
│   │   ├── packages/       PackagesScreen, PackageDetailScreen
│   │   ├── activities/     ActivitiesScreen, ActivityDetailScreen
│   │   ├── insurance/      InsuranceScreen
│   │   ├── bookings/       BookingsList, BookingDetail, Checkout,
│   │   │                    BookingConfirmation
│   │   ├── wishlist/       WishlistScreen
│   │   ├── notifications/  NotificationsScreen
│   │   └── profile/        ProfileHome, EditProfile, Travelers,
│   │                        AddTraveler, Rewards, PriceAlerts, ChangePassword
│   ├── components/
│   │   └── common/         Button, Input, Header, Loading, ErrorView
│   ├── types/
│   │   └── index.ts        All TypeScript interfaces + navigation param lists
│   └── utils/
│       └── formatters.ts   formatPrice, formatDate, formatDuration, etc.
```

## Quick Start

### Prerequisites

- Node.js 18+
- Android Studio (Android SDK, emulator or device)
- Java 17

### Setup

```bash
cd snaptravels-android

# Install dependencies
npm install

# Android
npx react-native run-android
```

### Connect to API

Edit `src/api/client.ts` and change `BASE_URL`:

```ts
// Production
export const BASE_URL = 'https://snaptravels.online/mobile-api/v1';

// Local development (Android emulator)
export const BASE_URL = 'http://10.0.2.2:5000/mobile-api/v1';
```

## API Endpoints Used

All endpoints are under `/mobile-api/v1` on the Flask backend:

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | /auth/login | — |
| POST | /auth/register | — |
| POST | /auth/logout | ✓ |
| POST | /auth/change-password | ✓ |
| GET | /flights/search | — |
| GET | /hotels/search | — |
| GET | /buses/search | — |
| GET | /trains/search | — |
| GET | /cabs/search | — |
| GET | /packages | — |
| GET | /packages/:slug | — |
| GET | /activities | — |
| GET | /activities/:id | — |
| GET | /insurance/plans | — |
| GET+POST | /bookings | ✓ |
| GET+PUT | /bookings/:id | ✓ |
| PUT | /bookings/:id/cancel | ✓ |
| GET+PUT | /user/profile | ✓ |
| GET+POST+DELETE | /user/travelers | ✓ |
| GET | /user/rewards | ✓ |
| GET+POST+DELETE | /wishlist | ✓ |
| GET+POST | /reviews | ✓ |
| GET+PUT | /notifications | ✓ |
| POST | /promo/validate | ✓ |
| GET+POST+DELETE | /price-alerts | ✓ |
| GET | /destinations/popular | — |
| GET | /autocomplete | — |

## Building APK

```bash
cd android
./gradlew assembleRelease
# APK: android/app/build/outputs/apk/release/app-release.apk
```
