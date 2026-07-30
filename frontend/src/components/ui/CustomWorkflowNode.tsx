import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Bot, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { ThinkingIndicator } from './ThinkingIndicator';

interface NodeData {
  label: string;
  status: 'idle' | 'running' | 'success' | 'error';
  cost?: number;
  tokens?: number;
}

export const CustomWorkflowNode = memo(({ data }: { data: NodeData }) => {
  const { label, status, cost, tokens } = data;
  const isRunning = status === 'running';
  const isError = status === 'error';
  const isSuccess = status === 'success';

  return (
    <div className={`px-4 py-3 shadow-md rounded-xl border-2 bg-card min-w-[200px] transition-all ${
      isRunning ? 'border-primary shadow-[0_0_15px_rgba(var(--primary),0.2)] scale-105' : 
      isError ? 'border-red-500' : 
      isSuccess ? 'border-green-500/50' : 'border-border'
    }`}>
      {/* Input Handle */}
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-muted border-2 border-border" />
      
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg ${
              isRunning ? 'bg-primary/20 text-primary' : 
              isError ? 'bg-red-500/20 text-red-500' :
              isSuccess ? 'bg-green-500/20 text-green-500' : 'bg-muted text-muted-foreground'
            }`}>
              {isError ? <AlertTriangle className="h-4 w-4" /> : 
               isSuccess ? <CheckCircle2 className="h-4 w-4" /> : 
               <Bot className="h-4 w-4" />}
            </div>
            <div className="font-semibold text-sm text-foreground">{label}</div>
          </div>
          
          <div className="scale-75 origin-right">
            <ThinkingIndicator status={status} />
          </div>
        </div>

        {/* Telemetry Footer */}
        {(cost !== undefined || tokens !== undefined) && (
          <div className="flex items-center justify-between pt-2 border-t border-border mt-1">
            {cost !== undefined && <span className="text-[10px] text-muted-foreground font-medium">${cost.toFixed(4)}</span>}
            {tokens !== undefined && <span className="text-[10px] text-muted-foreground font-medium">{tokens} tkns</span>}
          </div>
        )}
      </div>

      {/* Output Handle */}
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-muted border-2 border-border" />
    </div>
  );
});

CustomWorkflowNode.displayName = 'CustomWorkflowNode';
