import React from 'react';
import { LucideIcon } from 'lucide-react';

interface TelemetryBadgeProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  colorClass?: string;
}

export function TelemetryBadge({ icon: Icon, label, value, colorClass = "text-muted-foreground" }: TelemetryBadgeProps) {
  return (
    <div className="flex items-center gap-1.5 bg-muted/30 border border-border/50 px-2 py-1 rounded-md text-[10px] font-medium">
      <Icon className={`h-3 w-3 ${colorClass}`} />
      <span className="text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className="text-foreground">{value}</span>
    </div>
  );
}
