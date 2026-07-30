"use client";

import { Application, ApplicationCard, ApplicationStage } from "./ApplicationCard";

interface KanbanColumnProps {
  stage: ApplicationStage;
  applications: Application[];
  accent: string;
  onDragStart: (e: React.DragEvent, applicationId: string) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent, stage: ApplicationStage) => void;
  isDropTarget: boolean;
  onGeneratePackage?: (applicationId: string) => void;
  packagingId?: string | null;
}

export function KanbanColumn({
  stage,
  applications,
  accent,
  onDragStart,
  onDragOver,
  onDrop,
  isDropTarget,
  onGeneratePackage,
  packagingId,
}: KanbanColumnProps) {
  return (
    <div
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, stage)}
      className={`flex flex-col min-w-[260px] w-[260px] max-h-full rounded-xl border transition-colors ${
        isDropTarget
          ? "border-primary/50 bg-primary/5"
          : "border-border bg-card/50"
      }`}
    >
      <div className="flex items-center justify-between px-3 py-3 border-b border-border sticky top-0 bg-card/80 backdrop-blur-sm rounded-t-xl z-10">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${accent}`} />
          <h3 className="text-sm font-semibold text-foreground">{stage}</h3>
        </div>
        <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-md tabular-nums">
          {applications.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[120px]">
        {applications.length === 0 ? (
          <div className="flex items-center justify-center h-24 text-xs text-muted-foreground border border-dashed border-border rounded-lg">
            Drop here
          </div>
        ) : (
          applications.map((app) => (
            <ApplicationCard
              key={app.id}
              application={app}
              onDragStart={onDragStart}
              onGeneratePackage={onGeneratePackage}
              packagingId={packagingId}
            />
          ))
        )}
      </div>
    </div>
  );
}
