import { create } from 'zustand';

export interface NodeTelemetry {
  latency_ms?: number;
  tokens?: number;
  cost?: number;
  evidence?: any;
  status: 'idle' | 'running' | 'success' | 'error';
}

interface WorkflowState {
  activeNode: string | null;
  nodeTelemetry: Record<string, NodeTelemetry>;
  workflowStatus: 'idle' | 'running' | 'completed' | 'error';
  events: any[];
  finalState: any | null;
  
  setActiveNode: (node: string | null) => void;
  setNodeTelemetry: (node: string, data: Partial<NodeTelemetry>) => void;
  setWorkflowStatus: (status: 'idle' | 'running' | 'completed' | 'error') => void;
  setFinalState: (state: any) => void;
  addEvent: (event: any) => void;
  reset: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  activeNode: null,
  nodeTelemetry: {},
  workflowStatus: 'idle',
  events: [],

  setActiveNode: (node) => set({ activeNode: node }),
  
  setNodeTelemetry: (node, data) => set((state) => ({
    nodeTelemetry: {
      ...state.nodeTelemetry,
      [node]: {
        ...state.nodeTelemetry[node],
        ...data,
      }
    }
  })),

  setWorkflowStatus: (status) => set({ workflowStatus: status }),

  setFinalState: (state) => set({ finalState: state }),

  addEvent: (event) => set((state) => ({ events: [...state.events, event] })),

  reset: () => set({
    activeNode: null,
    nodeTelemetry: {},
    workflowStatus: 'idle',
    events: [],
    finalState: null,
  })
}));
