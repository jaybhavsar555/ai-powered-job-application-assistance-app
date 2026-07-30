import React from 'react';
import { Bot, TerminalSquare, Database, ArrowRight } from 'lucide-react';
import { ThinkingIndicator } from './ThinkingIndicator';

interface AgentCardProps {
  name: string;
  description: string;
  status: 'idle' | 'running' | 'success' | 'error';
  capabilities: ('web' | 'db' | 'terminal' | 'write')[];
  onClick?: () => void;
}

export function AgentCard({ name, description, status, capabilities, onClick }: AgentCardProps) {
  const isRunning = status === 'running';

  return (
    <div 
      onClick={onClick}
      className={`relative group bg-card border rounded-xl overflow-hidden cursor-pointer transition-all ${
        isRunning ? 'border-primary shadow-[0_0_15px_rgba(var(--primary),0.15)]' : 'border-border hover:border-muted-foreground/30'
      }`}
    >
      <div className="p-4 flex gap-4">
        <div className={`mt-1 p-2.5 rounded-lg flex-shrink-0 ${isRunning ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
          <Bot className="h-5 w-5" />
        </div>
        
        <div className="flex-1 space-y-1">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-sm text-foreground">{name}</h4>
            <ThinkingIndicator status={status} />
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {description}
          </p>
        </div>
      </div>

      <div className="px-4 py-2 bg-muted/20 border-t border-border flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {capabilities.includes('web') && <div className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[9px] font-bold tracking-wider uppercase border border-blue-500/20">WEB</div>}
          {capabilities.includes('db') && <div className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 text-[9px] font-bold tracking-wider uppercase border border-purple-500/20">DB</div>}
          {capabilities.includes('terminal') && <div className="px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 text-[9px] font-bold tracking-wider uppercase border border-orange-500/20">CMD</div>}
        </div>
        <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
}
