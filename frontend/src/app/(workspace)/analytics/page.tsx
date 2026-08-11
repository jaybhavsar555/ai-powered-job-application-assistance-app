"use client";

import { useEffect, useState } from "react";
import { 
  Activity, BrainCircuit, DollarSign, Clock, CheckCircle, 
  Filter, Zap
} from "lucide-react";
import { useAuthStore } from "@/store/auth";

interface AgentBreakdown {
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

interface StageCount {
  stage: string;
  count: number;
}

interface AnalyticsSummary {
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
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await fetch("/api/v1/analytics/summary", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (err) {
        console.error("Failed to fetch analytics summary", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchAnalytics();
    }
  }, [token]);

  if (loading) {
    return (
      <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8 animate-pulse">
        <div className="h-12 w-64 bg-muted rounded"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-muted"></div>
          ))}
        </div>
        <div className="h-64 rounded-xl bg-muted"></div>
      </div>
    );
  }

  const formatCost = (cost: number) => {
    return cost < 0.01 && cost > 0 
      ? `<$0.01` 
      : `$${cost.toFixed(2)}`;
  };

  const pipelineStages = ["Wishlist", "Applied", "Interviewing", "Offer", "Rejected"];
  const getPipelineCount = (stage: string) => {
    const s = data?.pipeline?.find(p => p.stage.toLowerCase() === stage.toLowerCase());
    return s ? s.count : 0;
  };
  
  const totalPipeline = data?.pipeline?.reduce((sum, item) => sum + item.count, 0) || 1;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-4xl font-bold tracking-tight mb-2">Analytics</h1>
        <p className="text-muted-foreground text-lg">Track your AI agent telemetry and application funnel.</p>
      </div>

      {/* Top Level KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Agent Runs"
          value={data?.total_runs?.toString() || "0"}
          icon={<Activity className="h-6 w-6 text-blue-500" />}
        />
        <MetricCard
          title="Avg Latency (ms)"
          value={Math.round(data?.avg_latency_ms || 0).toLocaleString()}
          icon={<Clock className="h-6 w-6 text-amber-500" />}
        />
        <MetricCard
          title="Global Success Rate"
          value={`${Math.round((data?.success_rate || 0) * 100)}%`}
          icon={<CheckCircle className="h-6 w-6 text-green-500" />}
        />
        <MetricCard
          title="Estimated API Cost"
          value={formatCost(data?.estimated_cost || 0)}
          icon={<DollarSign className="h-6 w-6 text-purple-500" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Pipeline Funnel */}
        <div className="lg:col-span-1 rounded-xl border bg-card p-6 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 mb-6">
            <Filter className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Application Funnel</h2>
          </div>
          <div className="flex-1 flex flex-col justify-center space-y-6">
            {pipelineStages.map((stage) => {
              const count = getPipelineCount(stage);
              const percentage = Math.max((count / totalPipeline) * 100, 2); // min width 2%
              return (
                <div key={stage} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium text-foreground">{stage}</span>
                    <span className="text-muted-foreground">{count}</span>
                  </div>
                  <div className="h-4 w-full bg-muted rounded-full overflow-hidden flex justify-start">
                    <div 
                      className={`h-full rounded-full bg-primary/80 transition-all duration-1000`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Agent Breakdown */}
        <div className="lg:col-span-2 rounded-xl border bg-card p-6 shadow-sm overflow-hidden flex flex-col">
          <div className="flex items-center gap-2 mb-6">
            <BrainCircuit className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Agent Telemetry</h2>
          </div>
          
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b">
                <tr>
                  <th className="px-4 py-3 rounded-tl-lg">Agent Name</th>
                  <th className="px-4 py-3">Runs</th>
                  <th className="px-4 py-3">Success Rate</th>
                  <th className="px-4 py-3">Tokens</th>
                  <th className="px-4 py-3 rounded-tr-lg">Est. Cost</th>
                </tr>
              </thead>
              <tbody>
                {data?.agents && data.agents.length > 0 ? (
                  data.agents.map((agent) => (
                    <tr key={agent.agent_name} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-4 font-medium flex items-center gap-2">
                        <Zap className="h-4 w-4 text-amber-500" />
                        {agent.agent_name}
                      </td>
                      <td className="px-4 py-4">{agent.runs}</td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <span className={agent.success_rate < 1 ? "text-destructive" : "text-green-500"}>
                            {Math.round(agent.success_rate * 100)}%
                          </span>
                          {agent.errors > 0 && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-destructive/10 text-destructive">
                              {agent.errors} err
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-muted-foreground">
                        {(agent.total_tokens / 1000).toFixed(1)}k
                      </td>
                      <td className="px-4 py-4 font-medium">
                        {formatCost(agent.estimated_cost)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      No agent telemetry recorded yet. Import a job to start!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon }: { title: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm hover:shadow-md transition-shadow group">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        <div className="p-2 bg-primary/5 rounded-full group-hover:bg-primary/10 transition-colors">{icon}</div>
      </div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  );
}
