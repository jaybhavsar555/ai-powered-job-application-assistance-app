import { create } from 'zustand';

export interface NodeTelemetry {
  latency_ms?: number;
  tokens?: number;
  cost?: number;
  evidence?: unknown;
  status: 'idle' | 'running' | 'success' | 'error';
}

export type WorkflowEvent = {
  type?: string;
  node?: string;
  agent?: string;
  timestamp?: string;
  message?: string;
  error?: string;
  latency_ms?: number;
  tokens?: number;
  cost?: number;
  evidence?: unknown;
  payload?: Record<string, unknown>;
  final_state?: WorkflowFinalState;
  [key: string]: unknown;
};

export type WorkflowFinalState = {
  job_id?: string;
  user_id?: string;
  cover_letter?: string | { content?: string };
  tailored_resume?: {
    summary?: string;
    tailored_bullets?: string[];
    added_keywords?: string[];
  };
  ats_score?: number;
  missing_skills?: string[];
  company_research?: Record<string, unknown>;
  job_details?: Record<string, unknown>;
  requires_human_approval?: boolean;
  [key: string]: unknown;
};

interface WorkflowState {
  /** Currently executing agent (from SSE) */
  activeNode: string | null;
  /** Agent the developer clicked on the canvas */
  selectedNode: string | null;
  nodeTelemetry: Record<string, NodeTelemetry>;
  workflowStatus: 'idle' | 'running' | 'completed' | 'error';
  events: WorkflowEvent[];
  finalState: WorkflowFinalState | null;

  setActiveNode: (node: string | null) => void;
  setSelectedNode: (node: string | null) => void;
  setNodeTelemetry: (node: string, data: Partial<NodeTelemetry>) => void;
  setWorkflowStatus: (status: 'idle' | 'running' | 'completed' | 'error') => void;
  setFinalState: (state: WorkflowFinalState | null) => void;
  addEvent: (event: WorkflowEvent) => void;
  reset: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  activeNode: null,
  selectedNode: null,
  nodeTelemetry: {},
  workflowStatus: 'idle',
  events: [],
  finalState: null,

  setActiveNode: (node) => set({ activeNode: node }),
  setSelectedNode: (node) => set({ selectedNode: node }),

  setNodeTelemetry: (node, data) =>
    set((state) => ({
      nodeTelemetry: {
        ...state.nodeTelemetry,
        [node]: {
          ...state.nodeTelemetry[node],
          status: data.status ?? state.nodeTelemetry[node]?.status ?? 'idle',
          ...data,
        },
      },
    })),

  setWorkflowStatus: (status) => set({ workflowStatus: status }),

  setFinalState: (state) => set({ finalState: state }),

  addEvent: (event) => set((state) => ({ events: [...state.events, event] })),

  reset: () =>
    set((state) => ({
      activeNode: null,
      // Keep developer selection across re-runs
      selectedNode: state.selectedNode,
      nodeTelemetry: {},
      workflowStatus: 'idle',
      events: [],
      finalState: null,
    })),
}));
