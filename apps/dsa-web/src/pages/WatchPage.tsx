import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiErrorAlert, Badge, Card, EmptyState } from '../components/common';
import { watchApi } from '../api/watch';
import { getParsedApiError } from '../api/error';
import type { ParsedApiError } from '../api/error';
import { useWatchStream } from '../hooks/useWatchStream';
import type {
  WatchRuntimeStatus,
  WatchSignalEventItem,
  WatchTargetDetail,
  WatchTargetItem,
} from '../types/watch';

const WATCH_INPUT_CLASS =
  'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';

const DETAIL_TABS: Array<7 | 30> = [7, 30];

const statusBadge = (enabled: boolean) => (
  <Badge variant={enabled ? 'success' : 'default'}>
    {enabled ? '运行中' : '已停止'}
  </Badge>
);

const eventDecisionLabel = (event: WatchSignalEventItem) =>
  event.latestReviewSummary?.summary || event.latestReviewSummary?.decision || event.status;

const summaryBadgeVariant = (status?: string | null) => {
  if (status === 'ready') return 'success';
  if (status === 'failed') return 'danger';
  return 'default';
};

const chartNumber = (value: unknown): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const formatLevels = (levels?: number[]) =>
  Array.isArray(levels) && levels.length > 0 ? levels.join(' / ') : '--';

