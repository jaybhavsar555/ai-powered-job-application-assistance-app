"use client";

import { useState, useEffect } from "react";
import { Database, Search, Plus } from "lucide-react";

interface WikiEntity {
  id: string;
  entity_type: string;
  title: string;
  content: any;
  created_at: string;
}

export default function VaultPage() {
  const [entities, setEntities] = useState<WikiEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // In a real app, this would use a proper fetch hook with auth headers
    const fetchEntities = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/knowledge/me', {
          headers: {
            'Authorization': 'Bearer placeholder-token'
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch knowledge graph');
        }
        
        const data = await response.json();
        setEntities(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchEntities();
  }, []);

  return (
    <div className="flex-1 p-8 space-y-6 overflow-y-auto">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Knowledge Graph Vault</h1>
        <button className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md font-medium text-sm hover:bg-primary/90 transition-colors">
          <Plus className="w-4 h-4" /> Add Entity
        </button>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input 
          type="text" 
          placeholder="Search extracted skills, companies, experiences..." 
          className="w-full pl-9 pr-4 py-2 rounded-md border border-border bg-card focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {loading ? (
        <div className="flex justify-center p-12 text-muted-foreground">Loading Knowledge Graph...</div>
      ) : error ? (
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4 text-red-400">
          <Database className="w-12 h-12 opacity-50" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">API Error</h3>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
      ) : entities.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <Database className="w-12 h-12 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">Vault is Empty</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">
              Your agents haven't extracted any entities yet. Start a workflow to populate your Knowledge Graph.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {entities.map(entity => (
            <div key={entity.id} className="border border-border bg-card rounded-lg p-4 space-y-2 hover:border-primary/50 transition-colors cursor-pointer">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary capitalize">
                  {entity.entity_type}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {new Date(entity.created_at).toLocaleDateString()}
                </span>
              </div>
              <h4 className="font-medium text-foreground">{entity.title}</h4>
              <p className="text-sm text-muted-foreground line-clamp-3">
                {JSON.stringify(entity.content).replace(/["{}]/g, ' ')}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
