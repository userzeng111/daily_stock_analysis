import type { WatchChartPeriod, WatchTargetDetail } from '../../types/watch';

export type CandleDatum = {
  label: string;
  shortLabel: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  lowBase: number;
  highLowRange: number;
  isUp: boolean;
  ma5: number | null;
  ma10: number | null;
  ma20: number | null;
  volMa: number | null;
  macd: number;
  dif: number;
  dea: number;
  rsi6: number;
  rsi12: number;
  rsi24: number;
};

function calcEma(values: number[], period: number) {
  const factor = 2 / (period + 1);
  return values.reduce<number[]>((result, value, index) => {
    if (index === 0) {
      result.push(value);
      return result;
    }
    result.push(value * factor + result[index - 1] * (1 - factor));
    return result;
  }, []);
}

function calcMacd(values: number[]) {
  const ema12 = calcEma(values, 12);
  const ema26 = calcEma(values, 26);
  const dif = values.map((_, index) => ema12[index] - ema26[index]);
  const dea = calcEma(dif, 9);
  const macd = dif.map((value, index) => (value - dea[index]) * 2);
  return { dif, dea, macd };
}

function calcRsi(values: number[], period: number) {
  const result = new Array(values.length).fill(50);
  let avgGain = 0;
  let avgLoss = 0;

  for (let index = 1; index < values.length; index += 1) {
    const delta = values[index] - values[index - 1];
    const gain = Math.max(delta, 0);
    const loss = Math.max(-delta, 0);

    if (index <= period) {
      avgGain += gain;
      avgLoss += loss;
      result[index] = 50;
      if (index === period) {
        avgGain /= period;
        avgLoss /= period;
      }
      continue;
    }

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    if (avgLoss === 0) {
      result[index] = 100;
      continue;
    }
    const rs = avgGain / avgLoss;
    result[index] = 100 - 100 / (1 + rs);
  }

  return result;
}

function pickSeriesValue(
  series: Array<number | null> | undefined,
  index: number,
  fallback: number | null,
) {
  const value = series?.[index];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export function buildCandleData(detail: WatchTargetDetail, selectedPeriod: WatchChartPeriod) {
  const baseBars = detail.kline;
  const closes = baseBars.map((item) => item.close);
  const { dif, dea, macd } = calcMacd(closes);
  const rsi6 = calcRsi(closes, 6);
  const rsi12 = calcRsi(closes, 12);
  const rsi24 = calcRsi(closes, 24);
  const overlays = detail.overlays ?? undefined;
  const subIndicators = detail.subIndicators ?? undefined;
  const volMaFallback = calcEma(baseBars.map((item) => item.volume), 5);

  return baseBars.map((bar, index) => ({
    label: bar.date,
    shortLabel: selectedPeriod === 'month' ? bar.date.slice(0, 7) : bar.date,
    open: bar.open,
    high: bar.high,
    low: bar.low,
    close: bar.close,
    volume: bar.volume,
    lowBase: bar.low,
    highLowRange: Math.max(bar.high - bar.low, 0.001),
    isUp: bar.close >= bar.open,
    ma5: pickSeriesValue(overlays?.ma5, index, null),
    ma10: pickSeriesValue(overlays?.ma10, index, null),
    ma20: pickSeriesValue(overlays?.ma20, index, null),
    volMa: pickSeriesValue(subIndicators?.volMa, index, volMaFallback[index] ?? null),
    macd: pickSeriesValue(subIndicators?.macd?.bar, index, macd[index] ?? 0) ?? 0,
    dif: pickSeriesValue(subIndicators?.macd?.dif, index, dif[index] ?? 0) ?? 0,
    dea: pickSeriesValue(subIndicators?.macd?.dea, index, dea[index] ?? 0) ?? 0,
    rsi6: pickSeriesValue(subIndicators?.rsi?.rsi6, index, rsi6[index] ?? 50) ?? 50,
    rsi12: pickSeriesValue(subIndicators?.rsi?.rsi12, index, rsi12[index] ?? 50) ?? 50,
    rsi24: pickSeriesValue(subIndicators?.rsi?.rsi24, index, rsi24[index] ?? 50) ?? 50,
  }));
}
