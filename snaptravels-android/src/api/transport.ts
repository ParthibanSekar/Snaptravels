import api from './client';
import {Bus, Train, Cab} from '../types';

export const busesAPI = {
  search: (params: {origin: string; destination: string; date: string; bus_type?: string}) =>
    api.get<{success: boolean; buses: Bus[]; total: number; date: string}>('/buses/search', {params}),
};

export const trainsAPI = {
  search: (params: {origin: string; destination: string; date: string; class?: string}) =>
    api.get<{success: boolean; trains: Train[]; total: number; date: string}>('/trains/search', {params}),
};

export const cabsAPI = {
  search: (params: {pickup: string; drop: string; distance_km?: number; vehicle_type?: string}) =>
    api.get<{success: boolean; cabs: Cab[]; total: number; pickup: string; drop: string; distance_km: number}>(
      '/cabs/search',
      {params},
    ),
};
