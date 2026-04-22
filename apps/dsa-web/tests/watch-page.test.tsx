import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { buildCandleData } from '../src/components/watch/chartData';
import WatchPage from '../src/pages/WatchPage';
import { SidebarNav } from '../src/components/layout/SidebarNav';
import type { WatchTargetDetail } from '../src/types/watch';

const {
  mockGetTargets,
  mockGetEvents,
  mockGetRuntimeStatus,
  mockStartRuntime,
  mockStopRuntime,
  mockCreateTarget,
  mockGetTargetDetail,
  mockScanAllTargetsOnce,
  mockScanTargetOnce,
  mockUseWatchStream,
} = vi.hoisted(() => ({
  mockGetTargets: vi.fn(),
  mockGetEvents: vi.fn(),
  mockGetRuntimeStatus: vi.fn(),
  mockStartRuntime: vi.fn(),
  mockStopRuntime: vi.fn(),
  mockCreateTarget: vi.fn(),
  mockGetTargetDetail: vi.fn(),
  mockScanAllTargetsOnce: vi.fn(),
  mockScanTargetOnce: vi.fn(),
  mockUseWatchStream: vi.fn(),
}));

vi.mock('../src/api/watch', () => ({
  watchApi: {
    getTargets: mockGetTargets,
    getEvents: mockGetEvents,
    getRuntimeStatus: mockGetRuntimeStatus,
    startRuntime: mockStartRuntime,
    stopRuntime: mockStopRuntime,
    createTarget: mockCreateTarget,
    getTargetDetail: mockGetTargetDetail,
    scanAllTargetsOnce: mockScanAllTargetsOnce,
    scanTargetOnce: mockScanTargetOnce,
    getStreamUrl: vi.fn(() => '/api/v1/watch/stream'),
  },
}));

vi.mock('../src/hooks/useWatchStream', () => ({
  useWatchStream: (options: unknown) => {
    mockUseWatchStream(options);
    return {
      isConnected: true,
      reconnect: vi.fn(),
      disconnect: vi.fn(),
    };
  },
}));

const mockLogout = vi.fn().mockResolvedValue(undefined);
const mockThemeToggle = vi.fn(({ collapsed }: { collapsed?: boolean }) => (
  <button type="button">{collapsed ? '切换主题(折叠)' : '切换主题'}</button>
));

vi.mock('../src/contexts/AuthContext', () => ({
  useAuth: () => ({
    authEnabled: false,
    logout: mockLogout,
  }),
}));

vi.mock('../src/stores/agentChatStore', () => ({
  useAgentChatStore: (selector: (state: { completionBadge: boolean }) => unknown) =>
    selector({ completionBadge: false }),
}));

vi.mock('../src/components/theme/ThemeToggle', () => ({
  ThemeToggle: (props: { collapsed?: boolean }) => mockThemeToggle(props),
}));

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function createBars(length: number, base = 10) {
  return Array.from({ length }).map((_, index) => {
    const open = base + index * 0.8;
    const close = open + (index % 2 === 0 ? 0.6 : -0.35);
    const high = Math.max(open, close) + 0.9;
    const low = Math.min(open, close) - 0.75;

    return {
      date: `2026-${String(Math.floor(index / 20) + 1).padStart(2, '0')}-${String((index % 20) + 1).padStart(2, '0')}`,
      open,
      high,
      low,
      close,
      volume: 1000000 + index * 12000,
    };
  });
}

