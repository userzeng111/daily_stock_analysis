export interface WatchTargetSummary {
  status: string;
  summaryWindowDays: number;
  signalScore?: number | null;
  action?: string | null;
  brief?: string | null;
  trendStatus?: string | null;
  buySignal?: string | null;
  periodReturnPct?: number | null;
  updatedAt?: string | null;
  representativeMemberCode?: string | null;
  representativeMemberName?: string | null;
  memberCount?: number | null;
  error?: string | null;
}

export interface WatchMemberOption {
  id: number;
  memberCode: string;
  memberName: string;
  memberKind: string;
}

export interface WatchTargetItem {
  id: number;
  targetKind: string;
  targetKey: string;
  displayName: string;
  status: string;
  themeId?: string;
  themeName?: string;
  source?: string;
  notes?: string;
  createdAt?: string;
  updatedAt?: string;
  memberCount: number;
  summary?: WatchTargetSummary | null;
}

export interface WatchTargetListResponse {
  total: number;
  page: number;
  limit: number;
  items: WatchTargetItem[];
}

export interface WatchTargetCreateRequest {
  inputText: string;
  targetKind?: string;
  displayName?: string;
}

export interface WatchReviewSummary {
  id: number;
  signalEventId: number;
  reviewRound: number;
  decision: string;
  confidence?: number;
  summary?: string;
  payload?: Record<string, unknown> | string;
  createdAt?: string;
  updatedAt?: string;
}

export interface WatchSignalEventItem {
  id: number;
  targetId: number;
  memberId?: number;
  memberCode: string;
  memberName?: string;
  signalDate?: string;
  signalType: string;
  signalScore?: number;
  status: string;
  dedupeKey: string;
  payload?: Record<string, unknown> | string;
  createdAt?: string;
  updatedAt?: string;
  latestReviewSummary?: WatchReviewSummary | null;
}

export interface WatchSignalEventDetail extends WatchSignalEventItem {
  latestReview?: WatchReviewSummary | null;
}

export interface WatchSignalEventListResponse {
  total: number;
  page: number;
  limit: number;
  items: WatchSignalEventItem[];
}

export interface WatchRuntimeStatus {
  enabled: boolean;
  registered: boolean;
  lastScanAt?: string | null;
  lastError?: string | null;
  scanIntervalMinutes: number;
}

export interface WatchTargetDetail {
  target: WatchTargetItem;
  summary: WatchTargetSummary;
  memberOptions: WatchMemberOption[];
  activeMember: WatchMemberOption;
  kline: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  indicators: WatchTargetIndicators;
  strategyInsights: WatchTargetStrategyInsights;
  latestReview?: WatchReviewSummary | null;
}

export interface WatchTargetIndicators {
  trendStatus?: string | null;
  signalScore?: number | null;
  buySignal?: string | null;
  ma5?: number | null;
  ma10?: number | null;
  ma20?: number | null;
  macdStatus?: string | null;
  rsiStatus?: string | null;
  volumeStatus?: string | null;
  supportLevels?: number[];
  resistanceLevels?: number[];
}

export interface WatchTargetStrategyInsights {
  signalReasons?: string[];
  riskFactors?: string[];
  action?: string | null;
}

export interface WatchStreamEvent {
  eventType: string;
  occurredAt?: string;
  payload?: Record<string, unknown>;
}
