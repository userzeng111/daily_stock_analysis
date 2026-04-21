import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import WatchPage from '../src/pages/WatchPage';
import { SidebarNav } from '../src/components/layout/SidebarNav';

const {
  mockGetTargets,
  mockGetEvents,
  mockGetRuntimeStatus,
  mockStartRuntime,
  mockStopRuntime,
  mockCreateTarget,
  mockGetTargetDetail,
} = vi.hoisted(() => ({
  mockGetTargets: vi.fn(),
  mockGetEvents: vi.fn(),
  mockGetRuntimeStatus: vi.fn(),
  mockStartRuntime: vi.fn(),
  mockStopRuntime: vi.fn(),
  mockCreateTarget: vi.fn(),
  mockGetTargetDetail: vi.fn(),
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
    getStreamUrl: vi.fn(() => '/api/v1/watch/stream'),
  },
}));

vi.mock('../src/hooks/useWatchStream', () => ({
  useWatchStream: () => ({
    isConnected: true,
    reconnect: vi.fn(),
    disconnect: vi.fn(),
  }),
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
  mockCreateTarget.mockResolvedValue({
    id: 2,
    targetKind: 'theme',
    targetKey: 'compute_power',
    displayName: '算力',
    status: 'active',
    memberCount: 4,
  });
  mockGetTargetDetail.mockResolvedValue({
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
    kline: Array.from({ length: 7 }).map((_, index) => ({
      date: `2026-04-${String(index + 1).padStart(2, '0')}`,
      open: 10 + index,
      high: 11 + index,
      low: 9 + index,
      close: 10.5 + index,
      volume: 1000000 + index * 1000,
    })),
    indicators: {
      buySignal: '买入',
      signalScore: 82,
      ma5: 10.2,
      ma10: 9.9,
      ma20: 9.5,
      macdStatus: '金叉',
      rsiStatus: '强势买入',
      volumeStatus: '缩量回调',
      supportLevels: [9.8, 9.5],
      resistanceLevels: [10.8, 11.2],
    },
    strategyInsights: {
      signalReasons: ['测试信号'],
      riskFactors: ['等待放量确认'],
      action: '买入',
    },
    latestReview: {
      id: 1001,
      signalEventId: 101,
      reviewRound: 1,
      decision: 'buyable',
      confidence: 0.88,
      summary: '可跟踪',
    },
  });
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

  it('loads watch targets/events and toggles runtime', async () => {
    render(
      <MemoryRouter>
        <WatchPage />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId('watch-page')).toBeInTheDocument();
    expect((await screen.findAllByText('贵州茅台')).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText((_, node) => node?.textContent?.includes('600519') ?? false).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText('可跟踪')).toBeInTheDocument();
    expect(screen.getByText('近7日趋势偏强，可继续跟踪')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '启动监测' }));
    await waitFor(() => expect(mockStartRuntime).toHaveBeenCalled());
    expect(await screen.findByText('运行中')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '停止监测' }));
    await waitFor(() => expect(mockStopRuntime).toHaveBeenCalled());
    expect(await screen.findByText('已停止')).toBeInTheDocument();
  });

  it('opens target detail, switches window, and creates a target', async () => {
    render(
      <MemoryRouter>
        <WatchPage />
      </MemoryRouter>,
    );

    expect((await screen.findAllByText('贵州茅台')).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: '展开详情' }));

    await waitFor(() => expect(mockGetTargetDetail).toHaveBeenCalledWith(1, { window: 7 }));
    expect(await screen.findByText('测试信号')).toBeInTheDocument();
    expect(screen.getByText('跟踪详情')).toBeInTheDocument();
    expect(screen.getByText('9.8 / 9.5')).toBeInTheDocument();
    expect(screen.getByText('10.8 / 11.2')).toBeInTheDocument();

    mockGetTargetDetail.mockResolvedValueOnce({
      ...(await mockGetTargetDetail.mock.results[0].value),
      kline: Array.from({ length: 30 }).map((_, index) => ({
        date: `2026-03-${String((index % 30) + 1).padStart(2, '0')}`,
        open: 20 + index,
        high: 21 + index,
        low: 19 + index,
        close: 20.5 + index,
        volume: 2000000 + index * 1000,
      })),
    });
    fireEvent.click(screen.getByRole('button', { name: '30日' }));
    await waitFor(() => expect(mockGetTargetDetail).toHaveBeenLastCalledWith(1, { window: 30 }));

    fireEvent.change(screen.getByPlaceholderText('输入股票代码、ETF 代码或主题名'), {
      target: { value: '算力' },
    });
    fireEvent.click(screen.getByRole('button', { name: '添加跟踪目标' }));

    await waitFor(() => expect(mockCreateTarget).toHaveBeenCalledWith({
      inputText: '算力',
      displayName: undefined,
      targetKind: undefined,
    }));
  });

  it('supports theme member switching in detail panel', async () => {
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
    mockGetTargetDetail.mockResolvedValueOnce({
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
      kline: Array.from({ length: 7 }).map((_, index) => ({
        date: `2026-04-${String(index + 1).padStart(2, '0')}`,
        open: 30 + index,
        high: 31 + index,
        low: 29 + index,
        close: 30.5 + index,
        volume: 1000000 + index * 1000,
      })),
      indicators: {
        buySignal: '强烈买入',
        signalScore: 90,
      },
      strategyInsights: {
        signalReasons: ['代表成员领涨'],
        riskFactors: [],
        action: '强烈买入',
      },
      latestReview: null,
    });
    mockGetTargetDetail.mockResolvedValueOnce({
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
      activeMember: { id: 22, memberCode: '603019', memberName: '中科曙光', memberKind: 'stock' },
      kline: Array.from({ length: 7 }).map((_, index) => ({
        date: `2026-04-${String(index + 1).padStart(2, '0')}`,
        open: 20 + index,
        high: 21 + index,
        low: 19 + index,
        close: 20.5 + index,
        volume: 900000 + index * 1000,
      })),
      indicators: {
        buySignal: '买入',
        signalScore: 71,
      },
      strategyInsights: {
        signalReasons: ['次级成员跟涨'],
        riskFactors: ['观察量能'],
        action: '买入',
      },
      latestReview: null,
    });

    render(
      <MemoryRouter>
        <WatchPage />
      </MemoryRouter>,
    );

    await screen.findByText('主题近7日偏强，代表标的浪潮信息领涨');
    fireEvent.click(screen.getByRole('button', { name: '展开详情' }));
    await waitFor(() => expect(mockGetTargetDetail).toHaveBeenCalledWith(2, { window: 7 }));

    fireEvent.change(screen.getByLabelText('详情成员切换'), {
      target: { value: '603019' },
    });
    await waitFor(() => expect(mockGetTargetDetail).toHaveBeenLastCalledWith(2, { window: 7, memberCode: '603019' }));
  });

  it('ignores stale detail responses and keeps the latest selection', async () => {
    const first = createDeferred<Awaited<ReturnType<typeof mockGetTargetDetail>>>();
    const second = createDeferred<Awaited<ReturnType<typeof mockGetTargetDetail>>>();

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

    render(
      <MemoryRouter>
        <WatchPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('茅台摘要')).toBeInTheDocument();
    expect(screen.getByText('曙光摘要')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: '展开详情' })[0]);
    fireEvent.click(screen.getAllByRole('button', { name: '展开详情' })[1]);

    second.resolve({
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
      memberOptions: [
        { id: 22, memberCode: '603019', memberName: '中科曙光', memberKind: 'stock' },
      ],
      activeMember: { id: 22, memberCode: '603019', memberName: '中科曙光', memberKind: 'stock' },
      kline: [],
      indicators: {
        buySignal: '买入',
        signalScore: 71,
        ma5: 20,
        ma10: 19,
        ma20: 18,
        macdStatus: '金叉',
        rsiStatus: '强势买入',
        volumeStatus: '缩量回调',
        supportLevels: [18.8],
        resistanceLevels: [21.2],
      },
      strategyInsights: {
        signalReasons: ['曙光信号'],
        riskFactors: ['曙光风险'],
        action: '买入',
      },
      latestReview: null,
    });

    await screen.findByText('曙光信号');

    first.resolve({
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
      activeMember: { id: 11, memberCode: '600519', memberName: '贵州茅台', memberKind: 'stock' },
      kline: [],
      indicators: {
        buySignal: '买入',
        signalScore: 82,
        ma5: 10,
        ma10: 9,
        ma20: 8,
        macdStatus: '金叉',
        rsiStatus: '强势买入',
        volumeStatus: '缩量回调',
        supportLevels: [8.8],
        resistanceLevels: [11.2],
      },
      strategyInsights: {
        signalReasons: ['茅台信号'],
        riskFactors: ['茅台风险'],
        action: '买入',
      },
      latestReview: null,
    });

    await waitFor(() => expect(screen.queryByText('茅台信号')).not.toBeInTheDocument());
    expect(screen.getByText('曙光信号')).toBeInTheDocument();
  });
});
