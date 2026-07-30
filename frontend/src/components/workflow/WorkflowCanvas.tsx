"use client";

import React, { useEffect, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  NodeTypes,
  Node,
  NodeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useWorkflowStore } from '@/hooks/useWorkflowStore';
import { CustomWorkflowNode } from '@/components/ui/CustomWorkflowNode';

type AgentNodeData = {
  label: string;
  agentId: string;
  status: 'idle' | 'running' | 'success' | 'error';
  selected?: boolean;
  cost?: number;
  tokens?: number;
  latency_ms?: number;
};

const initialNodes: Node<AgentNodeData>[] = [
  { id: '1', position: { x: 250, y: 50 }, data: { label: 'Job Intake Agent', agentId: 'job_intake_agent', status: 'idle' }, type: 'custom' },
  { id: '2', position: { x: 250, y: 150 }, data: { label: 'Company Research Agent', agentId: 'company_research_agent', status: 'idle' }, type: 'custom' },
  { id: '3', position: { x: 250, y: 250 }, data: { label: 'ATS Analyzer', agentId: 'ats_analyzer', status: 'idle' }, type: 'custom' },
  { id: '4', position: { x: 250, y: 350 }, data: { label: 'Resume Optimizer', agentId: 'resume_optimizer', status: 'idle' }, type: 'custom' },
  { id: '5', position: { x: 250, y: 450 }, data: { label: 'Cover Letter Agent', agentId: 'cover_letter_agent', status: 'idle' }, type: 'custom' },
  { id: '6', position: { x: 250, y: 550 }, data: { label: 'Human Approval', agentId: 'human_approval', status: 'idle' }, type: 'custom' },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: true },
  { id: 'e4-5', source: '4', target: '5', animated: true },
  { id: 'e5-6', source: '5', target: '6', animated: true },
];

function norm(s: string) {
  return s.toLowerCase().replace(/[\s_]+/g, '');
}

export function WorkflowCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { nodeTelemetry, activeNode, selectedNode, setSelectedNode } = useWorkflowStore();

  const nodeTypes = useMemo<NodeTypes>(() => ({ custom: CustomWorkflowNode as never }), []);

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      const agentId = (node.data as AgentNodeData)?.agentId;
      if (agentId) setSelectedNode(agentId);
    },
    [setSelectedNode]
  );

  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        const data = node.data as AgentNodeData;
        const agentId = data.agentId;
        const labelKey = norm(data.label);
        const telemetryEntry = Object.entries(nodeTelemetry).find(([key]) => {
          const k = norm(key);
          return k === norm(agentId) || k === labelKey || k.includes(labelKey) || labelKey.includes(k);
        });
        const telemetry = telemetryEntry?.[1];
        const activeNorm = activeNode ? norm(activeNode) : '';
        const agentNorm = norm(agentId);

        let newStatus: AgentNodeData['status'] = 'idle';
        if (
          activeNorm &&
          (activeNorm === agentNorm ||
            activeNorm === labelKey ||
            activeNorm.includes(agentNorm) ||
            agentNorm.includes(activeNorm))
        ) {
          newStatus = 'running';
        } else if (telemetry?.status === 'success') {
          newStatus = 'success';
        } else if (telemetry?.status === 'error') {
          newStatus = 'error';
        }

        return {
          ...node,
          selected: selectedNode === agentId,
          data: {
            ...data,
            status: newStatus,
            selected: selectedNode === agentId,
            cost: telemetry?.cost,
            tokens: telemetry?.tokens,
            latency_ms: telemetry?.latency_ms,
          },
        };
      })
    );
  }, [nodeTelemetry, activeNode, selectedNode, setNodes]);

  return (
    <div className="w-full h-full min-h-[420px] rounded-xl bg-card overflow-hidden border border-border relative group">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={() => setSelectedNode(null)}
        fitView
        colorMode="dark"
        minZoom={0.35}
        maxZoom={1.75}
        proOptions={{ hideAttribution: true }}
      >
        <Controls
          showInteractive
          className="!shadow-lg !border !border-border !rounded-lg !overflow-hidden"
        />
        <MiniMap
          pannable
          zoomable
          nodeStrokeWidth={2}
          className="!bg-muted/80 !border !border-border !rounded-lg !shadow-md opacity-80 hover:opacity-100 transition-opacity"
          maskColor="rgba(15, 15, 20, 0.65)"
        />
        <Background gap={18} size={1} color="#334155" />
      </ReactFlow>
      <p className="pointer-events-none absolute left-3 bottom-3 text-[10px] text-muted-foreground bg-card/80 px-2 py-1 rounded border border-border/60">
        Click an agent to inspect / edit its prompt
      </p>
    </div>
  );
}
