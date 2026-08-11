"use client";

import { useEffect, useState } from "react";
import { Users, Search, Copy, Linkedin, Mail } from "lucide-react";
import { useAuthStore } from "@/store/auth";

interface Recruiter {
  id: string;
  name: string;
  company_id: string;
  linkedin_url: string | null;
  email: string | null;
}

export default function RecruitersPage() {
  const [recruiters, setRecruiters] = useState<Recruiter[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    const fetchRecruiters = async () => {
      try {
        setLoading(true);
        const res = await fetch("/api/v1/recruiters/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setRecruiters(data);
        }
      } catch (err) {
        console.error("Failed to fetch recruiters", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) fetchRecruiters();
  }, [token]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Recruiters</h1>
          <p className="text-muted-foreground text-lg">Hiring managers and recruiters found by the AI.</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            className="w-full rounded-md border border-input bg-transparent pl-9 pr-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="Search recruiters..."
          />
        </div>
      </div>

      <div className="rounded-xl border bg-card overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted/50 border-b text-muted-foreground font-medium">
            <tr>
              <th className="px-6 py-4">Name</th>
              <th className="px-6 py-4">Contact</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center text-muted-foreground">
                  <div className="animate-pulse flex space-x-4 justify-center">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                  </div>
                </td>
              </tr>
            ) : recruiters.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center">
                  <Users className="mx-auto h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                  <h3 className="text-lg font-medium">No Recruiters Found</h3>
                  <p className="text-muted-foreground mt-1">Run the Recruiter Discovery Agent to find hiring managers.</p>
                </td>
              </tr>
            ) : (
              recruiters.map((r) => (
                <tr key={r.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4 font-medium text-foreground">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                        {r.name.charAt(0)}
                      </div>
                      {r.name}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col gap-1">
                      {r.email && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Mail className="h-4 w-4" />
                          <span>{r.email}</span>
                        </div>
                      )}
                      {r.linkedin_url && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Linkedin className="h-4 w-4" />
                          <a href={r.linkedin_url} target="_blank" rel="noreferrer" className="hover:text-primary hover:underline truncate max-w-[200px]">
                            {r.linkedin_url}
                          </a>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {r.email && (
                        <button 
                          onClick={() => copyToClipboard(r.email!)}
                          className="px-3 py-1.5 text-xs font-medium border rounded-md hover:bg-muted transition-colors"
                          title="Copy Email"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                      )}
                      {r.linkedin_url && (
                        <button 
                          onClick={() => copyToClipboard(r.linkedin_url!)}
                          className="px-3 py-1.5 text-xs font-medium border rounded-md hover:bg-muted transition-colors"
                          title="Copy LinkedIn URL"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
