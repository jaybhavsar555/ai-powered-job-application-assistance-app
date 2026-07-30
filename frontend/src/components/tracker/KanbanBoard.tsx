"use client";

import { useCallback, useEffect, useState } from "react";
import { Briefcase, RefreshCw, LayoutGrid } from "lucide-react";
import api from "@/lib/api";
import { Application, ApplicationStage } from "./ApplicationCard";
import { KanbanColumn } from "./KanbanColumn";

const STAGES: { stage: ApplicationStage; accent: string }[] = [
  { stage: "Wishlist", accent: "bg-slate-400" },
  { stage: "Researching", accent: "bg-sky-400" },
  { stage: "Ready", accent: "bg-emerald-400" },
  { stage: "Applied", accent: "bg-amber-400" },
  { stage: "Interview", accent: "bg-violet-400" },
  { stage: "Rejected", accent: "bg-red-400" },
];

export function KanbanBoard() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<ApplicationStage | null>(null);
  const [movingId, setMovingId] = useState<string | null>(null);

  const fetchApplications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Application[]>("/applications/");
      setApplications(data);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: string }).message)
          : "Failed to load applications";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const handleDragStart = (e: React.DragEvent, applicationId: string) => {
    e.dataTransfer.setData("applicationId", applicationId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, stage: ApplicationStage) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverStage(stage);
  };

  const handleDrop = async (e: React.DragEvent, stage: ApplicationStage) => {
    e.preventDefault();
    setDragOverStage(null);
    const applicationId = e.dataTransfer.getData("applicationId");
    if (!applicationId) return;

    const current = applications.find((a) => a.id === applicationId);
    if (!current || current.stage === stage) return;

    // Optimistic update
    setApplications((prev) =>
      prev.map((a) =>
        a.id === applicationId
          ? { ...a, stage, updated_at: new Date().toISOString() }
          : a
      )
    );
    setMovingId(applicationId);

    try {
      const { data } = await api.patch<Application>(
        `/applications/${applicationId}/stage`,
        { stage }
      );
      setApplications((prev) =>
        prev.map((a) => (a.id === applicationId ? data : a))
      );
    } catch {
      // Revert on failure
      setApplications((prev) =>
        prev.map((a) =>
          a.id === applicationId ? { ...a, stage: current.stage } : a
        )
      );
      setError("Failed to update stage. Changes reverted.");
    } finally {
      setMovingId(null);
    }
  };

  const byStage = (stage: ApplicationStage) =>
    applications.filter((a) => a.stage === stage);

  return (
    <div className="h-full min-h-0 flex flex-col p-8 space-y-6">
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Jobs Tracker</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Drag applications across pipeline stages
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground tabular-nums">
            {applications.length} application{applications.length !== 1 ? "s" : ""}
            {movingId && " · saving…"}
          </span>
          <button
            onClick={fetchApplications}
            disabled={loading}
            className="flex items-center gap-2 border border-border bg-card px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {loading && applications.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          Loading pipeline…
        </div>
      ) : error && applications.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <Briefcase className="w-12 h-12 text-red-400 opacity-50" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">Couldn’t load tracker</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">{error}</p>
          </div>
          <button
            onClick={fetchApplications}
            className="text-sm text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      ) : applications.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <LayoutGrid className="w-12 h-12 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">Pipeline is empty</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">
              Ingest a job to automatically add it to Wishlist. Applications will show up here as Kanban cards.
            </p>
          </div>
        </div>
      ) : (
        <>
          {error && (
            <div className="text-sm text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-md px-3 py-2 shrink-0">
              {error}
            </div>
          )}
          <div
            className="flex-1 overflow-x-auto overflow-y-hidden min-h-0"
            onDragLeave={() => setDragOverStage(null)}
          >
            <div className="flex gap-3 h-full pb-2">
              {STAGES.map(({ stage, accent }) => (
                <div
                  key={stage}
                  className="h-full"
                  onDragOver={(e) => handleDragOver(e, stage)}
                >
                  <KanbanColumn
                    stage={stage}
                    applications={byStage(stage)}
                    accent={accent}
                    onDragStart={handleDragStart}
                    onDragOver={(e) => handleDragOver(e, stage)}
                    onDrop={handleDrop}
                    isDropTarget={dragOverStage === stage}
                  />
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
