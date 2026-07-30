"use client";

import React, { useEffect, useMemo } from 'react';
import { ReactFlow, MiniMap, Controls, Background, useNodesState, useEdgesState, NodeTypes } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useWorkflowStore } from '@/hooks/useWorkflowStore';
import { CustomWorkflowNode } from '@/components/ui/CustomWorkflowNode';

const initialNodes = [
  { id: '1', position: { x: 250, y: 50 }, data: { label: 'Job Intake Agent', status: 'idle' }, type: 'custom' },
  { id: '2', position: { x: 250, y: 150 }, data: { label: 'Company Research Agent', status: 'idle' }, type: 'custom' },
  { id: '3', position: { x: 250, y: 250 }, data: { label: 'ATS Analyzer', status: 'idle' }, type: 'custom' },
  { id: '4', position: { x: 250, y: 350 }, data: { label: 'Resume Optimizer', status: 'idle' }, type: 'custom' },
  { id: '5', position: { x: 250, y: 450 }, data: { label: 'Cover Letter Agent', status: 'idle' }, type: 'custom' },
  { id: '6', position: { x: 250, y: 550 }, data: { label: 'Human Approval', status: 'idle' }, type: 'custom' },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: true },
  { id: 'e4-5', source: '4', target: '5', animated: true },
  { id: 'e5-6', source: '5', target: '6', animated: true },
];

export function WorkflowCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { nodeTelemetry, activeNode } = useWorkflowStore();
  
  const nodeTypes = useMemo<NodeTypes>(() => ({ custom: CustomWorkflowNode as any }), []);

  // Update node status dynamically based on live events from the backend!
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        // Strip spaces from labels if our backend agent names don't have spaces, 
        // e.g. "Job Intake Agent" -> "JobIntakeAgent"
        const backendAgentName = node.data.label.replace(/\s+/g, '');
        const telemetry = nodeTelemetry[backendAgentName] || nodeTelemetry[node.data.label];

        let newStatus = 'idle';
        if (activeNode === backendAgentName || activeNode === node.data.label) {
          newStatus = 'running';
        } else if (telemetry?.status === 'success') {
          newStatus = 'success';
        }

        return { 
          ...node, 
          data: { 
            ...node.data, 
            status: newStatus,
            cost: telemetry?.cost,
            tokens: telemetry?.tokens,
            latency_ms: telemetry?.latency_ms
          } 
        };
      })
    );
  }, [nodeTelemetry, activeNode, setNodes]);

  return (
    <div className="w-full h-full min-h-[600px] rounded-xl bg-card overflow-hidden border border-border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        colorMode="dark"
      >
        <Controls />
        <Background gap={16} size={1} color="#334155" />
      </ReactFlow>
    </div>
  );
}