function createDefaultDetail(overrides: Partial<WatchTargetDetail> = {}): WatchTargetDetail {
  const kline = createBars(260, 120);

  return {
    target: {
      id: 1,
      targetKind: 'stock',
      targetKey: '600519',
      displayName: '贵州茅台',
      status: 'active',
      memberCount: 1,
    },
    summary: {
      status: 'ready',
      summaryWindowDays: 7,
      signalScore: 82,
      action: '买入',
      brief: '近7日趋势偏强，可继续跟踪',
      trendStatus: '多头排列',
    },
    memberOptions: [
      {
        id: 11,
        memberCode: '600519',
        memberName: '贵州茅台',
        memberKind: 'stock',
      },
      {
        id: 12,
        memberCode: '603019',
        memberName: '中科曙光',
        memberKind: 'stock',
      },
    ],
    activeMember: {
      id: 11,
      memberCode: '600519',
      memberName: '贵州茅台',
      memberKind: 'stock',
    },
    quoteSnapshot: {
      latestPrice: 1888.88,
      change: 16.2,
      changeAmount: 16.2,
      changePct: 0.86,
      amplitude: 1.68,
      high: 1899.6,
      low: 1868.2,
      open: 1872.66,
      prevClose: 1872.68,
      volume: 5234000,
      turnover: 9830000000,
    },
    intraday: Array.from({ length: 16 }).map((_, index) => ({
      time: `${9 + Math.floor(index / 8)}:${index % 2 === 0 ? '30' : '45'}`,
      price: 1870 + index * 1.15,
      averagePrice: 1868 + index * 0.9,
      volume: 120000 + index * 1200,
    })),
    kline,
    chartType: 'candlestick',
    indicators: {
      buySignal: '买入',
      signalScore: 82,
      ma5: 1880.2,
      ma10: 1869.9,
      ma20: 1859.5,
      macdStatus: '金叉',
      rsiStatus: '强势买入',
      volumeStatus: '放量突破',
      supportLevels: [1858.8, 1836.4],
      resistanceLevels: [1906.2, 1928.6],
    },
    strategyInsights: {
      signalReasons: ['主升趋势维持', '量能同步放大'],
      riskFactors: ['短线偏离较大'],
      action: '买入',
    },
    overlays: {
      ma5: kline.map((item) => item.close - 1.2),
      ma10: kline.map((item) => item.close - 2.1),
      ma20: kline.map((item) => item.close - 3.4),
    },
    subIndicators: {
      volMa: kline.map((item) => item.volume * 0.92),
      macd: {
        dif: kline.map((_, index) => index * 0.06),
        dea: kline.map((_, index) => index * 0.05),
        bar: kline.map((_, index) => index * 0.02),
      },
      rsi: {
        rsi6: kline.map(() => 68),
        rsi12: kline.map(() => 62),
        rsi24: kline.map(() => 58),
      },
    },
    meta: {
      timeframe: 'day',
      window: '30',
      barCount: 260,
      updatedAt: '2026-04-22T10:30:00',
    },
    latestReview: {
      id: 1001,
      signalEventId: 101,
      reviewRound: 1,
      decision: 'buyable',
      confidence: 0.88,
      summary: '可跟踪',
    },
    ...overrides,
  };
}

function renderWatchPage() {
  return render(
    <MemoryRouter>
      <WatchPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  mockGetTargets.mockResolvedValue({
    total: 1,
    page: 1,
    limit: 20,
    items: [
      {
        id: 1,
        targetKind: 'stock',
        targetKey: '600519',
        displayName: '贵州茅台',
        status: 'active',
        memberCount: 1,
        summary: {
          status: 'ready',
          summaryWindowDays: 7,
          signalScore: 82,
          action: '买入',
          brief: '近7日趋势偏强，可继续跟踪',
          trendStatus: '多头排列',
        },
      },
    ],
  });

  mockGetEvents.mockResolvedValue({
    total: 1,
    page: 1,
    limit: 20,
    items: [
      {
        id: 101,
        targetId: 1,
        memberCode: '600519',
        memberName: '贵州茅台',
        signalDate: '2026-04-21',
        signalType: 'stage_buy_point',
        signalScore: 68,
        status: 'accepted',
        dedupeKey: '1:600519:2026-04-21:stage_buy_point:v1',
        latestReviewSummary: {
          id: 1001,
          signalEventId: 101,
          reviewRound: 1,
          decision: 'buyable',
          confidence: 0.88,
          summary: '可跟踪',
        },
      },
    ],
  });

  mockGetRuntimeStatus.mockResolvedValue({
    enabled: false,
    registered: false,
    scanIntervalMinutes: 45,
    lastScanAt: null,
    lastError: null,
  });

  mockStartRuntime.mockResolvedValue({
    enabled: true,
    registered: false,
    scanIntervalMinutes: 45,
    lastScanAt: null,
    lastError: null,
  });

  mockStopRuntime.mockResolvedValue({
    enabled: false,
    registered: false,
    scanIntervalMinutes: 45,
    lastScanAt: null,
    lastError: null,
  });

  mockScanAllTargetsOnce.mockResolvedValue({
    processedTargets: 1,
    emittedEvents: 1,
  });

  mockScanTargetOnce.mockResolvedValue({
    targetId: 1,
    emittedEvents: 1,
  });

  mockCreateTarget.mockResolvedValue({
    id: 2,
    targetKind: 'theme',
    targetKey: 'compute_power',
    displayName: '算力',
    status: 'active',
    memberCount: 4,
  });

  mockGetTargetDetail.mockResolvedValue(createDefaultDetail());
});

