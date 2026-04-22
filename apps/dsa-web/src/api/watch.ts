import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  WatchChartPeriod,
  WatchDayRange,
  WatchQuoteSnapshot,
  WatchRuntimeStatus,
  WatchScanActionResponse,
  WatchSignalEventDetail,
  WatchSignalEventListResponse,
  WatchTargetCreateRequest,
  WatchTargetDetail,
  WatchTargetItem,
  WatchTargetListResponse,
} from '../types/watch';

const normalizeWatchQuote = (
  detail: WatchTargetDetail,
  quoteSnapshot?: WatchQuoteSnapshot | null,
): WatchQuoteSnapshot | null => {
  const lastBar = detail.kline[detail.kline.length - 1];
  const previousBar = detail.kline[detail.kline.length - 2];
  if (!lastBar && !quoteSnapshot) return null;

  const prevClose = quoteSnapshot?.prevClose ?? previousBar?.close ?? lastBar?.open ?? null;
  const latestPrice = quoteSnapshot?.latestPrice ?? lastBar?.close ?? null;
  const changeAmount =
    quoteSnapshot?.changeAmount
    ?? quoteSnapshot?.change
    ?? (latestPrice != null && prevClose != null ? latestPrice - prevClose : null);
  const changePct =
    quoteSnapshot?.changePct
    ?? (changeAmount != null && prevClose ? (changeAmount / prevClose) * 100 : null);

  return {
    latestPrice,
    change: changeAmount,
    changeAmount,
    changePct,
    amplitude: quoteSnapshot?.amplitude ?? null,
    high: quoteSnapshot?.high ?? lastBar?.high ?? null,
    low: quoteSnapshot?.low ?? lastBar?.low ?? null,
    open: quoteSnapshot?.open ?? lastBar?.open ?? null,
    prevClose,
    volume: quoteSnapshot?.volume ?? lastBar?.volume ?? null,
    turnover: quoteSnapshot?.turnover ?? null,
  };
};

const normalizeWatchTargetDetail = (detail: WatchTargetDetail): WatchTargetDetail => {
  const quoteSnapshot = normalizeWatchQuote(detail, detail.quoteSnapshot ?? detail.quote ?? null);

  return {
    ...detail,
    chartType: detail.chartType ?? (detail.meta?.timeframe === 'intraday' ? 'line' : 'candlestick'),
    quote: quoteSnapshot,
    quoteSnapshot,
  };
};

export const watchApi = {
  getTargets: async (params: {
    page?: number;
    limit?: number;
    targetKind?: string;
    status?: string;
    query?: string;
  } = {}): Promise<WatchTargetListResponse> => {
    const { page = 1, limit = 20, targetKind, status, query } = params;
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/watch/targets', {
      params: {
        page,
        limit,
        target_kind: targetKind,
        status,
        query,
      },
    });
    return toCamelCase<WatchTargetListResponse>(response.data);
  },

  createTarget: async (payload: WatchTargetCreateRequest): Promise<WatchTargetItem> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/watch/targets', {
      input_text: payload.inputText,
      target_kind: payload.targetKind,
      display_name: payload.displayName,
    });
    return toCamelCase<WatchTargetItem>(response.data);
  },

  getTargetDetail: async (
    targetId: number,
    params: {
      memberCode?: string;
      period?: WatchChartPeriod;
      range?: WatchDayRange;
    } = {},
  ): Promise<WatchTargetDetail> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/watch/targets/${targetId}/detail`, {
      params: {
        member_code: params.memberCode,
        timeframe: params.period,
        window: params.range,
      },
    });
    return normalizeWatchTargetDetail(toCamelCase<WatchTargetDetail>(response.data));
  },

  getEvents: async (params: {
    page?: number;
    limit?: number;
    targetId?: number;
    status?: string;
  } = {}): Promise<WatchSignalEventListResponse> => {
    const { page = 1, limit = 20, targetId, status } = params;
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/watch/events', {
      params: {
        page,
        limit,
        target_id: targetId,
        status,
      },
    });
    return toCamelCase<WatchSignalEventListResponse>(response.data);
  },

  getEventDetail: async (eventId: number): Promise<WatchSignalEventDetail> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/watch/events/${eventId}`);
    return toCamelCase<WatchSignalEventDetail>(response.data);
  },

  getRuntimeStatus: async (): Promise<WatchRuntimeStatus> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/watch/runtime/status');
    return toCamelCase<WatchRuntimeStatus>(response.data);
  },

  startRuntime: async (): Promise<WatchRuntimeStatus> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/watch/runtime/start');
    return toCamelCase<WatchRuntimeStatus>(response.data);
  },

  stopRuntime: async (): Promise<WatchRuntimeStatus> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/watch/runtime/stop');
    return toCamelCase<WatchRuntimeStatus>(response.data);
  },

  scanAllTargetsOnce: async (): Promise<WatchScanActionResponse> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/watch/runtime/scan');
    return toCamelCase<WatchScanActionResponse>(response.data);
  },

  scanTargetOnce: async (targetId: number): Promise<WatchScanActionResponse> => {
    const response = await apiClient.post<Record<string, unknown>>(`/api/v1/watch/targets/${targetId}/scan`);
    return toCamelCase<WatchScanActionResponse>(response.data);
  },

  getStreamUrl: (): string => '/api/v1/watch/stream',
};
