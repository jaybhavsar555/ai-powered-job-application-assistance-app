"use client";

import Link from "next/link";
import { Building2, GripVertical, ExternalLink, FileStack, Loader2, Workflow, Presentation } from "lucide-react";

export type ApplicationStage =
  | "Wishlist"
  | "Researching"
  | "Ready"
  | "Needs input"
  | "Failed"
  | "Reapply"
  | "Applied"
  | "Shortlisted"
  | "Interview"
  | "Rejected";

export interface JobSummary {
  id: string;
  role_title: string;
  url?: string | null;
  status: string;
  company_name?: string | null;
  required_skills: string[];
}

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  stage: ApplicationStage | string;
  workflow_state: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  job?: JobSummary | null;
}

interface ApplicationCardProps {
  application: Application;
  onDragStart: (e: React.DragEvent, applicationId: string) => void;
  onGeneratePackage?: (applicationId: string) => void;
  packagingId?: string | null;
}

export function ApplicationCard({
  application,
  onDragStart,
  onGeneratePackage,
  packagingId,
}: ApplicationCardProps) {
  const job = application.job;
  const skills = job?.required_skills?.slice(0, 3) ?? [];
  const busy = packagingId === application.id;
  const pkg = application.workflow_state?.apply_package as
    | { folder?: string; role_family?: string }
    | undefined;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, application.id)}
      className="group border border-border bg-background rounded-lg p-3 space-y-2 cursor-grab active:cursor-grabbing hover:border-primary/40 hover:bg-muted/20 transition-all shadow-sm"
    >
      <div className="flex items-start gap-2">
        <GripVertical className="h-4 w-4 mt-0.5 text-muted-foreground/50 group-hover:text-muted-foreground shrink-0" />
        <div className="min-w-0 flex-1 space-y-1.5">
          <h4 className="font-medium text-sm text-foreground leading-snug line-clamp-2">
            {job?.role_title || "Untitled Role"}
          </h4>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Building2 className="h-3 w-3 shrink-0" />
            <span className="truncate">{job?.company_name || "Unknown company"}</span>
          </div>
        </div>
        {job?.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-muted-foreground hover:text-primary transition-colors shrink-0"
            title="Open job posting"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1 pl-6">
          {skills.map((skill) => (
            <span
              key={skill}
              className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border"
            >
              {skill}
            </span>
          ))}
        </div>
      )}

      <div className="pl-6 flex items-center justify-between gap-2 flex-wrap">
        <span className="text-[10px] text-muted-foreground/70 truncate min-w-0">
          {pkg?.folder
            ? `Package ready${pkg.role_family ? ` · ${pkg.role_family}` : ""}`
            : `Updated ${new Date(application.updated_at).toLocaleDateString()}`}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          <Link
            href={`/canvas?job_id=${encodeURIComponent(application.job_id)}`}
            title="Run agent pipeline for this job on Canvas"
            onClick={(e) => e.stopPropagation()}
            draggable={false}
            className="inline-flex items-center gap-1 text-[10px] px-1.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <Workflow className="h-3 w-3" />
            Canvas
          </Link>
          {onGeneratePackage && (
            <button
              type="button"
              title="Write tailored resume + cover letter (DOCX/PDF) into company folder"
              disabled={busy}
              onClick={(e) => {
                e.stopPropagation();
                onGeneratePackage(application.id);
              }}
              className="inline-flex items-center gap-1 text-[10px] px-1.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
            >
              {busy ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <FileStack className="h-3 w-3" />
              )}
              {busy ? "Packaging…" : "Package"}
            </button>
          )}
          {(application.stage === "Interview" || application.stage === "Shortlisted") && (
            <Link
              href={`/interviews/${application.id}`}
              title="View Interview Prep Guide & Mock Interview Simulator"
              onClick={(e) => e.stopPropagation()}
              draggable={false}
              className="inline-flex items-center gap-1 text-[10px] px-1.5 py-1 rounded border border-primary/50 text-primary hover:bg-primary/10 transition-colors bg-primary/5"
            >
              <Presentation className="h-3 w-3" />
              Prep Guide
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
