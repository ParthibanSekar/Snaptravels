
# SnapTravels Mobile App Integration Guide

## Overview
SnapTravels is now fully prepared for native mobile app development with React Native, Flutter, or other mobile frameworks.

## Key Features Added

### 1. Mobile API Endpoints (`/mobile-api/v1/`)
- JWT-based authentication
- RESTful API design
- Comprehensive flight and hotel search
- Booking management
- User profile management
- App configuration endpoint

### 2. Progressive Web App (PWA) Support
- Service Worker for offline functionality
- Web App Manifest for native app-like experience
- Install prompts for mobile browsers
- Push notification support
- Background sync capabilities

### 3. Mobile-Optimized UI/UX
- Touch-friendly interface design
- Mobile-first responsive layout
- Native app-style navigation
- Haptic feedback simulation
- Pull-to-refresh functionality
- Offline indicators

## Mobile App Development Options

### Option 1: React Native
```javascript
// API Integration Example
const API_BASE = 'https://snaptravels.online/mobile-api/v1';

const login = async (email, password) => {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return response.json();
};

const searchFlights = async (origin, destination) => {
  const token = await AsyncStorage.getItem('token');
  const response = await fetch(`${API_BASE}/flights/search?origin=${origin}&destination=${destination}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

### Option 2: Flutter
```dart
// API Integration Example
class SnapTravelsAPI {
  static const String baseUrl = 'https://snaptravels.online/mobile-api/v1';
  
  static Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'email': email, 'password': password}),
    );
    return json.decode(response.body);
  }
  
  static Future<List<Flight>> searchFlights(String origin, String destination) async {
    final token = await storage.read(key: 'token');
    final response = await http.get(
      Uri.parse('$baseUrl/flights/search?origin=$origin&destination=$destination'),
      headers: {'Authorization': 'Bearer $token'},
    );
    // Parse and return flights
  }
}
```

### Option 3: WebView Wrapper
```javascript
// For hybrid apps using WebView
window.addEventListener('message', function(event) {
  const { action, data } = JSON.parse(event.data);
  
  switch(action) {
    case 'LOGIN':
      // Handle native login
      break;
    case 'BOOK_FLIGHT':
      // Handle native booking
      break;
    case 'GET_LOCATION':
      // Get device location
      break;
  }
});
```

## API Endpoints for Mobile App

### Authentication
- `POST /mobile-api/v1/auth/register` - User registration
- `POST /mobile-api/v1/auth/login` - User login
- `POST /mobile-api/v1/auth/refresh` - Refresh JWT token

### Search
- `GET /mobile-api/v1/flights/search` - Search flights
- `GET /mobile-api/v1/hotels/search` - Search hotels

### Bookings
- `POST /mobile-api/v1/bookings` - Create booking
- `GET /mobile-api/v1/bookings` - Get user bookings

### User Management
- `GET /mobile-api/v1/user/profile` - Get user profile
- `GET /mobile-api/v1/config` - Get app configuration

## PWA Installation
Users can install the PWA directly from their mobile browser:
- Chrome/Edge: "Add to Home Screen"
- Safari: "Add to Home Screen"
- Firefox: "Install App"

## Push Notifications Setup
1. Generate VAPID keys for web push
2. Update service worker with your VAPID public key
3. Implement server-side push notification sending
4. Handle notification permissions in the app

## Offline Support
- Service worker caches essential resources
- Background sync for failed requests
- Offline page for no connectivity
- Local storage for temporary data

## Mobile App Features Ready
✅ JWT Authentication
✅ RESTful API endpoints
✅ Push notification support
✅ Offline functionality
✅ Mobile-optimized UI
✅ Touch gestures support
✅ Native app install prompts
✅ Background sync
✅ Device integration ready
✅ App store preparation ready

## Next Steps for Mobile App Development
1. Choose mobile framework (React Native/Flutter/Native)
2. Set up development environment
3. Integrate API endpoints
4. Implement authentication flow
5. Add push notification service
6. Test on devices
7. Publish to app stores

## Production Deployment Notes
- API is production-ready at `https://snaptravels.online/mobile-api/v1/`
- PWA is accessible at `https://snaptravels.online`
- All mobile features are live and functional
- Ready for app store submission
