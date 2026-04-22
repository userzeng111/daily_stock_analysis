import type React from 'react';
import { useMemo, useState } from 'react';
import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Rectangle,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Badge, EmptyState } from '../common';
import { cn } from '../../utils/cn';
import { buildCandleData, type CandleDatum } from './chartData';
import type {
  WatchChartPeriod,
  WatchDayRange,
  WatchIndicatorPanel,
  WatchQuoteSnapshot,
  WatchTargetDetail,
} from '../../types/watch';

const UP_COLOR = '#ef4444';
const DOWN_COLOR = '#22c55e';

const DAY_RANGE_OPTIONS: Array<{ label: string; value: WatchDayRange }> = [
  { label: '30日', value: '30' },
  { label: '60日', value: '60' },
  { label: '120日', value: '120' },
  { label: '250日', value: '250' },
  { label: '年内', value: 'ytd' },
];

const PERIOD_OPTIONS: Array<{ label: string; value: WatchChartPeriod }> = [
  { label: '分时', value: 'intraday' },
  { label: '日K', value: 'day' },
  { label: '周K', value: 'week' },
  { label: '月K', value: 'month' },
];

const INDICATOR_OPTIONS: Array<{ label: string; value: WatchIndicatorPanel }> = [
  { label: 'VOL', value: 'vol' },
  { label: 'MACD', value: 'macd' },
  { label: 'RSI', value: 'rsi' },
];

type WatchMarketPanelProps = {
  detail: WatchTargetDetail | null;
  detailLoading: boolean;
  selectedPeriod: WatchChartPeriod;
  selectedRange: WatchDayRange;
  selectedIndicator: WatchIndicatorPanel;
  onPeriodChange: (period: WatchChartPeriod) => void;
  onRangeChange: (range: WatchDayRange) => void;
  onIndicatorChange: (indicator: WatchIndicatorPanel) => void;
  onMemberChange: (memberCode: string | undefined) => void;
  onScanTarget: (targetId: number) => void;
  isScanningTarget: boolean;
};

function formatPrice(value?: number | null, digits = 2) {
  if (value == null || Number.isNaN(value)) return '--';
  return Number(value).toFixed(digits);
}

function formatSignedPrice(value?: number | null, digits = 2) {
  if (value == null || Number.isNaN(value)) return '--';
  return `${value > 0 ? '+' : ''}${Number(value).toFixed(digits)}`;
}

function formatPercent(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '--';
  return `${value > 0 ? '+' : ''}${Number(value).toFixed(2)}%`;
}

