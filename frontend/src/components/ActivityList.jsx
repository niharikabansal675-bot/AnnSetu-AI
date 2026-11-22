
import React from 'react';
import { Activity } from 'lucide-react';
import { fmt, cap } from '../utils/formatters';
import Empty from './EmptyState';

function ActivityList({ items = [] }) {
  return items.length ? (
    <div className="activity-list">
      {items.map((a) => (
        <div className="activity-row" key={a.id}>
          <span className="activity-symbol">
            <Activity size={16} />
          </span>

          <div>
            <b>{cap(a.action)}</b>
            <p>{a.detail}</p>
          </div>

          <span className="activity-time">
            {fmt(a.created_at)}
          </span>
        </div>
      ))}
    </div>
  ) : (
    <Empty
      title="Nothing here yet"
      description="Events and decisions will appear here as the platform is used."
    />
  );
}

export default ActivityList;