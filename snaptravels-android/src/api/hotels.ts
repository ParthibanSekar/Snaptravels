import api from './client';
import {Hotel} from '../types';

export const hotelsAPI = {
  search: (params: {city: string; checkin: string; checkout: string; guests?: number}) =>
    api.get<{success: boolean; hotels: Hotel[]; total: number}>('/hotels/search', {params}),
};
