"use client";

import { useWorkflowStore } from '@/hooks/useWorkflowStore';
import { ApprovalCard } from '@/components/ui/ApprovalCard';
import { CheckCircle2, AlertCircle } from 'lucide-react';

export default function ApprovalsPage() {
  const { finalState, workflowStatus } = useWorkflowStore();

  if (workflowStatus !== 'completed' || !finalState) {
    return (
      <div className="flex-1 p-8 space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">Human-in-the-Loop Approvals</h1>
        </div>
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">No Pending Approvals</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">
              Start a new workflow on the Canvas. Any generated resumes or cover letters that require human review will appear here.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const coverLetter = finalState.cover_letter || "";
  const resumeUpdates = finalState.tailored_resume || {};
  
  return (
    <div className="flex-1 p-8 space-y-6 overflow-y-auto">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Pending Approvals</h1>
        <div className="flex items-center gap-2 text-sm text-amber-500 bg-amber-500/10 px-3 py-1.5 rounded-full border border-amber-500/20 font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          Requires Human Review
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 max-w-4xl">
        {/* Cover Letter Approval */}
        {coverLetter && (
          <ApprovalCard 
            title="Generated Cover Letter"
            originalText="[No existing cover letter provided for comparison. Showing purely newly generated text.]"
            proposedText={coverLetter}
            evidence="The AI used hooks related to the user's background in Python and Kubernetes, mapping directly to the Job Description's requirements."
            onApprove={() => alert("Cover Letter Approved!")}
            onReject={() => alert("Cover Letter Rejected!")}
          />
        )}
        
        {/* Resume Updates Approval */}
        {resumeUpdates.added_keywords && (
          <ApprovalCard 
            title="Resume Optimization"
            originalText="[Missing ATS Keywords]"
            proposedText={`Added Keywords: ${resumeUpdates.added_keywords.join(', ')}`}
            evidence="The ATS Analyzer detected missing critical keywords. The Resume Optimizer successfully injected these keywords into the experience section while maintaining factual accuracy."
            onApprove={() => alert("Resume Changes Approved!")}
            onReject={() => alert("Resume Changes Rejected!")}
          />
        )}
      </div>
    </div>
  );
}
