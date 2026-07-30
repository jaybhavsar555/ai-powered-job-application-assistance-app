"use client";

import { useWorkflowStream } from '@/hooks/useWorkflowStream';
import { useWorkflowStore } from '@/hooks/useWorkflowStore';
import { Timeline } from '@/components/workflow/Timeline';
import { WorkflowCanvas } from '@/components/workflow/WorkflowCanvas';
import { useState } from 'react';

// Hardcoded for demo purposes.
const DEMO_JOB_ID = "00000000-0000-0000-0000-000000000000"; 

export default function DashboardPage() {
  const [jobId, setJobId] = useState<string>("");
  
  // Call the stream hook which connects when jobId is set
  useWorkflowStream(jobId);
  
  // Read from the global store
  const { workflowStatus } = useWorkflowStore();

  const startWorkflow = () => {
    setJobId(DEMO_JOB_ID); // Trigger SSE hook
  };

  return (
    <div className="flex-1 p-8 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">AI Operating System</h1>
        <button 
          onClick={startWorkflow}
          disabled={workflowStatus === 'running'}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50"
        >
          {workflowStatus === 'running' ? 'Agents Working...' : 'Simulate Application Flow'}
        </button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <WorkflowCanvas />
        </div>
        <div>
          <Timeline />
        </div>
      </div>
    </div>
  );
}
