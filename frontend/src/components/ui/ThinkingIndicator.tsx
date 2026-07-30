import React from 'react';

interface ThinkingIndicatorProps {
  status?: 'idle' | 'running' | 'success' | 'error';
  text?: string;
}

export function ThinkingIndicator({ status = 'running', text = 'Agent Thinking...' }: ThinkingIndicatorProps) {
  if (status === 'idle') return null;

  const colorMap = {
    running: 'bg-primary',
    success: 'bg-green-500',
    error: 'bg-red-500'
  };

  const textMap = {
    running: text,
    success: 'Completed',
    error: 'Failed'
  };

  const ringMap = {
    running: 'ring-primary/30',
    success: 'ring-green-500/30',
    error: 'ring-red-500/30'
  };

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex h-2.5 w-2.5">
        {status === 'running' && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${colorMap[status]}`}></span>
        )}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${colorMap[status]} ring-2 ${ringMap[status]}`}></span>
      </div>
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground animate-pulse">
        {textMap[status]}
      </span>
    </div>
  );
}
