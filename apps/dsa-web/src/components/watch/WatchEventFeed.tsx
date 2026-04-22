import type React from 'react';
import { Badge, EmptyState } from '../common';
import type { WatchSignalEventItem } from '../../types/watch';

const eventDecisionLabel = (event: WatchSignalEventItem) =>
  event.latestReviewSummary?.summary || event.latestReviewSummary?.decision || event.status;

type WatchEventFeedProps = {
  events: WatchSignalEventItem[];
};

export const WatchEventFeed: React.FC<WatchEventFeedProps> = ({ events }) => {
  if (events.length === 0) {
    return (
      <EmptyState title="暂无候选事件" description="监测启动后，阶段性买点会出现在这里。" />
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <article
          key={event.id}
          className="rounded-3xl border border-border/60 bg-surface/45 p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-base font-semibold text-foreground">
                  {event.memberName || event.memberCode}
                </span>
                <Badge variant={event.status === 'accepted' ? 'success' : 'default'}>
                  {event.status}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-secondary-text">
                {event.memberCode} · 评分 {event.signalScore ?? '--'} · {event.signalDate ?? '--'}
              </p>
              <p className="mt-3 text-sm text-foreground">{eventDecisionLabel(event)}</p>
            </div>
            <div className="rounded-2xl border border-border/50 px-3 py-2 text-right text-xs text-secondary-text">
              <div>{event.signalType}</div>
              <div className="mt-1">#{event.id}</div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
};
