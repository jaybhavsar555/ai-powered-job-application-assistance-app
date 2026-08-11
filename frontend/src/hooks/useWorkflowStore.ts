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

export interface WorkflowFinalState {
  job_id?: string;
  user_id?: string;
  cover_letter?: string | { content?: string };
  tailored_resume?: {
    summary?: string;
    tailored_bullets?: string[];
    added_keywords?: string[];
    // added for comparison UI
    text?: string;
    fileUrl?: string;
  };
  ats_score?: number;
  ats_recommendation?: string;
  missing_skills?: string[];
  company_research?: Record<string, unknown>;
  job_details?: Record<string, unknown>;
  requires_human_approval?: boolean;
  [key: string]: unknown;
}

export interface SkillImpact {
  skill: string;
  level: "high" | "medium" | "low";
  reason: string;
  jd_mentions?: number;
}

export interface SkillPresent {
  skill: string;
  confidence: "strong" | "partial";
  note?: string;
}

export interface NiceToHaveSkill {
  skill: string;
  reason: string;
}

export interface TailorState {
  step: 1 | 2 | 3;
  jdText: string;
  jobUrl: string;
  selectedBaseResume: string;
  proposedSkills: string[];
  approvedSkills: string[];
  // ATS scoring
  beforeAtsScore: number | null;
  afterAtsScore: number | null;
  rationale: string;
  skillImpacts: SkillImpact[];
  // Comprehensive analysis
  presentSkills: SkillPresent[];
  niceToHaveMissing: NiceToHaveSkill[];
  qualificationsMatch: string;
  // Iterative improvement
  previouslyAddedSkills: string[];
  iterativeMode: boolean;
  iterativeTailoredText: string;
}

interface WorkflowState {
  /** Currently executing agent (from SSE) */
  activeNode: string | null;
  /** Agent the developer clicked on the canvas */
  selectedNode: string | null;
  nodeTelemetry: Record<string, NodeTelemetry>;
  workflowStatus: 'idle' | 'running' | 'completed' | 'error';
  events: WorkflowEvent[];
  finalState: WorkflowFinalState | null;
  // Store original resume preview for comparison
  originalResumeData: { text: string; fileUrl?: string } | null;
  tailorState: TailorState;

  setActiveNode: (node: string | null) => void;
  setSelectedNode: (node: string | null) => void;
  setNodeTelemetry: (node: string, data: Partial<NodeTelemetry>) => void;
  setWorkflowStatus: (status: 'idle' | 'running' | 'completed' | 'error') => void;
  setFinalState: (state: WorkflowFinalState | null) => void;
  setOriginalResumeData: (data: { text: string; fileUrl?: string } | null) => void;
  setTailorState: (state: Partial<TailorState>) => void;
  addEvent: (event: WorkflowEvent) => void;
  reset: () => void;
}

const initialTailorState: TailorState = {
  step: 1,
  jdText: "",
  jobUrl: "",
  selectedBaseResume: "",
  proposedSkills: [],
  approvedSkills: [],
  beforeAtsScore: null,
  afterAtsScore: null,
  rationale: "",
  skillImpacts: [],
  presentSkills: [],
  niceToHaveMissing: [],
  qualificationsMatch: "",
  previouslyAddedSkills: [],
  iterativeMode: false,
  iterativeTailoredText: "",
};

export const useWorkflowStore = create<WorkflowState>((set) => ({
  activeNode: null,
  selectedNode: null,
  nodeTelemetry: {},
  workflowStatus: 'idle',
  events: [],
  finalState: null,
  originalResumeData: null,
  tailorState: initialTailorState,

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

  setOriginalResumeData: (data) => set({ originalResumeData: data }),

  setTailorState: (state) => set((s) => ({ tailorState: { ...s.tailorState, ...state } })),

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
      originalResumeData: null,
      tailorState: initialTailorState,
    })),
}));
