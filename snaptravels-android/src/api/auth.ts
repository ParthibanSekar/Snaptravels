import api from './client';
import {User} from '../types';

export interface LoginResponse {
  success: boolean;
  token: string;
  user: User;
}

export const authAPI = {
  login: (email: string, password: string) =>
    api.post<LoginResponse>('/auth/login', {email, password}),

  register: (email: string, password: string) =>
    api.post<LoginResponse>('/auth/register', {email, password}),

  refresh: () =>
    api.post<LoginResponse>('/auth/refresh'),

  logout: () =>
    api.post('/auth/logout'),

  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password', {current_password, new_password}),
};
