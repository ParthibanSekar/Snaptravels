import api from './client';
import {Flight} from '../types';

export const flightsAPI = {
  search: (params: {origin: string; destination: string; date: string; passengers?: number}) =>
    api.get<{success: boolean; flights: Flight[]; total: number}>('/flights/search', {params}),

  autocomplete: (q: string) =>
    api.get<{success: boolean; suggestions: string[]}>('/autocomplete', {params: {q}}),
};
