import React, {createContext, useContext, useEffect, useReducer, ReactNode} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {authAPI} from '../api/auth';
import {AuthState, User} from '../types';

// ── Actions ───────────────────────────────────────────────────
type AuthAction =
  | {type: 'LOGIN'; payload: {token: string; user: User}}
  | {type: 'LOGOUT'}
  | {type: 'LOADING'; payload: boolean}
  | {type: 'RESTORE'; payload: {token: string; user: User} | null};

const initialState: AuthState = {
  user: null,
  token: null,
  isLoading: true,
  isAuthenticated: false,
};

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN':
      return {...state, user: action.payload.user, token: action.payload.token, isAuthenticated: true, isLoading: false};
    case 'LOGOUT':
      return {...state, user: null, token: null, isAuthenticated: false, isLoading: false};
    case 'LOADING':
      return {...state, isLoading: action.payload};
    case 'RESTORE':
      if (action.payload) {
        return {...state, user: action.payload.user, token: action.payload.token, isAuthenticated: true, isLoading: false};
      }
      return {...state, isLoading: false};
    default:
      return state;
  }
}

// ── Context ───────────────────────────────────────────────────
interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ── Provider ──────────────────────────────────────────────────
export function AuthProvider({children}: {children: ReactNode}) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Restore session on launch
  useEffect(() => {
    (async () => {
      try {
        const [token, userJson] = await AsyncStorage.multiGet(['auth_token', 'auth_user']);
        const tokenVal = token[1];
        const userVal = userJson[1];
        if (tokenVal && userVal) {
          dispatch({type: 'RESTORE', payload: {token: tokenVal, user: JSON.parse(userVal)}});
        } else {
          dispatch({type: 'RESTORE', payload: null});
        }
      } catch {
        dispatch({type: 'RESTORE', payload: null});
      }
    })();
  }, []);

  const login = async (email: string, password: string) => {
    dispatch({type: 'LOADING', payload: true});
    const res = await authAPI.login(email, password);
    const {token, user} = res.data;
    await AsyncStorage.multiSet([
      ['auth_token', token],
      ['auth_user', JSON.stringify(user)],
    ]);
    dispatch({type: 'LOGIN', payload: {token, user}});
  };

  const register = async (email: string, password: string) => {
    dispatch({type: 'LOADING', payload: true});
    const res = await authAPI.register(email, password);
    const {token, user} = res.data;
    await AsyncStorage.multiSet([
      ['auth_token', token],
      ['auth_user', JSON.stringify(user)],
    ]);
    dispatch({type: 'LOGIN', payload: {token, user}});
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch {}
    await AsyncStorage.multiRemove(['auth_token', 'auth_user']);
    dispatch({type: 'LOGOUT'});
  };

  return (
    <AuthContext.Provider value={{...state, login, register, logout}}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}
