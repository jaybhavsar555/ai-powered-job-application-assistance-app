"use client";

import { useEffect, useState } from "react";
import { Building2, Search, Activity } from "lucide-react";
import { useAuthStore } from "@/store/auth";

interface Company {
  id: string;
  name: string;
  research_data: Record<string, unknown> | null;
  created_at: string;
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        setLoading(true);
        const res = await fetch("/api/v1/companies/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setCompanies(data);
        }
      } catch (err) {
        console.error("Failed to fetch companies", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) fetchCompanies();
  }, [token]);

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Companies</h1>
          <p className="text-muted-foreground text-lg">Research data gathered by the AI.</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            className="w-full rounded-md border border-input bg-transparent pl-9 pr-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="Search companies..."
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-40 rounded-xl bg-muted animate-pulse"></div>
          ))}
        </div>
      ) : companies.length === 0 ? (
        <div className="text-center py-12 border rounded-xl border-dashed">
          <Building2 className="mx-auto h-12 w-12 text-muted-foreground mb-4 opacity-50" />
          <h3 className="text-lg font-medium">No Companies Found</h3>
          <p className="text-muted-foreground mt-1">Companies will appear here when the AI researches a job application.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {companies.map((company) => (
            <div key={company.id} className="rounded-xl border bg-card p-6 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="p-2 bg-primary/10 rounded-lg text-primary">
                    <Building2 className="h-6 w-6" />
                  </div>
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-md flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    Tracked
                  </span>
                </div>
                <h3 className="font-semibold text-xl mb-2 line-clamp-1">{company.name}</h3>
                
                {company.research_data && Object.keys(company.research_data).length > 0 ? (
                  <div className="text-sm text-muted-foreground mt-4 space-y-2">
                    <p className="font-medium text-foreground">AI Research Insights:</p>
                    <pre className="bg-muted p-3 rounded-md overflow-x-auto text-xs">
                      {JSON.stringify(company.research_data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic mt-4">
                    Pending full AI research...
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
