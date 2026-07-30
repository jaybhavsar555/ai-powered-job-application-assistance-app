import React from 'react';
import { DollarSign, Cpu, Clock, Activity } from 'lucide-react';
import { TelemetryBadge } from './TelemetryBadge';

interface CostCardProps {
  totalCost: number;
  inputTokens: number;
  outputTokens: number;
  totalLatency: string;
}

export function CostCard({ totalCost, inputTokens, outputTokens, totalLatency }: CostCardProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-1.5 bg-primary/10 rounded-lg">
          <Activity className="h-4 w-4 text-primary" />
        </div>
        <h3 className="font-semibold text-sm">Execution Telemetry</h3>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Total Cost</span>
          <div className="flex items-center gap-1.5 text-lg font-bold text-foreground">
            <DollarSign className="h-4 w-4 text-green-500" />
            ${totalCost.toFixed(4)}
          </div>
        </div>
        
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Duration</span>
          <div className="flex items-center gap-1.5 text-lg font-bold text-foreground">
            <Clock className="h-4 w-4 text-blue-500" />
            {totalLatency}
          </div>
        </div>
      </div>

      <div className="flex gap-2 mt-4 pt-4 border-t border-border">
        <TelemetryBadge icon={Cpu} label="In" value={`${inputTokens} tkns`} colorClass="text-purple-400" />
        <TelemetryBadge icon={Cpu} label="Out" value={`${outputTokens} tkns`} colorClass="text-orange-400" />
      </div>
    </div>
  );
}
