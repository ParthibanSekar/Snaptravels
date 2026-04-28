import {useState, useCallback} from 'react';
import {AxiosPromise} from 'axios';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  execute: (...args: Parameters<(...a: unknown[]) => AxiosPromise<T>>) => Promise<T | null>;
  reset: () => void;
}

/**
 * Generic hook that wraps any API call returning an AxiosPromise.
 *
 * Usage:
 *   const {data, loading, error, execute} = useApi(flightsAPI.search);
 *   await execute({origin: 'DEL', destination: 'BOM', date: '2026-05-01'});
 */
export function useApi<T, Args extends unknown[]>(
  apiCall: (...args: Args) => AxiosPromise<T>,
): {data: T | null; loading: boolean; error: string | null; execute: (...args: Args) => Promise<T | null>; reset: () => void} {
  const [state, setState] = useState<UseApiState<T>>({data: null, loading: false, error: null});

  const execute = useCallback(
    async (...args: Args): Promise<T | null> => {
      setState(prev => ({...prev, loading: true, error: null}));
      try {
        const res = await apiCall(...args);
        setState({data: res.data, loading: false, error: null});
        return res.data;
      } catch (err: unknown) {
        const message =
          (err as {response?: {data?: {error?: string}}})?.response?.data?.error ||
          (err as Error)?.message ||
          'Request failed';
        setState({data: null, loading: false, error: message});
        return null;
      }
    },
    [apiCall],
  );

  const reset = useCallback(() => {
    setState({data: null, loading: false, error: null});
  }, []);

  return {...state, execute, reset};
}