describe('Watch page', () => {
  it('renders the new 跟踪 nav item', () => {
    render(
      <MemoryRouter initialEntries={['/watch']}>
        <SidebarNav />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: '跟踪' })).toBeInTheDocument();
  });

  it('renders the workstation layout and top action bar', async () => {
    renderWatchPage();

    expect(await screen.findByTestId('watch-page')).toBeInTheDocument();
    expect(screen.getByText('目标池')).toBeInTheDocument();
    expect(screen.getByText('行情工作台')).toBeInTheDocument();
    expect(screen.getByText('候选事件')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '刷新数据' }));
    await waitFor(() => expect(mockGetTargets).toHaveBeenCalledTimes(2));
    expect(mockGetEvents).toHaveBeenCalledTimes(2);
    expect(mockGetRuntimeStatus).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getByRole('button', { name: '全量扫描一次' }));
    await waitFor(() => expect(mockScanAllTargetsOnce).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole('button', { name: '启动监测' }));
    await waitFor(() => expect(mockStartRuntime).toHaveBeenCalledTimes(1));
    expect((await screen.findAllByText('运行中')).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '停止监测' }));
    await waitFor(() => expect(mockStopRuntime).toHaveBeenCalledTimes(1));
    expect((await screen.findAllByText('已停止')).length).toBeGreaterThan(0);
  });

  it('opens the market workstation, shows explicit single-target scan buttons, and creates a target', async () => {
    renderWatchPage();

    expect(await screen.findByText('近7日趋势偏强，可继续跟踪')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '打开工作台' }));

    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenCalledWith(1, {
        memberCode: undefined,
        period: 'day',
        range: '30',
      }),
    );

    expect(await screen.findByText('主升趋势维持')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '分时' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '日K' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '周K' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '月K' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '30日' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '60日' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '120日' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '250日' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '年内' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'VOL' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'MACD' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'RSI' })).toBeInTheDocument();

    const scanButtons = screen.getAllByRole('button', { name: '仅扫描当前目标' });
    expect(scanButtons).toHaveLength(2);

    fireEvent.click(scanButtons[0]);
    await waitFor(() => expect(mockScanTargetOnce).toHaveBeenCalledWith(1));

    fireEvent.click(scanButtons[1]);
    await waitFor(() => expect(mockScanTargetOnce).toHaveBeenCalledTimes(2));

    fireEvent.change(screen.getByPlaceholderText('输入股票代码、ETF 代码或主题名'), {
      target: { value: '算力' },
    });
    fireEvent.click(screen.getByRole('button', { name: '添加跟踪目标' }));

    await waitFor(() =>
      expect(mockCreateTarget).toHaveBeenCalledWith({
        inputText: '算力',
        displayName: undefined,
        targetKind: undefined,
      }),
    );
  });

  it('switches timeframe, day-range, indicator panels, and theme members', async () => {
    mockGetTargets.mockResolvedValueOnce({
      total: 1,
      page: 1,
      limit: 20,
      items: [
        {
          id: 2,
          targetKind: 'theme',
          targetKey: 'compute_power',
          displayName: '算力',
          status: 'active',
          memberCount: 4,
          summary: {
            status: 'ready',
            summaryWindowDays: 7,
            signalScore: 75,
            action: '买入',
            brief: '主题近7日偏强，代表标的浪潮信息领涨',
            representativeMemberCode: '000977',
            representativeMemberName: '浪潮信息',
          },
        },
      ],
    });

    mockGetTargetDetail.mockResolvedValueOnce(
      createDefaultDetail({
        target: {
          id: 2,
          targetKind: 'theme',
          targetKey: 'compute_power',
          displayName: '算力',
          status: 'active',
          memberCount: 4,
        },
        summary: {
          status: 'ready',
          summaryWindowDays: 7,
          signalScore: 75,
          action: '买入',
          brief: '主题近7日偏强，代表标的浪潮信息领涨',
          representativeMemberCode: '000977',
          representativeMemberName: '浪潮信息',
        },
        memberOptions: [
          { id: 21, memberCode: '000977', memberName: '浪潮信息', memberKind: 'stock' },
          { id: 22, memberCode: '603019', memberName: '中科曙光', memberKind: 'stock' },
        ],
        activeMember: { id: 21, memberCode: '000977', memberName: '浪潮信息', memberKind: 'stock' },
      }),
    );

    mockGetTargetDetail.mockResolvedValueOnce(
      createDefaultDetail({
        target: {
          id: 2,
          targetKind: 'theme',
          targetKey: 'compute_power',
          displayName: '算力',
          status: 'active',
          memberCount: 4,
        },
        memberOptions: [
          { id: 21, memberCode: '000977', memberName: '浪潮信息', memberKind: 'stock' },
          { id: 22, memberCode: '603019', memberName: '中科曙光', memberKind: 'stock' },
        ],
        activeMember: { id: 22, memberCode: '603019', memberName: '中科曙光', memberKind: 'stock' },
      }),
    );

    renderWatchPage();

    expect(await screen.findByText('主题近7日偏强，代表标的浪潮信息领涨')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '打开工作台' }));

    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenCalledWith(2, {
        memberCode: undefined,
        period: 'day',
        range: '30',
      }),
    );
    await screen.findByRole('button', { name: '周K' });

    fireEvent.click(screen.getByRole('button', { name: '周K' }));
    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenLastCalledWith(2, {
        memberCode: undefined,
        period: 'week',
        range: '30',
      }),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: '周K' })).toHaveAttribute('aria-pressed', 'true'),
    );

    fireEvent.click(screen.getByRole('button', { name: '月K' }));
    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenLastCalledWith(2, {
        memberCode: undefined,
        period: 'month',
        range: '30',
      }),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: '月K' })).toHaveAttribute('aria-pressed', 'true'),
    );

    fireEvent.click(screen.getByRole('button', { name: '分时' }));
    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenLastCalledWith(2, {
        memberCode: undefined,
        period: 'intraday',
        range: '30',
      }),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: '分时' })).toHaveAttribute('aria-pressed', 'true'),
    );

    fireEvent.click(screen.getByRole('button', { name: '日K' }));
    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenLastCalledWith(2, {
        memberCode: undefined,
        period: 'day',
        range: '30',
      }),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: '日K' })).toHaveAttribute('aria-pressed', 'true'),
    );
    fireEvent.click(screen.getByRole('button', { name: '120日' }));
    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenLastCalledWith(2, {
        memberCode: undefined,
        period: 'day',
        range: '120',
      }),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: '120日' })).toHaveAttribute('aria-pressed', 'true'),
    );

    fireEvent.click(screen.getByRole('button', { name: 'RSI' }));
    expect(screen.getByRole('button', { name: 'RSI' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.change(screen.getByLabelText('详情成员切换'), {
      target: { value: '603019' },
    });

    await waitFor(() =>
      expect(mockGetTargetDetail).toHaveBeenLastCalledWith(2, {
        memberCode: '603019',
        period: 'day',
        range: '120',
      }),
    );
  });

  it('refreshes the active detail when a related SSE event arrives', async () => {
    renderWatchPage();

    expect(await screen.findByText('近7日趋势偏强，可继续跟踪')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '打开工作台' }));
    await waitFor(() => expect(mockGetTargetDetail).toHaveBeenCalledTimes(1));

    const streamOptions = mockUseWatchStream.mock.lastCall?.[0] as {
      onEvent?: (event: { eventType: string; payload?: Record<string, unknown> }) => void;
    };
    streamOptions.onEvent?.({
      eventType: 'watch.review.updated',
      payload: { targetId: 1 },
    });

    await waitFor(() => expect(mockGetTargetDetail).toHaveBeenCalledTimes(2));
  });

  it('ignores stale detail responses and keeps the latest selection', async () => {
    const first = createDeferred<WatchTargetDetail>();
    const second = createDeferred<WatchTargetDetail>();

    mockGetTargets.mockResolvedValueOnce({
      total: 2,
      page: 1,
      limit: 20,
      items: [
        {
          id: 1,
          targetKind: 'stock',
          targetKey: '600519',
          displayName: '贵州茅台',
          status: 'active',
          memberCount: 1,
          summary: { status: 'ready', summaryWindowDays: 7, brief: '茅台摘要' },
        },
        {
          id: 2,
          targetKind: 'stock',
          targetKey: '603019',
          displayName: '中科曙光',
          status: 'active',
          memberCount: 1,
          summary: { status: 'ready', summaryWindowDays: 7, brief: '曙光摘要' },
        },
      ],
    });

    mockGetTargetDetail
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);

    renderWatchPage();

    expect(await screen.findByText('茅台摘要')).toBeInTheDocument();
    expect(screen.getByText('曙光摘要')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: '打开工作台' })[0]);
    fireEvent.click(screen.getAllByRole('button', { name: '打开工作台' })[1]);

    second.resolve(
      createDefaultDetail({
        target: {
          id: 2,
          targetKind: 'stock',
          targetKey: '603019',
          displayName: '中科曙光',
          status: 'active',
          memberCount: 1,
        },
        summary: {
          status: 'ready',
          summaryWindowDays: 7,
          brief: '曙光详情',
        },
        activeMember: {
          id: 22,
          memberCode: '603019',
          memberName: '中科曙光',
          memberKind: 'stock',
        },
        memberOptions: [
          { id: 22, memberCode: '603019', memberName: '中科曙光', memberKind: 'stock' },
        ],
        strategyInsights: {
          signalReasons: ['曙光信号'],
          riskFactors: ['曙光风险'],
          action: '买入',
        },
      }),
    );

    await screen.findByText('曙光信号');

    first.resolve(
      createDefaultDetail({
        target: {
          id: 1,
          targetKind: 'stock',
          targetKey: '600519',
          displayName: '贵州茅台',
          status: 'active',
          memberCount: 1,
        },
        summary: {
          status: 'ready',
          summaryWindowDays: 7,
          brief: '茅台详情',
        },
        memberOptions: [
          { id: 11, memberCode: '600519', memberName: '贵州茅台', memberKind: 'stock' },
        ],
        activeMember: {
          id: 11,
          memberCode: '600519',
          memberName: '贵州茅台',
          memberKind: 'stock',
        },
        strategyInsights: {
          signalReasons: ['茅台信号'],
          riskFactors: ['茅台风险'],
          action: '买入',
        },
      }),
    );

    await waitFor(() => expect(screen.queryByText('茅台信号')).not.toBeInTheDocument());
    expect(screen.getByText('曙光信号')).toBeInTheDocument();
  });

  it('does not re-aggregate weekly or monthly bars that already match the requested timeframe', () => {
    const weekDetail = createDefaultDetail({
      kline: [
        { date: '2026-04-03', open: 10, high: 12, low: 9, close: 11, volume: 1000 },
        { date: '2026-04-10', open: 11, high: 13, low: 10, close: 12, volume: 1100 },
        { date: '2026-04-17', open: 12, high: 14, low: 11, close: 13, volume: 1200 },
      ],
      overlays: {
        ma5: [10.2, 11.2, 12.2],
        ma10: [9.8, 10.8, 11.8],
        ma20: [9.1, 10.1, 11.1],
      },
      subIndicators: {
        volMa: [950, 1025, 1110],
        macd: { dif: [0.1, 0.2, 0.3], dea: [0.05, 0.15, 0.25], bar: [0.1, 0.1, 0.1] },
        rsi: { rsi6: [60, 65, 70], rsi12: [58, 63, 68], rsi24: [56, 61, 66] },
      },
      meta: { timeframe: 'week', window: '30', barCount: 3, updatedAt: '2026-04-22T10:30:00' },
    });
    const monthDetail = createDefaultDetail({
      kline: [
        { date: '2026-02-28', open: 20, high: 24, low: 18, close: 22, volume: 5000 },
        { date: '2026-03-31', open: 22, high: 26, low: 21, close: 25, volume: 5200 },
        { date: '2026-04-30', open: 25, high: 29, low: 24, close: 28, volume: 5400 },
      ],
      overlays: {
        ma5: [20.5, 22.1, 24.6],
        ma10: [19.8, 21.4, 23.7],
        ma20: [18.9, 20.6, 22.8],
      },
      subIndicators: {
        volMa: [4800, 5000, 5200],
        macd: { dif: [0.6, 0.9, 1.2], dea: [0.4, 0.7, 1.0], bar: [0.2, 0.2, 0.2] },
        rsi: { rsi6: [62, 67, 72], rsi12: [59, 64, 69], rsi24: [57, 62, 67] },
      },
      meta: { timeframe: 'month', window: '120', barCount: 3, updatedAt: '2026-04-22T10:30:00' },
    });

    expect(buildCandleData(weekDetail, 'week').map((item) => item.label)).toEqual([
      '2026-04-03',
      '2026-04-10',
      '2026-04-17',
    ]);
    expect(buildCandleData(monthDetail, 'month').map((item) => item.label)).toEqual([
      '2026-02-28',
      '2026-03-31',
      '2026-04-30',
    ]);
  });
});
