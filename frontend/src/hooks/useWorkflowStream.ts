import { useEffect } from 'react';
import { useWorkflowStore } from './useWorkflowStore';

export function useWorkflowStream(jobId: string) {
  const { setActiveNode, setNodeTelemetry, setWorkflowStatus, setFinalState, addEvent, reset } = useWorkflowStore();

  useEffect(() => {
    if (!jobId) return;

    reset();
    setWorkflowStatus('running');
    
    const eventSource = new EventSource(`http://localhost:8000/api/v1/workflows/${jobId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Save the raw event for the Timeline
        addEvent({
          ...data,
          timestamp: new Date().toISOString()
        });
        
        if (data.type === 'AGENT_STARTED') {
          setActiveNode(data.agent);
          setNodeTelemetry(data.agent, { status: 'running' });
        } else if (data.type === 'AGENT_SUCCESS') {
          if (data.payload) {
            setNodeTelemetry(data.agent, {
              status: 'success',
              latency_ms: data.payload.latency_ms,
              tokens: data.payload.tokens,
              cost: data.payload.cost,
              evidence: data.payload.evidence,
            });
          }
        } else if (data.type === 'COMPLETED') {
          if (data.final_state) {
            setFinalState(data.final_state);
          }
          setWorkflowStatus('completed');
          setActiveNode(null);
          eventSource.close();
        } else if (data.type === 'ERROR') {
          setWorkflowStatus('error');
          eventSource.close();
        }
      } catch (e) {
        console.error("Error parsing SSE data", e);
      }
    };

    eventSource.onerror = () => {
      setWorkflowStatus('error');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);
}
