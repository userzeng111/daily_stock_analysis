import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { watchApi } from '../api/watch';
import { getParsedApiError } from '../api/error';
import type { ParsedApiError } from '../api/error';
import { WatchEventFeed, WatchMarketPanel, WatchTargetList } from '../components/watch';
import { ApiErrorAlert, Badge, Card } from '../components/common';
import { useWatchStream } from '../hooks/useWatchStream';
import type {
  WatchChartPeriod,
  WatchDayRange,
  WatchIndicatorPanel,
  WatchRuntimeStatus,
  WatchSignalEventItem,
  WatchTargetDetail,
  WatchTargetItem,
} from '../types/watch';

const WATCH_INPUT_CLASS =
  'input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none disabled:cursor-not-allowed disabled:opacity-60';

const statusBadge = (enabled: boolean) => (
  <Badge variant={enabled ? 'success' : 'default'}>{enabled ? '运行中' : '已停止'}</Badge>
);

const WATCH_EVENT_TYPES = new Set([
  'watch.scan.completed',
  'watch.signal.created',
  'watch.review.updated',
]);

const WatchPage: React.FC = () => {
  useEffect(() => {
    document.title = '连续跟踪 - DSA';
  }, []);

  const [runtime, setRuntime] = useState<WatchRuntimeStatus | null>(null);
  const [targets, setTargets] = useState<WatchTargetItem[]>([]);
  const [events, setEvents] = useState<WatchSignalEventItem[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [selectedMemberCode, setSelectedMemberCode] = useState<string | undefined>(undefined);
  const [selectedTargetDetail, setSelectedTargetDetail] = useState<WatchTargetDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isScanningAll, setIsScanningAll] = useState(false);
  const [isScanningTarget, setIsScanningTarget] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<WatchChartPeriod>('day');
  const [selectedRange, setSelectedRange] = useState<WatchDayRange>('30');
  const [selectedIndicator, setSelectedIndicator] = useState<WatchIndicatorPanel>('vol');
  const detailRequestIdRef = useRef(0);
  const selectedTargetIdRef = useRef<number | null>(null);
  const selectedMemberCodeRef = useRef<string | undefined>(undefined);
  const selectedPeriodRef = useRef<WatchChartPeriod>('day');
  const selectedRangeRef = useRef<WatchDayRange>('30');

  useEffect(() => {
    selectedTargetIdRef.current = selectedTargetId;
  }, [selectedTargetId]);

  useEffect(() => {
    selectedMemberCodeRef.current = selectedMemberCode;
  }, [selectedMemberCode]);

  useEffect(() => {
    selectedPeriodRef.current = selectedPeriod;
  }, [selectedPeriod]);

  useEffect(() => {
    selectedRangeRef.current = selectedRange;
  }, [selectedRange]);

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
    await Promise.all([loadTargets(), loadEvents(), loadRuntime()]);
  }, [loadEvents, loadRuntime, loadTargets]);

  const loadTargetDetail = useCallback(async (
    targetId: number,
    params: {
      memberCode?: string;
      period?: WatchChartPeriod;
      range?: WatchDayRange;
    } = {},
  ) => {
    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;

    try {
      setDetailLoading(true);
      const detail = await watchApi.getTargetDetail(targetId, {
        memberCode: params.memberCode,
        period: params.period ?? selectedPeriodRef.current,
        range: params.range ?? selectedRangeRef.current,
      });
      if (detailRequestIdRef.current !== requestId) return;
      setSelectedTargetDetail(detail);
      setError(null);
    } catch (err) {
      if (detailRequestIdRef.current !== requestId) return;
      setSelectedTargetDetail(null);
      setError(getParsedApiError(err));
    } finally {
      if (detailRequestIdRef.current === requestId) {
        setDetailLoading(false);
      }
    }
  }, []);

  const refreshActiveDetail = useCallback(async () => {
    if (selectedTargetIdRef.current == null) return;
    await loadTargetDetail(selectedTargetIdRef.current, {
      memberCode: selectedMemberCodeRef.current,
      period: selectedPeriodRef.current,
      range: selectedRangeRef.current,
    });
  }, [loadTargetDetail]);

  useEffect(() => {
    void (async () => {
      try {
        await loadPage();
        setError(null);
      } catch (err) {
        setError(getParsedApiError(err));
      }
    })();
  }, [loadPage]);

  useEffect(() => {
    if (selectedTargetId == null) return;
    void loadTargetDetail(selectedTargetId, {
      memberCode: selectedMemberCode,
      period: selectedPeriod,
      range: selectedRange,
    });
  }, [loadTargetDetail, selectedMemberCode, selectedPeriod, selectedRange, selectedTargetId]);

  useEffect(() => {
    if (selectedTargetId == null) {
      setSelectedTargetDetail(null);
      return;
    }

    if (targets.length > 0 && !targets.some((target) => target.id === selectedTargetId)) {
      setSelectedTargetId(null);
      setSelectedMemberCode(undefined);
      setSelectedTargetDetail(null);
    }
  }, [selectedTargetId, targets]);

  const { isConnected } = useWatchStream({
    enabled: true,
    onEvent: (event) => {
      if (event.eventType === 'watch.runtime.started' || event.eventType === 'watch.runtime.stopped') {
        void loadRuntime();
        return;
      }

      if (!WATCH_EVENT_TYPES.has(event.eventType)) return;

      void loadTargets();
      void loadEvents();
      void loadRuntime();

      const eventTargetId = typeof event.payload?.targetId === 'number' ? event.payload.targetId : null;
      const shouldRefreshActiveDetail =
        event.eventType === 'watch.scan.completed' ||
        (selectedTargetIdRef.current != null && eventTargetId === selectedTargetIdRef.current);

      if (shouldRefreshActiveDetail) {
        void refreshActiveDetail();
      }
    },
  });

  const handleRefreshData = useCallback(async () => {
    try {
      setIsRefreshing(true);
      await loadPage();
      await refreshActiveDetail();
      setError(null);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setIsRefreshing(false);
    }
  }, [loadPage, refreshActiveDetail]);

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

  const handleScanAll = useCallback(async () => {
    try {
      setIsScanningAll(true);
      await watchApi.scanAllTargetsOnce();
      await loadPage();
      await refreshActiveDetail();
      setError(null);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setIsScanningAll(false);
    }
  }, [loadPage, refreshActiveDetail]);

  const handleScanTarget = useCallback(async (targetId: number) => {
    try {
      setIsScanningTarget(true);
      await watchApi.scanTargetOnce(targetId);
      await Promise.all([loadTargets(), loadEvents(), loadRuntime()]);
      if (selectedTargetIdRef.current === targetId) {
        await refreshActiveDetail();
      }
      setError(null);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setIsScanningTarget(false);
    }
  }, [loadEvents, loadRuntime, loadTargets, refreshActiveDetail]);

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

  const handleOpenTarget = useCallback((targetId: number) => {
    setSelectedMemberCode(undefined);
    setSelectedPeriod('day');
    setSelectedRange('30');
    setSelectedIndicator('vol');
    setSelectedTargetId(targetId);
  }, []);

  const targetSummary = useMemo(() => {
    const activeCount = targets.filter((item) => item.status === 'active').length;
    return `${activeCount}/${targets.length}`;
  }, [targets]);

  return (
    <div data-testid="watch-page" className="watch-page space-y-4 px-3 pb-6 md:px-6">
      {error ? <ApiErrorAlert error={error} /> : null}

      <Card variant="gradient" padding="md">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <p className="label-uppercase">连续跟踪</p>
            <h1 className="text-2xl font-semibold text-foreground">个股 / ETF / 主题持续监测</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-secondary-text">
              <span>当前状态：{runtime ? statusBadge(runtime.enabled) : <Badge>加载中</Badge>}</span>
              <span>
                跟踪目标 <span className="font-semibold text-foreground">{targetSummary}</span>
              </span>
              <span>
                扫描频率{' '}
                <span className="font-semibold text-foreground">
                  {runtime?.scanIntervalMinutes ?? 45} 分钟
                </span>
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={isRefreshing}
              onClick={() => void handleRefreshData()}
            >
              刷新数据
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={isScanningAll}
              onClick={() => void handleScanAll()}
            >
              全量扫描一次
            </button>
            <button type="button" className="btn-primary" onClick={() => void handleToggleRuntime()}>
              {runtime?.enabled ? '停止监测' : '启动监测'}
            </button>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 2xl:grid-cols-[320px_minmax(0,1fr)_360px]">
        <Card padding="md">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-foreground">目标池</h2>
            <p className="text-sm text-secondary-text">支持股票代码、ETF 代码和内置主题名。</p>
          </div>

          <div className="mb-4 flex gap-3">
            <input
              value={inputText}
              onChange={(event) => setInputText(event.target.value)}
              placeholder="输入股票代码、ETF 代码或主题名"
              className={WATCH_INPUT_CLASS}
            />
            <button
              type="button"
              className="btn-primary whitespace-nowrap"
              disabled={isSubmitting}
              onClick={() => void handleCreateTarget()}
            >
              添加跟踪目标
            </button>
          </div>

          <WatchTargetList
            targets={targets}
            selectedTargetId={selectedTargetId}
            onSelectTarget={handleOpenTarget}
            onScanTarget={(targetId) => void handleScanTarget(targetId)}
            isScanningTarget={isScanningTarget}
          />
        </Card>

        <Card padding="md">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-foreground">行情工作台</h2>
            <p className="text-sm text-secondary-text">
              分时 / K 线 / 副图联动查看，接近个股页的基础观察结构。
            </p>
          </div>

          <WatchMarketPanel
            detail={selectedTargetDetail}
            detailLoading={detailLoading}
            selectedPeriod={selectedPeriod}
            selectedRange={selectedRange}
            selectedIndicator={selectedIndicator}
            onPeriodChange={setSelectedPeriod}
            onRangeChange={setSelectedRange}
            onIndicatorChange={setSelectedIndicator}
            onMemberChange={setSelectedMemberCode}
            onScanTarget={(targetId) => void handleScanTarget(targetId)}
            isScanningTarget={isScanningTarget}
          />
        </Card>

        <div className="space-y-4">
          <Card padding="md">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-foreground">候选事件</h2>
              <p className="text-sm text-secondary-text">规则筛选后，再交给复核服务判断是否可跟踪。</p>
            </div>
            <WatchEventFeed events={events} />
          </Card>

          <Card padding="md">
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-secondary-text">连接状态</span>
                <Badge variant={isConnected ? 'success' : 'warning'}>
                  {isConnected ? 'SSE 已连接' : 'SSE 重连中'}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-secondary-text">运行状态</span>
                {statusBadge(runtime?.enabled ?? false)}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-secondary-text">最后扫描</span>
                <span className="text-foreground">{runtime?.lastScanAt || '--'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-secondary-text">最近错误</span>
                <span className="max-w-[220px] truncate text-right text-foreground">
                  {runtime?.lastError || '无'}
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default WatchPage;
