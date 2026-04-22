import { useCallback, useEffect, useRef, useState } from 'react';
import { watchApi } from '../api/watch';
import { toCamelCase } from '../api/utils';
import type { WatchStreamEvent } from '../types/watch';

type UseWatchStreamOptions = {
  enabled?: boolean;
  autoReconnect?: boolean;
  reconnectDelay?: number;
  onEvent?: (event: WatchStreamEvent) => void;
  onError?: (error: Event) => void;
};

type UseWatchStreamResult = {
  isConnected: boolean;
  reconnect: () => void;
  disconnect: () => void;
};

export function useWatchStream(options: UseWatchStreamOptions = {}): UseWatchStreamResult {
  const {
    enabled = true,
    autoReconnect = true,
    reconnectDelay = 3000,
    onEvent,
    onError,
  } = options;

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbacksRef = useRef({ onEvent, onError });
  const connectRef = useRef<() => void>(() => undefined);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    callbacksRef.current = { onEvent, onError };
  }, [onEvent, onError]);

  const dispatchEvent = useCallback((eventType: string, event: MessageEvent<string>) => {
    try {
      const data = toCamelCase<{ occurredAt?: string; payload?: WatchStreamEvent['payload'] }>(
        JSON.parse(event.data),
      );
      callbacksRef.current.onEvent?.({
        eventType,
        occurredAt: data.occurredAt,
        payload: data.payload,
      });
    } catch (error) {
      console.error('Failed to parse watch SSE event:', error);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    queueMicrotask(() => setIsConnected(false));
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;
    disconnect();
    const source = new EventSource(watchApi.getStreamUrl(), { withCredentials: true });
    eventSourceRef.current = source;

    source.addEventListener('watch.connected', () => {
      setIsConnected(true);
    });
    source.addEventListener('watch.runtime.started', (event) => dispatchEvent('watch.runtime.started', event as MessageEvent<string>));
    source.addEventListener('watch.runtime.stopped', (event) => dispatchEvent('watch.runtime.stopped', event as MessageEvent<string>));
    source.addEventListener('watch.scan.completed', (event) => dispatchEvent('watch.scan.completed', event as MessageEvent<string>));
    source.addEventListener('watch.signal.created', (event) => dispatchEvent('watch.signal.created', event as MessageEvent<string>));
    source.addEventListener('watch.review.updated', (event) => dispatchEvent('watch.review.updated', event as MessageEvent<string>));

    source.onerror = (error) => {
      setIsConnected(false);
      callbacksRef.current.onError?.(error);
      if (autoReconnect && enabled) {
        source.close();
        reconnectTimerRef.current = setTimeout(() => {
          connectRef.current();
        }, reconnectDelay);
      }
    };
  }, [autoReconnect, disconnect, dispatchEvent, enabled, reconnectDelay]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const reconnect = useCallback(() => {
    disconnect();
    connect();
  }, [connect, disconnect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, enabled]);

  return { isConnected, reconnect, disconnect };
}
