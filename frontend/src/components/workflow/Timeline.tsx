import { useWorkflowStore } from '@/hooks/useWorkflowStore';
import { CheckCircle2, Clock, Loader2, PlayCircle } from 'lucide-react';

export function Timeline() {
  const { events, workflowStatus: status } = useWorkflowStore();

  return (
    <div className="flex flex-col space-y-4 p-4 border border-border rounded-xl bg-card h-[600px] overflow-y-auto">
      <h3 className="font-semibold text-lg flex items-center gap-2">
        Execution Timeline
        {status === 'running' && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
      </h3>
      
      <div className="relative border-l border-border ml-3 space-y-6">
        {events.map((evt, idx) => (
          <div key={idx} className="relative pl-6">
            <span className="absolute -left-[11px] top-1 bg-background">
              {evt.type === 'AGENT_STARTED' ? (
                <PlayCircle className="w-5 h-5 text-blue-500 bg-background" />
              ) : evt.type === 'AGENT_SUCCESS' ? (
                <CheckCircle2 className="w-5 h-5 text-green-500 bg-background" />
              ) : (
                <div className="w-5 h-5" />
              )}
            </span>
            <div className="flex flex-col">
              <span className="text-sm font-medium">{evt.agent || evt.type}</span>
              <span className="text-xs text-muted-foreground flex items-center gap-1 mt-2">
                <Clock className="w-3 h-3" />
                {new Date(evt.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
        {events.length === 0 && status === 'idle' && (
          <div className="text-sm text-muted-foreground pl-6">Waiting for workflow to start...</div>
        )}
        {status === 'completed' && (
          <div className="relative pl-6">
             <span className="absolute -left-[11px] top-1 bg-background">
              <CheckCircle2 className="w-5 h-5 text-purple-500 bg-background" />
            </span>
            <span className="text-sm font-medium text-purple-500">Pipeline Paused for Human Approval</span>
          </div>
        )}
      </div>
    </div>
  );
}