const KlineChart: React.FC<{ data: WatchTargetDetail['kline'] }> = ({ data }) => {
  if (!data.length) {
    return (
      <EmptyState title="暂无K线数据" description="当前窗口没有可展示的交易数据。" />
    );
  }

  const width = 760;
  const height = 280;
  const padding = 24;
  const highs = data.map((item) => chartNumber(item.high));
  const lows = data.map((item) => chartNumber(item.low));
  const maxPrice = Math.max(...highs);
  const minPrice = Math.min(...lows);
  const range = Math.max(maxPrice - minPrice, 0.1);
  const slotWidth = (width - padding * 2) / data.length;
  const candleWidth = Math.max(6, slotWidth * 0.45);

  const priceToY = (price: number) =>
    padding + ((maxPrice - price) / range) * (height - padding * 2);

  return (
    <div className="rounded-2xl border border-border/60 bg-surface/30 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold text-foreground">K线图</h3>
        <span className="text-xs text-secondary-text">{data.length} 根</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[260px] w-full overflow-visible">
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={height - padding}
          stroke="rgba(148,163,184,0.35)"
          strokeWidth="1"
        />
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="rgba(148,163,184,0.35)"
          strokeWidth="1"
        />
        {data.map((item, index) => {
          const x = padding + slotWidth * index + slotWidth / 2;
          const open = chartNumber(item.open);
          const close = chartNumber(item.close);
          const high = chartNumber(item.high);
          const low = chartNumber(item.low);
          const bullish = close >= open;
          const bodyTop = priceToY(Math.max(open, close));
          const bodyBottom = priceToY(Math.min(open, close));
          const bodyHeight = Math.max(bodyBottom - bodyTop, 2);

          return (
            <g key={`${item.date}-${index}`}>
              <line
                x1={x}
                y1={priceToY(high)}
                x2={x}
                y2={priceToY(low)}
                stroke={bullish ? '#16a34a' : '#dc2626'}
                strokeWidth="1.5"
              />
              <rect
                x={x - candleWidth / 2}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                fill={bullish ? 'rgba(22,163,74,0.45)' : 'rgba(220,38,38,0.45)'}
                stroke={bullish ? '#16a34a' : '#dc2626'}
                strokeWidth="1.2"
                rx="1"
              />
            </g>
          );
        })}
      </svg>
      <div className="mt-3 flex items-center justify-between text-xs text-secondary-text">
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
};

const WatchPage: React.FC = () => {
  useEffect(() => {
    document.title = '连续跟踪 - DSA';
  }, []);

  const [runtime, setRuntime] = useState<WatchRuntimeStatus | null>(null);
  const [targets, setTargets] = useState<WatchTargetItem[]>([]);
  const [events, setEvents] = useState<WatchSignalEventItem[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [detailWindow, setDetailWindow] = useState<7 | 30>(7);
  const [selectedMemberCode, setSelectedMemberCode] = useState<string | undefined>(undefined);
  const [selectedTargetDetail, setSelectedTargetDetail] = useState<WatchTargetDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const detailRequestIdRef = useRef(0);

  const loadTargets = useCallback(async () => {
    const response = await watchApi.getTargets({ page: 1, limit: 20 });
    setTargets(response.items ?? []);
  }, []);

  const loadEvents = useCallback(async () => {
    const response = await watchApi.getEvents({ page: 1, limit: 20 });
    setEvents(response.items ?? []);
  }, []);

  const loadRuntime = useCallback(async () => {
    const response = await watchApi.getRuntimeStatus();
    setRuntime(response);
  }, []);

  const loadPage = useCallback(async () => {
    try {
      await Promise.all([loadTargets(), loadEvents(), loadRuntime()]);
      setError(null);
    } catch (err) {
      setError(getParsedApiError(err));
    }
  }, [loadEvents, loadRuntime, loadTargets]);

  const loadTargetDetail = useCallback(async (
    targetId: number,
    windowDays: 7 | 30,
    memberCode?: string,
  ) => {
    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;
    try {
      setDetailLoading(true);
      setSelectedTargetDetail(null);
      const detail = await watchApi.getTargetDetail(targetId, {
        window: windowDays,
        memberCode,
      });
      if (detailRequestIdRef.current !== requestId) {
        return;
      }
      setSelectedTargetDetail(detail);
      setError(null);
    } catch (err) {
      if (detailRequestIdRef.current !== requestId) {
        return;
      }
      setSelectedTargetDetail(null);
      setError(getParsedApiError(err));
    } finally {
      if (detailRequestIdRef.current === requestId) {
        setDetailLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  useEffect(() => {
    if (selectedTargetId == null) return;
    void loadTargetDetail(selectedTargetId, detailWindow, selectedMemberCode);
  }, [detailWindow, loadTargetDetail, selectedMemberCode, selectedTargetId]);

  useWatchStream({
    enabled: true,
    onEvent: (event) => {
      if (event.eventType === 'watch.runtime.started' || event.eventType === 'watch.runtime.stopped') {
        void loadRuntime();
        return;
      }
      if (event.eventType === 'watch.scan.completed' || event.eventType === 'watch.signal.created' || event.eventType === 'watch.review.updated') {
        void loadTargets();
        void loadEvents();
        void loadRuntime();
      }
    },
  });

  const handleToggleRuntime = useCallback(async () => {
    try {
      const nextRuntime = runtime?.enabled
        ? await watchApi.stopRuntime()
        : await watchApi.startRuntime();
      setRuntime(nextRuntime);
      setError(null);
    } catch (err) {
      setError(getParsedApiError(err));
    }
  }, [runtime?.enabled]);

  const handleCreateTarget = useCallback(async () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;
    try {
      setIsSubmitting(true);
      await watchApi.createTarget({
        inputText: trimmed,
        displayName: undefined,
        targetKind: undefined,
      });
      setInputText('');
      await loadTargets();
      setError(null);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  }, [inputText, loadTargets]);

  const handleOpenTargetDetail = useCallback(async (targetId: number) => {
    setSelectedTargetId(targetId);
    setDetailWindow(7);
    setSelectedMemberCode(undefined);
  }, []);

  const targetSummary = useMemo(() => {
    const activeCount = targets.filter((item) => item.status === 'active').length;
    return `${activeCount}/${targets.length}`;
  }, [targets]);

  return (
    <div data-testid="watch-page" className="space-y-4 px-3 pb-6 md:px-6">
      {error ? <ApiErrorAlert error={error} /> : null}

      <Card variant="gradient" padding="md">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="label-uppercase">连续跟踪</p>
            <h1 className="text-2xl font-semibold text-foreground">个股 / ETF / 主题持续监测</h1>
            <p className="mt-2 text-sm text-secondary-text">
              当前状态：{runtime ? statusBadge(runtime.enabled) : <Badge variant="default">加载中</Badge>}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-2xl border border-border/70 px-4 py-3 text-sm text-secondary-text">
              跟踪目标 <span className="font-semibold text-foreground">{targetSummary}</span>
            </div>
            <div className="rounded-2xl border border-border/70 px-4 py-3 text-sm text-secondary-text">
              扫描频率 <span className="font-semibold text-foreground">{runtime?.scanIntervalMinutes ?? 45} 分钟</span>
            </div>
            <button type="button" className="btn-primary" onClick={() => void handleToggleRuntime()}>
              {runtime?.enabled ? '停止监测' : '启动监测'}
            </button>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card padding="md">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-foreground">跟踪目标</h2>
              <p className="text-sm text-secondary-text">支持股票代码、ETF 代码和内置主题名。</p>
            </div>
          </div>
          <div className="mb-4 flex gap-3">
            <input
              value={inputText}
              onChange={(event) => setInputText(event.target.value)}
              placeholder="输入股票代码、ETF 代码或主题名"
              className={WATCH_INPUT_CLASS}
            />
            <button type="button" className="btn-primary whitespace-nowrap" disabled={isSubmitting} onClick={() => void handleCreateTarget()}>
              添加跟踪目标
            </button>
          </div>
          {targets.length === 0 ? (
            <EmptyState title="暂无跟踪目标" description="添加一个股票、ETF 或主题后，这里会显示监测篮子。" />
          ) : (
            <div className="space-y-3">
              {targets.map((target) => (
                <div key={target.id} className="rounded-2xl border border-border/60 bg-surface/40 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-base font-semibold text-foreground">{target.displayName}</span>
                        <Badge variant={target.status === 'active' ? 'success' : 'warning'}>{target.status}</Badge>
                        {target.summary?.status ? (
                          <Badge variant={summaryBadgeVariant(target.summary.status)}>{target.summary.status}</Badge>
                        ) : null}
                      </div>
                      <p className="text-sm text-secondary-text">
                        {target.targetKey} · {target.targetKind} · 成员 {target.memberCount}
                      </p>
                      <div className="flex flex-wrap gap-2 text-xs text-secondary-text">
                        {target.summary?.trendStatus ? (
                          <Badge variant="default">{target.summary.trendStatus}</Badge>
                        ) : null}
                        {target.summary?.signalScore != null ? (
                          <Badge variant="info">评分 {target.summary.signalScore}</Badge>
                        ) : null}
                        {target.summary?.action ? (
                          <Badge variant="warning">{target.summary.action}</Badge>
                        ) : null}
                      </div>
                      <p className="text-sm text-foreground">
                        {target.summary?.brief || '摘要生成中'}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn-secondary whitespace-nowrap"
                      onClick={() => void handleOpenTargetDetail(target.id)}
                    >
                      展开详情
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card padding="md">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-foreground">候选事件</h2>
            <p className="text-sm text-secondary-text">规则筛选后再交给复核服务判断是否可跟踪。</p>
          </div>
          {events.length === 0 ? (
            <EmptyState title="暂无候选事件" description="监测启动后，阶段性买点会出现在这里。" />
          ) : (
            <div className="space-y-3">
              {events.map((event) => (
                <div key={event.id} className="rounded-2xl border border-border/60 bg-surface/40 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-base font-semibold text-foreground">{event.memberName || event.memberCode}</span>
                        <Badge variant={event.status === 'accepted' ? 'success' : 'default'}>{event.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-secondary-text">
                        {event.memberCode} · 评分 {event.signalScore ?? '--'} · {event.signalDate}
                      </p>
                      <p className="mt-2 text-sm text-foreground">{eventDecisionLabel(event)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card padding="md">
        <div className="mb-3">
          <h2 className="text-lg font-semibold text-foreground">跟踪详情</h2>
          <p className="text-sm text-secondary-text">点击左侧跟踪目标后，查看近 7 日摘要、K 线和策略详情。</p>
        </div>
        {detailLoading ? (
          <EmptyState title="详情加载中" description="正在读取 K 线和策略信息。" />
        ) : !selectedTargetDetail ? (
          <EmptyState title="未选择跟踪目标" description="选择左侧跟踪目标后，这里会展示 K 线与策略面板。" />
        ) : (
          <div className="space-y-4">
            <div className="rounded-2xl border border-border/60 bg-surface/40 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-semibold text-foreground">
                      {selectedTargetDetail.target.displayName}
                    </span>
                    <Badge variant={summaryBadgeVariant(selectedTargetDetail.summary.status)}>
                      {selectedTargetDetail.summary.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-secondary-text">
                    {selectedTargetDetail.summary.brief || '暂无摘要'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {DETAIL_TABS.map((windowValue) => (
                    <button
                      key={windowValue}
                      type="button"
                      className={windowValue === detailWindow ? 'btn-primary' : 'btn-secondary'}
                      onClick={() => setDetailWindow(windowValue)}
                    >
                      {windowValue}日
                    </button>
                  ))}
                </div>
              </div>
              {selectedTargetDetail.memberOptions.length > 1 ? (
                <div className="mt-4 max-w-xs">
                  <label className="mb-2 block text-sm font-medium text-foreground" htmlFor="watch-member-select">
                    详情成员切换
                  </label>
                  <select
                    id="watch-member-select"
                    aria-label="详情成员切换"
                    className={WATCH_INPUT_CLASS}
                    value={selectedTargetDetail.activeMember.memberCode}
                    onChange={(event) => {
                      setSelectedMemberCode(event.target.value);
                    }}
                  >
                    {selectedTargetDetail.memberOptions.map((member) => (
                      <option key={member.memberCode} value={member.memberCode}>
                        {member.memberName} ({member.memberCode})
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
              <KlineChart data={selectedTargetDetail.kline} />

              <div className="space-y-4">
                <div className="rounded-2xl border border-border/60 bg-surface/30 p-4">
                  <h3 className="mb-3 text-base font-semibold text-foreground">策略指标</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-xl border border-border/50 p-3">
                      <div className="text-secondary-text">信号</div>
                      <div className="mt-1 font-semibold text-foreground">
                        {String(selectedTargetDetail.indicators.buySignal ?? '--')}
                      </div>
                    </div>
                    <div className="rounded-xl border border-border/50 p-3">
                      <div className="text-secondary-text">评分</div>
                      <div className="mt-1 font-semibold text-foreground">
                        {String(selectedTargetDetail.indicators.signalScore ?? '--')}
                      </div>
                    </div>
                    <div className="rounded-xl border border-border/50 p-3">
                      <div className="text-secondary-text">MA5 / MA10 / MA20</div>
                      <div className="mt-1 font-semibold text-foreground">
                        {String(selectedTargetDetail.indicators.ma5 ?? '--')} / {String(selectedTargetDetail.indicators.ma10 ?? '--')} / {String(selectedTargetDetail.indicators.ma20 ?? '--')}
                      </div>
                    </div>
                    <div className="rounded-xl border border-border/50 p-3">
                      <div className="text-secondary-text">MACD / RSI / 量价</div>
                      <div className="mt-1 font-semibold text-foreground">
                        {String(selectedTargetDetail.indicators.macdStatus ?? '--')} / {String(selectedTargetDetail.indicators.rsiStatus ?? '--')} / {String(selectedTargetDetail.indicators.volumeStatus ?? '--')}
                      </div>
                    </div>
                    <div className="rounded-xl border border-border/50 p-3">
                      <div className="text-secondary-text">支撑位</div>
                      <div className="mt-1 font-semibold text-foreground">
                        {formatLevels(selectedTargetDetail.indicators.supportLevels)}
                      </div>
                    </div>
                    <div className="rounded-xl border border-border/50 p-3">
                      <div className="text-secondary-text">压力位</div>
                      <div className="mt-1 font-semibold text-foreground">
                        {formatLevels(selectedTargetDetail.indicators.resistanceLevels)}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/60 bg-surface/30 p-4">
                  <h3 className="mb-3 text-base font-semibold text-foreground">策略解释</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <div className="mb-1 text-secondary-text">信号原因</div>
                      <div className="text-foreground">
                        {Array.isArray(selectedTargetDetail.strategyInsights.signalReasons)
                          ? selectedTargetDetail.strategyInsights.signalReasons.join(' / ')
                          : '--'}
                      </div>
                    </div>
                    <div>
                      <div className="mb-1 text-secondary-text">风险因素</div>
                      <div className="text-foreground">
                        {Array.isArray(selectedTargetDetail.strategyInsights.riskFactors)
                          ? selectedTargetDetail.strategyInsights.riskFactors.join(' / ')
                          : '--'}
                      </div>
                    </div>
                    <div>
                      <div className="mb-1 text-secondary-text">复核结论</div>
                      <div className="text-foreground">
                        {selectedTargetDetail.latestReview?.summary || '暂无复核结论'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default WatchPage;
