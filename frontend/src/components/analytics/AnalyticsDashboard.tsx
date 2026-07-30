"use client";

import { CostCard } from "@/components/ui/CostCard";

interface SummaryStatProps {
  label: string;
  value: string;
  hint?: string;
}

function SummaryStat({ label, value, hint }: SummaryStatProps) {
  return (
    <div className="border border-border bg-card rounded-xl p-4 space-y-1">
      <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold tabular-nums text-foreground">{value}</p>
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

export interface AgentBreakdown {
  agent_name: string;
  runs: number;
  successes: number;
  errors: number;
  success_rate: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_latency_ms: number;
  avg_latency_ms: number;
  estimated_cost: number;
}

export interface StageCount {
  stage: string;
  count: number;
}

export interface RecentEvent {
  id: string;
  agent_name: string;
  action_type: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  estimated_cost: number;
  application_id?: string | null;
  created_at: string;
}

export interface AnalyticsSummary {
  total_runs: number;
  successes: number;
  errors: number;
  success_rate: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_latency_ms: number;
  avg_latency_ms: number;
  estimated_cost: number;
  applications_tracked: number;
  agents: AgentBreakdown[];
  pipeline: StageCount[];
  recent_events: RecentEvent[];
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

interface AnalyticsDashboardProps {
  data: AnalyticsSummary;
}

export function AnalyticsDashboard({ data }: AnalyticsDashboardProps) {
  const maxAgentRuns = Math.max(...data.agents.map((a) => a.runs), 1);
  const maxStageCount = Math.max(...data.pipeline.map((p) => p.count), 1);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryStat
          label="Success rate"
          value={`${data.success_rate.toFixed(1)}%`}
          hint={`${data.successes} ok · ${data.errors} err`}
        />
        <SummaryStat
          label="Agent runs"
          value={String(data.total_runs)}
          hint={`Avg ${formatMs(data.avg_latency_ms)}`}
        />
        <SummaryStat
          label="Total tokens"
          value={data.total_tokens.toLocaleString()}
          hint={`${data.total_input_tokens.toLocaleString()} in · ${data.total_output_tokens.toLocaleString()} out`}
        />
        <SummaryStat
          label="Applications"
          value={String(data.applications_tracked)}
          hint="In pipeline tracker"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1">
          <CostCard
            totalCost={data.estimated_cost}
            inputTokens={data.total_input_tokens}
            outputTokens={data.total_output_tokens}
            totalLatency={formatMs(data.total_latency_ms)}
          />
        </div>

        <div className="lg:col-span-2 border border-border bg-card rounded-xl p-4 space-y-4">
          <h3 className="font-semibold text-sm text-foreground">Pipeline distribution</h3>
          {data.pipeline.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No applications tracked yet.
            </p>
          ) : (
            <div className="space-y-3">
              {data.pipeline.map((stage) => (
                <div key={stage.stage} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-foreground font-medium">{stage.stage}</span>
                    <span className="text-muted-foreground tabular-nums">{stage.count}</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary/70 transition-all"
                      style={{ width: `${(stage.count / maxStageCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border border-border bg-card rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <h3 className="font-semibold text-sm text-foreground">Per-agent telemetry</h3>
        </div>
        {data.agents.length === 0 ? (
          <p className="text-sm text-muted-foreground p-8 text-center">
            Run a workflow on the Canvas to populate agent metrics.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground border-b border-border">
                  <th className="px-4 py-2.5 font-medium">Agent</th>
                  <th className="px-4 py-2.5 font-medium">Runs</th>
                  <th className="px-4 py-2.5 font-medium">Success</th>
                  <th className="px-4 py-2.5 font-medium">Avg latency</th>
                  <th className="px-4 py-2.5 font-medium">Tokens</th>
                  <th className="px-4 py-2.5 font-medium">Est. cost</th>
                </tr>
              </thead>
              <tbody>
                {data.agents.map((agent) => (
                  <tr
                    key={agent.agent_name}
                    className="border-b border-border/60 last:border-0 hover:bg-muted/20"
                  >
                    <td className="px-4 py-3">
                      <div className="space-y-1.5 min-w-[160px]">
                        <span className="font-medium text-foreground">{agent.agent_name}</span>
                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-sky-500/70"
                            style={{ width: `${(agent.runs / maxAgentRuns) * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 tabular-nums text-muted-foreground">{agent.runs}</td>
                    <td className="px-4 py-3 tabular-nums">
                      <span
                        className={
                          agent.success_rate >= 90
                            ? "text-emerald-400"
                            : agent.success_rate >= 70
                              ? "text-amber-400"
                              : "text-red-400"
                        }
                      >
                        {agent.success_rate.toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 tabular-nums text-muted-foreground">
                      {formatMs(agent.avg_latency_ms)}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-muted-foreground">
                      {agent.total_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-foreground">
                      ${agent.estimated_cost.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="border border-border bg-card rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <h3 className="font-semibold text-sm text-foreground">Recent agent events</h3>
        </div>
        {data.recent_events.length === 0 ? (
          <p className="text-sm text-muted-foreground p-8 text-center">No events logged yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {data.recent_events.map((ev) => (
              <li
                key={ev.id}
                className="px-4 py-3 flex flex-wrap items-center justify-between gap-2 text-sm"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                      ev.action_type === "error" ? "bg-red-400" : "bg-emerald-400"
                    }`}
                  />
                  <span className="font-medium text-foreground truncate">{ev.agent_name}</span>
                  <span className="text-xs text-muted-foreground capitalize">{ev.action_type}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                  <span>{formatMs(ev.latency_ms)}</span>
                  <span>{ev.input_tokens + ev.output_tokens} tkns</span>
                  <span>${ev.estimated_cost.toFixed(4)}</span>
                  <span>{new Date(ev.created_at).toLocaleString()}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
