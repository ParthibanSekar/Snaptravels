import axios, {AxiosInstance, InternalAxiosRequestConfig, AxiosResponse} from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Toast from 'react-native-toast-message';

// Point this at your production or dev server
export const BASE_URL = 'https://snaptravels.online/mobile-api/v1';
// For local dev: export const BASE_URL = 'http://10.0.2.2:5000/mobile-api/v1';

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {'Content-Type': 'application/json'},
});

// Attach JWT from storage on every request
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await AsyncStorage.getItem('auth_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global error handler
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async error => {
    const message: string =
      error.response?.data?.error ||
      error.response?.data?.message ||
      error.message ||
      'Something went wrong';

    // 401 — expired / invalid token, force logout
    if (error.response?.status === 401) {
      await AsyncStorage.multiRemove(['auth_token', 'auth_user']);
      // Navigation reset happens via AuthContext listener
    }

    // 503 — chaos mode active
    if (error.response?.status === 503) {
      Toast.show({type: 'error', text1: 'Service Unavailable', text2: message});
    }

    return Promise.reject(error);
  },
);

export default api;
