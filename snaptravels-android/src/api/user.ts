import api from './client';
import {
  User, TravelerProfile, Rewards, PointsTransaction,
  WishlistItem, Review, Notification, PriceAlert, Destination,
} from '../types';

// ── Profile ──────────────────────────────────────────────────
export const profileAPI = {
  get: () =>
    api.get<{success: boolean; user: User}>('/user/profile'),

  update: (data: Partial<{full_name: string; phone: string; gender: string; date_of_birth: string; nationality: string}>) =>
    api.put<{success: boolean; message: string}>('/user/profile', data),
};

// ── Traveler Profiles ────────────────────────────────────────
export const travelersAPI = {
  list: () =>
    api.get<{success: boolean; travelers: TravelerProfile[]}>('/user/travelers'),

  add: (data: Omit<TravelerProfile, 'id'>) =>
    api.post<{success: boolean; id: number; message: string}>('/user/travelers', data),

  update: (id: number, data: Partial<TravelerProfile>) =>
    api.put<{success: boolean; message: string}>(`/user/travelers/${id}`, data),

  delete: (id: number) =>
    api.delete<{success: boolean; message: string}>(`/user/travelers/${id}`),
};

// ── Rewards ──────────────────────────────────────────────────
export const rewardsAPI = {
  get: () =>
    api.get<{success: boolean; rewards: Rewards; transactions: PointsTransaction[]}>('/user/rewards'),
};

// ── Wishlist ─────────────────────────────────────────────────
export const wishlistAPI = {
  list: () =>
    api.get<{success: boolean; wishlist: WishlistItem[]; total: number}>('/wishlist'),

  add: (item_type: string, ref_id: number) =>
    api.post<{success: boolean; id: number; message: string}>('/wishlist', {item_type, ref_id}),

  remove: (id: number) =>
    api.delete<{success: boolean; message: string}>(`/wishlist/${id}`),
};

// ── Reviews ──────────────────────────────────────────────────
export const reviewsAPI = {
  list: (params: {type: string; ref_id: number; page?: number}) =>
    api.get<{success: boolean; reviews: Review[]; total: number; average_rating: number; pages: number}>(
      '/reviews',
      {params},
    ),

  submit: (data: {review_type: string; ref_id: number; rating: number; title?: string; comment?: string}) =>
    api.post<{success: boolean; id: number; message: string}>('/reviews', data),
};

// ── Notifications ─────────────────────────────────────────────
export const notificationsAPI = {
  list: (params?: {unread_only?: boolean; page?: number}) =>
    api.get<{success: boolean; notifications: Notification[]; total: number; unread_count: number; pages: number}>(
      '/notifications',
      {params},
    ),

  markRead: (id: number) =>
    api.put<{success: boolean}>(`/notifications/${id}/read`),

  markAllRead: () =>
    api.put<{success: boolean}>('/notifications/read-all'),
};

// ── Promo Codes ───────────────────────────────────────────────
export const promoAPI = {
  validate: (code: string, amount: number) =>
    api.post<{success: boolean; promo: {code: string; discount_amount: number; final_amount: number; discount_type: string; discount_value: number; description: string}}>('/promo/validate', {code, amount}),
};

// ── Price Alerts ──────────────────────────────────────────────
export const priceAlertsAPI = {
  list: () =>
    api.get<{success: boolean; alerts: PriceAlert[]}>('/price-alerts'),

  create: (data: {alert_type: string; origin?: string; destination?: string; city?: string; target_price: number}) =>
    api.post<{success: boolean; id: number; message: string}>('/price-alerts', data),

  delete: (id: number) =>
    api.delete<{success: boolean; message: string}>(`/price-alerts/${id}`),
};

// ── Popular Destinations ──────────────────────────────────────
export const destinationsAPI = {
  popular: (limit?: number) =>
    api.get<{success: boolean; destinations: Destination[]; total: number}>(
      '/destinations/popular',
      {params: {limit}},
    ),
};
