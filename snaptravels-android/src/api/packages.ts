import api from './client';
import {Package, Activity} from '../types';

export const packagesAPI = {
  list: (params?: {destination?: string; tag?: string; min_price?: number; max_price?: number; page?: number}) =>
    api.get<{success: boolean; packages: Package[]; total: number; page: number; pages: number}>(
      '/packages',
      {params},
    ),

  get: (slug: string) =>
    api.get<{success: boolean; package: Package}>(`/packages/${slug}`),
};

export const activitiesAPI = {
  list: (params?: {city?: string; category?: string; page?: number}) =>
    api.get<{success: boolean; activities: Activity[]; total: number; page: number; pages: number}>(
      '/activities',
      {params},
    ),

  get: (id: number) =>
    api.get<{success: boolean; activity: Activity}>(`/activities/${id}`),
};
