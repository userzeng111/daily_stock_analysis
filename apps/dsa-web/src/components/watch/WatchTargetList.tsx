import type React from 'react';
import { Badge, EmptyState } from '../common';
import { cn } from '../../utils/cn';
import type { WatchTargetItem } from '../../types/watch';

const statusVariant = (status?: string | null) => {
  if (status === 'ready') return 'success';
  if (status === 'failed') return 'danger';
  return 'default';
};

type WatchTargetListProps = {
  targets: WatchTargetItem[];
  selectedTargetId: number | null;
  onSelectTarget: (targetId: number) => void;
  onScanTarget: (targetId: number) => void;
  isScanningTarget: boolean;
};

export const WatchTargetList: React.FC<WatchTargetListProps> = ({
  targets,
  selectedTargetId,
  onSelectTarget,
  onScanTarget,
  isScanningTarget,
}) => {
  if (targets.length === 0) {
    return (
      <EmptyState
        title="暂无跟踪目标"
        description="添加一个股票、ETF 或主题后，这里会显示监测篮子。"
      />
    );
  }

  return (
    <div className="space-y-3">
      {targets.map((target) => {
        const isActive = target.id === selectedTargetId;

        return (
          <article
            key={target.id}
            className={cn(
              'rounded-3xl border border-border/60 bg-surface/45 p-4 transition-all',
              isActive && 'border-danger/35 bg-danger/6 shadow-[0_24px_70px_-46px_rgba(225,29,72,0.55)]',
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-base font-semibold text-foreground">{target.displayName}</span>
                  <Badge variant={target.status === 'active' ? 'success' : 'warning'}>{target.status}</Badge>
                  {target.summary?.status ? (
                    <Badge variant={statusVariant(target.summary.status)}>{target.summary.status}</Badge>
                  ) : null}
                </div>
                <p className="text-sm text-secondary-text">
                  {target.targetKey} · {target.targetKind} · 成员 {target.memberCount}
                </p>
                <div className="flex flex-wrap gap-2 text-xs text-secondary-text">
                  {target.summary?.trendStatus ? <Badge>{target.summary.trendStatus}</Badge> : null}
                  {target.summary?.signalScore != null ? (
                    <Badge variant="info">评分 {target.summary.signalScore}</Badge>
                  ) : null}
                  {target.summary?.action ? <Badge variant="warning">{target.summary.action}</Badge> : null}
                </div>
                <p className="line-clamp-2 text-sm text-foreground">
                  {target.summary?.brief || '摘要生成中'}
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className={isActive ? 'btn-primary' : 'btn-secondary'}
                onClick={() => onSelectTarget(target.id)}
              >
                打开工作台
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={isScanningTarget}
                onClick={() => onScanTarget(target.id)}
              >
                仅扫描当前目标
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
};