function formatCompactNumber(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '--';
  return new Intl.NumberFormat('zh-CN', {
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDayLabel(dateValue: string) {
  const date = new Date(`${dateValue}T00:00:00`);
  if (Number.isNaN(date.getTime())) return dateValue;
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${month}/${day}`;
}

function buildIntradayData(detail: WatchTargetDetail) {
  const intraday = detail.intraday ?? [];
  if (intraday.length > 0) {
    const prevClose = detail.quoteSnapshot?.prevClose ?? detail.quote?.prevClose ?? intraday[0]?.price ?? 0;
    return intraday.map((item) => ({
      label: item.time,
      price: item.price,
      averagePrice: item.averagePrice ?? item.price,
      volume: item.volume ?? 0,
      isUp: item.price >= prevClose,
    }));
  }

  const fallbackBars = detail.kline.slice(-16);
  const fallbackPrevClose = fallbackBars[0]?.open ?? 0;
  return fallbackBars.map((item, index) => ({
    label: index === 0 ? '09:30' : `${10 + Math.floor(index / 4)}:${index % 2 === 0 ? '00' : '30'}`,
    price: item.close,
    averagePrice: (item.open + item.close) / 2,
    volume: item.volume,
    isUp: item.close >= fallbackPrevClose,
  }));
}

function resolveQuote(detail: WatchTargetDetail | null): WatchQuoteSnapshot | null {
  if (!detail) return null;
  if (detail.quoteSnapshot || detail.quote) {
    return detail.quoteSnapshot ?? detail.quote ?? null;
  }

  const last = detail.kline[detail.kline.length - 1];
  const previous = detail.kline[detail.kline.length - 2];
  if (!last) return null;

  const prevClose = previous?.close ?? last.open;
  const change = last.close - prevClose;
  return {
    latestPrice: last.close,
    change,
    changeAmount: change,
    changePct: prevClose ? (change / prevClose) * 100 : 0,
    high: last.high,
    low: last.low,
    open: last.open,
    prevClose,
    volume: last.volume,
  };
}

const toggleClass = (pressed: boolean) =>
  cn(
    'rounded-2xl border px-3 py-2 text-sm font-medium transition-all',
    pressed
      ? 'border-danger/35 bg-danger/12 text-foreground shadow-[0_16px_40px_-28px_rgba(239,68,68,0.65)]'
      : 'border-border/60 bg-surface/35 text-secondary-text hover:text-foreground',
  );

const priceTone = (value: number) => (value >= 0 ? 'text-danger' : 'text-success');

const CandleShape = (props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: CandleDatum;
}) => {
  const { x = 0, y = 0, width = 0, height = 0, payload } = props;
  if (!payload || width <= 0 || height <= 0) return null;

  const color = payload.isUp ? UP_COLOR : DOWN_COLOR;
  const maxBody = Math.max(payload.open, payload.close);
  const minBody = Math.min(payload.open, payload.close);
  const bodyTop = y + ((payload.high - maxBody) / payload.highLowRange) * height;
  const bodyHeight = Math.max(((maxBody - minBody) / payload.highLowRange) * height, 2);
  const centerX = x + width / 2;

  return (
    <g>
      <line
        x1={centerX}
        x2={centerX}
        y1={y}
        y2={y + height}
        stroke={color}
        strokeWidth={1.3}
      />
      <Rectangle
        x={x + width * 0.18}
        y={bodyTop}
        width={Math.max(width * 0.64, 4)}
        height={bodyHeight}
        radius={2}
        fill={payload.isUp ? 'rgba(239,68,68,0.24)' : 'rgba(34,197,94,0.24)'}
        stroke={color}
        strokeWidth={1.2}
      />
    </g>
  );
};

export const WatchMarketPanel: React.FC<WatchMarketPanelProps> = ({
  detail,
  detailLoading,
  selectedPeriod,
  selectedRange,
  selectedIndicator,
  onPeriodChange,
  onRangeChange,
  onIndicatorChange,
  onMemberChange,
  onScanTarget,
  isScanningTarget,
}) => {
  const quote = useMemo(() => resolveQuote(detail), [detail]);
  const candleData = useMemo(
    () => (detail ? buildCandleData(detail, selectedPeriod) : []),
    [detail, selectedPeriod],
  );
  const intradayData = useMemo(() => (detail ? buildIntradayData(detail) : []), [detail]);
  const [hoverLabel, setHoverLabel] = useState<string | null>(null);
  const latestLabel = (
    selectedPeriod === 'intraday'
      ? intradayData[intradayData.length - 1]?.label
      : candleData[candleData.length - 1]?.label
  ) ?? null;
  const activeLabel = hoverLabel ?? latestLabel;

  const activeCandle = activeLabel
    ? candleData.find((item) => item.label === activeLabel) ?? candleData[candleData.length - 1]
    : candleData[candleData.length - 1];
  const activeIntraday = activeLabel
    ? intradayData.find((item) => item.label === activeLabel) ?? intradayData[intradayData.length - 1]
    : intradayData[intradayData.length - 1];

  if (detailLoading) {
    return <EmptyState title="详情加载中" description="正在读取行情与策略信息。" />;
  }

  if (!detail) {
    return (
      <EmptyState
        title="未选择跟踪目标"
        description="选择左侧跟踪目标后，这里会展示分时、K 线、副图和策略面板。"
      />
    );
  }

  const latestChange = quote?.change ?? 0;
  const summaryAction = detail.strategyInsights.action ?? detail.summary.action ?? '--';
  const chartIsIntraday = selectedPeriod === 'intraday';
  const updateActiveLabelFromState = (state: unknown) => {
    const nextLabel = (state as { activePayload?: Array<{ payload?: { label?: string } }> } | null)
      ?.activePayload?.[0]?.payload?.label;
    setHoverLabel(nextLabel ?? null);
  };

  return (
    <div className="space-y-4">
      <section className="rounded-3xl border border-border/60 bg-surface/45 p-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-2xl font-semibold text-foreground">{detail.target.displayName}</span>
              <Badge variant={latestChange >= 0 ? 'warning' : 'success'}>
                {detail.activeMember.memberCode}
              </Badge>
              <Badge variant="default">{detail.target.targetKind}</Badge>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <div className={cn('text-4xl font-semibold', priceTone(latestChange))}>
                {formatPrice(quote?.latestPrice)}
              </div>
              <div className={cn('pb-1 text-sm font-medium', priceTone(latestChange))}>
                {formatSignedPrice(quote?.change)} / {formatPercent(quote?.changePct)}
              </div>
            </div>
            <p className="max-w-3xl text-sm text-secondary-text">
              {detail.summary.brief || '暂无摘要'}
            </p>
          </div>

          <div className="flex flex-col gap-3 xl:items-end">
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={isScanningTarget}
                onClick={() => onScanTarget(detail.target.id)}
              >
                仅扫描当前目标
              </button>
            </div>
            {detail.memberOptions.length > 1 ? (
              <div className="min-w-[240px]">
                <label
                  className="mb-2 block text-sm font-medium text-foreground"
                  htmlFor="watch-member-select"
                >
                  详情成员切换
                </label>
                <select
                  id="watch-member-select"
                  aria-label="详情成员切换"
                  className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm"
                  value={detail.activeMember.memberCode}
                  onChange={(event) => onMemberChange(event.target.value || undefined)}
                >
                  {detail.memberOptions.map((member) => (
                    <option key={member.memberCode} value={member.memberCode}>
                      {member.memberName} ({member.memberCode})
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        {[
          { label: '开盘', value: formatPrice(quote?.open) },
          { label: '最高 / 最低', value: `${formatPrice(quote?.high)} / ${formatPrice(quote?.low)}` },
          { label: '成交量', value: formatCompactNumber(quote?.volume) },
          { label: '成交额', value: formatCompactNumber(quote?.turnover) },
        ].map((item) => (
          <div key={item.label} className="rounded-3xl border border-border/60 bg-surface/40 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-secondary-text">{item.label}</div>
            <div className="mt-2 text-base font-semibold text-foreground">{item.value}</div>
          </div>
        ))}
      </section>

      <section className="rounded-3xl border border-border/60 bg-surface/45 p-4">
        <div className="flex flex-col gap-4 border-b border-border/50 pb-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-2">
            {PERIOD_OPTIONS.map((item) => (
              <button
                key={item.value}
                type="button"
                aria-pressed={selectedPeriod === item.value}
                className={toggleClass(selectedPeriod === item.value)}
                onClick={() => onPeriodChange(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {selectedPeriod === 'day'
              ? DAY_RANGE_OPTIONS.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    aria-pressed={selectedRange === item.value}
                    className={toggleClass(selectedRange === item.value)}
                    onClick={() => onRangeChange(item.value)}
                  >
                    {item.label}
                  </button>
                ))
              : null}
          </div>
        </div>

        <div className="mt-4 rounded-3xl border border-border/60 bg-[radial-gradient(circle_at_top,rgba(239,68,68,0.08),transparent_40%),linear-gradient(180deg,rgba(15,23,42,0.16),rgba(15,23,42,0.02))] p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 text-sm">
            <div className="flex flex-wrap items-center gap-4">
              <span className="font-medium text-foreground">
                {chartIsIntraday ? activeIntraday?.label : activeCandle?.label}
              </span>
              {chartIsIntraday ? (
                <>
                  <span className={cn('font-medium', priceTone((activeIntraday?.price ?? 0) - (quote?.prevClose ?? 0)))}>
                    价格 {formatPrice(activeIntraday?.price)}
                  </span>
                  <span className="text-secondary-text">均价 {formatPrice(activeIntraday?.averagePrice)}</span>
                  <span className="text-secondary-text">量 {formatCompactNumber(activeIntraday?.volume)}</span>
                </>
              ) : (
                <>
                  <span className={cn('font-medium', priceTone((activeCandle?.close ?? 0) - (activeCandle?.open ?? 0)))}>
                    O {formatPrice(activeCandle?.open)} / C {formatPrice(activeCandle?.close)}
                  </span>
                  <span className="text-secondary-text">H {formatPrice(activeCandle?.high)}</span>
                  <span className="text-secondary-text">L {formatPrice(activeCandle?.low)}</span>
                  <span className="text-secondary-text">VOL {formatCompactNumber(activeCandle?.volume)}</span>
                </>
              )}
            </div>
            <Badge variant={summaryAction === '买入' ? 'warning' : 'default'}>{summaryAction}</Badge>
          </div>

          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              {chartIsIntraday ? (
                <ComposedChart
                  data={intradayData}
                  margin={{ top: 10, right: 12, bottom: 6, left: 4 }}
                  onMouseLeave={() => setHoverLabel(null)}
                  onMouseMove={(state) => updateActiveLabelFromState(state)}
                >
                  <CartesianGrid stroke="rgba(148,163,184,0.16)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis
                    yAxisId="price"
                    orientation="right"
                    domain={['dataMin - 2', 'dataMax + 2']}
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) => formatPrice(Number(value))}
                  />
                  <YAxis yAxisId="volume" hide />
                  <Tooltip content={() => null} cursor={false} />
                  {activeIntraday?.label ? <ReferenceLine x={activeIntraday.label} stroke="rgba(148,163,184,0.38)" /> : null}
                  {activeIntraday?.price ? (
                    <ReferenceLine yAxisId="price" y={activeIntraday.price} stroke="rgba(148,163,184,0.28)" />
                  ) : null}
                  <Area
                    yAxisId="price"
                    type="monotone"
                    dataKey="price"
                    stroke={UP_COLOR}
                    fill="rgba(239,68,68,0.16)"
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                  <Line
                    yAxisId="price"
                    type="monotone"
                    dataKey="averagePrice"
                    stroke="#60a5fa"
                    dot={false}
                    strokeWidth={1.6}
                    isAnimationActive={false}
                  />
                  <Bar
                    yAxisId="volume"
                    dataKey="volume"
                    fill="rgba(148,163,184,0.18)"
                    maxBarSize={10}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              ) : (
                <ComposedChart
                  data={candleData}
                  margin={{ top: 10, right: 12, bottom: 6, left: 4 }}
                  onMouseLeave={() => setHoverLabel(null)}
                  onMouseMove={(state) => updateActiveLabelFromState(state)}
                >
                  <CartesianGrid stroke="rgba(148,163,184,0.16)" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) => formatDayLabel(String(value))}
                    minTickGap={28}
                  />
                  <YAxis
                    orientation="right"
                    domain={['dataMin - 2', 'dataMax + 2']}
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) => formatPrice(Number(value))}
                  />
                  <Tooltip content={() => null} cursor={false} />
                  {activeCandle?.label ? <ReferenceLine x={activeCandle.label} stroke="rgba(148,163,184,0.38)" /> : null}
                  {activeCandle?.close ? (
                    <ReferenceLine y={activeCandle.close} stroke="rgba(148,163,184,0.28)" />
                  ) : null}
                  <Bar dataKey="lowBase" stackId="candle" fill="transparent" isAnimationActive={false} />
                  <Bar
                    dataKey="highLowRange"
                    stackId="candle"
                    fill="transparent"
                    shape={<CandleShape />}
                    isAnimationActive={false}
                  />
                  <Line dataKey="ma5" stroke="#f59e0b" dot={false} strokeWidth={1.6} isAnimationActive={false} />
                  <Line dataKey="ma10" stroke="#38bdf8" dot={false} strokeWidth={1.6} isAnimationActive={false} />
                  <Line dataKey="ma20" stroke="#e879f9" dot={false} strokeWidth={1.4} isAnimationActive={false} />
                </ComposedChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-border/60 bg-surface/45 p-4">
        <div className="flex flex-col gap-4 border-b border-border/50 pb-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground">副图</h3>
            <p className="mt-1 text-sm text-secondary-text">VOL / MACD / RSI 快速切换</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {INDICATOR_OPTIONS.map((item) => (
              <button
                key={item.value}
                type="button"
                aria-pressed={selectedIndicator === item.value}
                className={toggleClass(selectedIndicator === item.value)}
                onClick={() => onIndicatorChange(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 h-[220px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={candleData} margin={{ top: 10, right: 12, bottom: 6, left: 4 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) => formatDayLabel(String(value))}
                minTickGap={28}
              />
              <YAxis
                orientation="right"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) =>
                  selectedIndicator === 'vol'
                    ? formatCompactNumber(Number(value))
                    : formatPrice(Number(value), 1)
                }
              />
              <Tooltip content={() => null} cursor={false} />
              {selectedIndicator === 'vol' ? (
                <>
                  <Bar dataKey="volume" maxBarSize={14} isAnimationActive={false}>
                    {candleData.map((item) => (
                      <Cell key={item.label} fill={item.isUp ? 'rgba(239,68,68,0.45)' : 'rgba(34,197,94,0.45)'} />
                    ))}
                  </Bar>
                  <Line dataKey="volMa" stroke="#f59e0b" dot={false} strokeWidth={1.6} isAnimationActive={false} />
                </>
              ) : null}
              {selectedIndicator === 'macd' ? (
                <>
                  <Bar dataKey="macd" maxBarSize={14} isAnimationActive={false}>
                    {candleData.map((item) => (
                      <Cell key={item.label} fill={item.macd >= 0 ? 'rgba(239,68,68,0.45)' : 'rgba(34,197,94,0.45)'} />
                    ))}
                  </Bar>
                  <Line dataKey="dif" stroke="#f97316" dot={false} strokeWidth={1.8} isAnimationActive={false} />
                  <Line dataKey="dea" stroke="#38bdf8" dot={false} strokeWidth={1.8} isAnimationActive={false} />
                </>
              ) : null}
              {selectedIndicator === 'rsi' ? (
                <>
                  <Line dataKey="rsi6" stroke="#f97316" dot={false} strokeWidth={1.8} isAnimationActive={false} />
                  <Line dataKey="rsi12" stroke="#38bdf8" dot={false} strokeWidth={1.6} isAnimationActive={false} />
                  <Line dataKey="rsi24" stroke="#e879f9" dot={false} strokeWidth={1.4} isAnimationActive={false} />
                </>
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl border border-border/60 bg-surface/45 p-4">
          <h3 className="text-base font-semibold text-foreground">策略解释</h3>
          <div className="mt-4 space-y-4 text-sm">
            <div>
              <div className="mb-2 text-secondary-text">信号原因</div>
              <div className="space-y-2 text-foreground">
                {(detail.strategyInsights.signalReasons ?? []).length > 0
                  ? detail.strategyInsights.signalReasons?.map((item) => <div key={item}>{item}</div>)
                  : '--'}
              </div>
            </div>
            <div>
              <div className="mb-2 text-secondary-text">风险因素</div>
              <div className="space-y-2 text-foreground">
                {(detail.strategyInsights.riskFactors ?? []).length > 0
                  ? detail.strategyInsights.riskFactors?.map((item) => <div key={item}>{item}</div>)
                  : '--'}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-border/60 bg-surface/45 p-4">
          <h3 className="text-base font-semibold text-foreground">关键位与复核</h3>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-2xl border border-border/50 p-3">
              <div className="text-secondary-text">MA5 / MA10 / MA20</div>
              <div className="mt-2 font-semibold text-foreground">
                {formatPrice(detail.indicators.ma5)} / {formatPrice(detail.indicators.ma10)} /{' '}
                {formatPrice(detail.indicators.ma20)}
              </div>
            </div>
            <div className="rounded-2xl border border-border/50 p-3">
              <div className="text-secondary-text">MACD / RSI / 量能</div>
              <div className="mt-2 font-semibold text-foreground">
                {detail.indicators.macdStatus ?? '--'} / {detail.indicators.rsiStatus ?? '--'} /{' '}
                {detail.indicators.volumeStatus ?? '--'}
              </div>
            </div>
            <div className="rounded-2xl border border-border/50 p-3">
              <div className="text-secondary-text">支撑位</div>
              <div className="mt-2 font-semibold text-foreground">
                {(detail.indicators.supportLevels ?? []).length > 0
                  ? detail.indicators.supportLevels?.map((item) => formatPrice(item)).join(' / ')
                  : '--'}
              </div>
            </div>
            <div className="rounded-2xl border border-border/50 p-3">
              <div className="text-secondary-text">压力位</div>
              <div className="mt-2 font-semibold text-foreground">
                {(detail.indicators.resistanceLevels ?? []).length > 0
                  ? detail.indicators.resistanceLevels?.map((item) => formatPrice(item)).join(' / ')
                  : '--'}
              </div>
            </div>
            <div className="col-span-2 rounded-2xl border border-border/50 p-3">
              <div className="text-secondary-text">最新复核</div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Badge variant={detail.latestReview ? 'warning' : 'default'}>
                  {detail.latestReview?.decision ?? '待复核'}
                </Badge>
                <span className="text-foreground">{detail.latestReview?.summary ?? '暂无复核结论'}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
