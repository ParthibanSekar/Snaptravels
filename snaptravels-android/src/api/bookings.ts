import api from './client';
import {Booking, InsurancePlan} from '../types';

export const bookingsAPI = {
  list: () =>
    api.get<{success: boolean; bookings: Booking[]; total: number}>('/bookings'),

  get: (id: number) =>
    api.get<{success: boolean; booking: Booking}>(`/bookings/${id}`),

  create: (data: {
    type: string;
    flight_id?: number;
    hotel_id?: number;
    customer_name?: string;
    customer_email?: string;
    customer_phone?: string;
    nights?: number;
    checkin?: string;
    checkout?: string;
    amount?: number;
  }) => api.post<{success: boolean; booking: Booking}>('/bookings', data),

  cancel: (id: number) =>
    api.put<{success: boolean; message: string; booking_code: string}>(`/bookings/${id}/cancel`),

  resendConfirmation: (id: number) =>
    api.post<{success: boolean; message: string}>(`/bookings/${id}/resend`),
};

export const insuranceAPI = {
  list: () =>
    api.get<{success: boolean; plans: InsurancePlan[]}>('/insurance/plans'),
};
