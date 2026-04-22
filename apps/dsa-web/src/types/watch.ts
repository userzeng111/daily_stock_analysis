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

export type WatchChartPeriod = 'intraday' | 'day' | 'week' | 'month';

export type WatchDayRange = '30' | '60' | '120' | '250' | 'ytd';

export type WatchIndicatorPanel = 'vol' | 'macd' | 'rsi';

export interface WatchQuoteSnapshot {
  latestPrice?: number | null;
  change?: number | null;
  changeAmount?: number | null;
  changePct?: number | null;
  amplitude?: number | null;
  high?: number | null;
  low?: number | null;
  open?: number | null;
  prevClose?: number | null;
  volume?: number | null;
  turnover?: number | null;
}

export interface WatchIntradayPoint {
  time: string;
  price: number;
  averagePrice?: number | null;
  volume?: number | null;
}

export interface WatchKlineBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface WatchOverlaySeries {
  ma5?: Array<number | null>;
  ma10?: Array<number | null>;
  ma20?: Array<number | null>;
}

export interface WatchMacdSubIndicator {
  dif: Array<number | null>;
  dea: Array<number | null>;
  bar: Array<number | null>;
}

export interface WatchRsiSubIndicator {
  rsi6: Array<number | null>;
  rsi12: Array<number | null>;
  rsi24: Array<number | null>;
}

export interface WatchSubIndicators {
  volMa?: Array<number | null>;
  macd?: WatchMacdSubIndicator;
  rsi?: WatchRsiSubIndicator;
}

export interface WatchDetailMeta {
  timeframe: WatchChartPeriod;
  window: WatchDayRange;
  barCount: number;
  updatedAt?: string | null;
}

export interface WatchTargetDetail {
  target: WatchTargetItem;
  summary: WatchTargetSummary;
  memberOptions: WatchMemberOption[];
  activeMember: WatchMemberOption;
  quote?: WatchQuoteSnapshot | null;
  quoteSnapshot?: WatchQuoteSnapshot | null;
  intraday?: WatchIntradayPoint[];
  kline: WatchKlineBar[];
  chartType?: string | null;
  indicators: WatchTargetIndicators;
  strategyInsights: WatchTargetStrategyInsights;
  overlays?: WatchOverlaySeries | null;
  subIndicators?: WatchSubIndicators | null;
  meta?: WatchDetailMeta | null;
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

export interface WatchScanActionResponse {
  targetId?: number;
  processedTargets?: number;
  emittedEvents?: number;
  lastScanAt?: string | null;
  status?: string | null;
  [key: string]: unknown;
}

export interface WatchStreamEventPayload {
  targetId?: number;
  eventId?: number;
  reviewId?: number;
  memberCode?: string;
  status?: string;
  enabled?: boolean;
  processedTargets?: number;
  emittedEvents?: number;
  lastScanAt?: string;
  [key: string]: unknown;
}

export interface WatchStreamEvent {
  eventType: string;
  occurredAt?: string;
  payload?: WatchStreamEventPayload;
}
