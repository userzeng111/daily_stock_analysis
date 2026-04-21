import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  WatchRuntimeStatus,
  WatchSignalEventDetail,
  WatchSignalEventListResponse,
  WatchTargetCreateRequest,
  WatchTargetDetail,
  WatchTargetItem,
  WatchTargetListResponse,
} from '../types/watch';

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
      window: 7 | 30;
      memberCode?: string;
    },
  ): Promise<WatchTargetDetail> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/watch/targets/${targetId}/detail`, {
      params: {
        window: params.window,
        member_code: params.memberCode,
      },
    });
    return toCamelCase<WatchTargetDetail>(response.data);
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

  getStreamUrl: (): string => '/api/v1/watch/stream',
};
