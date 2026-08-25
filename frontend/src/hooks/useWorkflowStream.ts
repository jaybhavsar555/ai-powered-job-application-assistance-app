import { useEffect } from 'react';
import { useWorkflowStore, type WorkflowEvent } from './useWorkflowStore';
import { useAuthStore } from '@/store/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

function agentKey(data: { node?: string; agent?: string }) {
  return data.node || data.agent || 'unknown';
}

export function useWorkflowStream(jobId: string, resume = false, nonce = 0) {
  const { setActiveNode, setNodeTelemetry, setWorkflowStatus, setFinalState, addEvent, reset } =
    useWorkflowStore();

  useEffect(() => {
    if (!jobId) return;

    const token = useAuthStore.getState().token;
    if (!token) {
      addEvent({
        type: 'ERROR',
        node: 'System',
        timestamp: new Date().toISOString(),
        error: 'Not authenticated — sign in or wait for demo login, then retry.',
      });
      setWorkflowStatus('error');
      return;
    }

    reset();
    setWorkflowStatus('running');
    addEvent({
      type: 'SYSTEM',
      node: 'System',
      timestamp: new Date().toISOString(),
      message: resume
        ? `Resuming workflow checkpoint for job ${jobId}…`
        : `Initializing workflow stream for job ${jobId}…`,
    });

    const url =
      `${API_BASE}/workflows/${jobId}/stream?token=${encodeURIComponent(token)}` +
      (resume ? '&resume=true' : '');
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WorkflowEvent;
        const name = agentKey(data);

        let enriched: WorkflowEvent = {
          ...data,
          node: name,
          timestamp: new Date().toISOString(),
        };

        if (data.type === 'AGENT_ERROR') {
          const errMsg =
            (typeof data.error === 'string' && data.error) ||
            (typeof data.message === 'string' && data.message) ||
            ((data.payload as Record<string, unknown> | undefined)?.error as string) ||
            'Agent failed — check API logs (LLM/scrape may be missing).';
          enriched = { ...enriched, error: errMsg, message: errMsg };
        }

        addEvent(enriched);

        if (data.type === 'AGENT_STARTED') {
          setActiveNode(name);
          setNodeTelemetry(name, { status: 'running' });
        } else if (data.type === 'AGENT_SUCCESS') {
          const payload = (data.payload || {}) as Record<string, unknown>;
          setNodeTelemetry(name, {
            status: 'success',
            latency_ms: (data.latency_ms ?? payload.latency_ms) as number | undefined,
            tokens: (data.tokens ?? payload.tokens) as number | undefined,
            cost: (data.cost ?? payload.cost) as number | undefined,
            evidence: data.evidence ?? payload.evidence,
          });
        } else if (data.type === 'AGENT_ERROR') {
          setNodeTelemetry(name, { status: 'error' });
          setWorkflowStatus('error');
        } else if (data.type === 'COMPLETED') {
          if (data.final_state) {
            setFinalState(data.final_state);
          }
          setWorkflowStatus('completed');
          setActiveNode(null);
          eventSource.close();
        } else if (data.type === 'ERROR') {
          setWorkflowStatus('error');
          setActiveNode(null);
          eventSource.close();
        }
      } catch (e) {
        console.error('Error parsing SSE data', e);
      }
    };

    eventSource.onerror = () => {
      // EventSource hides status codes; common causes: 401 (bad/expired JWT) or API down
      const ready = eventSource.readyState;
      addEvent({
        type: 'ERROR',
        node: 'System',
        timestamp: new Date().toISOString(),
        error:
          ready === EventSource.CLOSED
            ? `SSE closed (${API_BASE}). Check Docker API (port 8001), valid login token, and that a real Tracker job is selected (not only demo).`
            : `SSE connection failed (${API_BASE}). Is Docker API up on :8001?`,
      });
      setWorkflowStatus('error');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId, resume, nonce, addEvent, reset, setActiveNode, setFinalState, setNodeTelemetry, setWorkflowStatus]);
}
