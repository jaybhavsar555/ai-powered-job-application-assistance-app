"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BrainCircuit,
  Database,
  Network,
  LineChart,
  FileText,
  Store,
  LogOut,
  LayoutDashboard,
  ToggleLeft,
  ToggleRight,
  Building2,
  Users,
  Send,
  ChevronDown,
  ClipboardCheck,
  Sparkles,
  HelpCircle,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useModeStore } from "@/store/modeStore";

type NavItem = { name: string; href: string; icon: typeof LayoutDashboard };

const simplePrimary: NavItem[] = [
  { name: "Inbox", href: "/inbox", icon: LayoutDashboard },
  { name: "Jobs", href: "/jobs", icon: Store },
  { name: "Apply", href: "/apply", icon: Sparkles },
  { name: "Resumes", href: "/resumes", icon: FileText },
  { name: "Tracker", href: "/tracker", icon: Network },
  { name: "Outreach", href: "/outreach", icon: Send },
  { name: "Approvals", href: "/approvals", icon: ClipboardCheck },
];

const simpleMore: NavItem[] = [
  { name: "Discovery", href: "/discovery", icon: Sparkles },
  { name: "Screening Q&A", href: "/screening-qa", icon: HelpCircle },
  { name: "Companies", href: "/companies", icon: Building2 },
  { name: "Recruiters", href: "/recruiters", icon: Users },
  { name: "Analytics", href: "/analytics", icon: LineChart },
  { name: "Vault", href: "/vault", icon: Database },
];

const advancedNavItems: NavItem[] = [
  { name: "Canvas", href: "/canvas", icon: BrainCircuit },
  { name: "Vault", href: "/vault", icon: Database },
  { name: "Screening Q&A", href: "/screening-qa", icon: HelpCircle },
  { name: "Approvals", href: "/approvals", icon: ClipboardCheck },
  { name: "Tracker", href: "/tracker", icon: Network },
  { name: "Analytics", href: "/analytics", icon: LineChart },
  { name: "Marketplace", href: "/marketplace", icon: Store },
];

function NavLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const isActive = pathname.startsWith(item.href);
  return (
    <Link
      href={item.href}
      className={`flex items-center justify-center lg:justify-start gap-3 px-3 py-2.5 rounded-md transition-colors ${
        isActive
          ? "bg-primary/10 text-primary font-medium"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      }`}
    >
      <item.icon className="h-5 w-5 shrink-0" />
      <span className="hidden lg:block text-sm">{item.name}</span>
    </Link>
  );
}

export function WorkspaceNav() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { mode, toggleMode } = useModeStore();
  const moreActive = simpleMore.some((item) => pathname.startsWith(item.href));
  const [moreOpen, setMoreOpen] = useState(moreActive);

  return (
    <nav className="w-16 lg:w-64 flex flex-col items-center lg:items-start bg-card border-r border-border py-4">
      <div className="px-4 mb-4 flex items-center justify-center lg:justify-start w-full">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
          OS
        </div>
        <span className="hidden lg:block ml-3 font-bold text-lg">Career OS</span>
      </div>

      <div className="px-4 w-full mb-6 hidden lg:flex justify-between items-center text-sm border-b border-border pb-4">
        <span className="text-muted-foreground font-medium">
          {mode === "simple" ? "Simple Mode" : "Advanced Mode"}
        </span>
        <button
          onClick={toggleMode}
          className="text-primary hover:text-primary/80 transition-colors"
          title={`Switch to ${mode === "simple" ? "Advanced" : "Simple"}`}
        >
          {mode === "simple" ? (
            <ToggleLeft className="w-6 h-6" />
          ) : (
            <ToggleRight className="w-6 h-6" />
          )}
        </button>
      </div>
      <div className="w-full mb-6 flex lg:hidden justify-center items-center pb-4 border-b border-border">
        <button
          onClick={toggleMode}
          className="text-primary hover:text-primary/80 transition-colors"
          title={`Switch to ${mode === "simple" ? "Advanced" : "Simple"}`}
        >
          {mode === "simple" ? (
            <ToggleLeft className="w-6 h-6" />
          ) : (
            <ToggleRight className="w-6 h-6" />
          )}
        </button>
      </div>

      <div className="flex flex-col gap-2 w-full px-2 flex-1 overflow-y-auto">
        {mode === "simple" ? (
          <>
            {simplePrimary.map((item) => (
              <NavLink key={item.href} item={item} pathname={pathname} />
            ))}
            <div className="pt-2 mt-1 border-t border-border">
              <button
                type="button"
                onClick={() => setMoreOpen((o) => !o)}
                className={`w-full flex items-center justify-center lg:justify-between gap-3 px-3 py-2.5 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground ${
                  moreActive ? "text-primary" : ""
                }`}
                title="More"
              >
                <span className="hidden lg:block text-sm font-medium">More</span>
                <ChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform ${moreOpen || moreActive ? "rotate-180" : ""}`}
                />
              </button>
              {(moreOpen || moreActive) && (
                <div className="flex flex-col gap-1 mt-1">
                  {simpleMore.map((item) => (
                    <NavLink key={item.href} item={item} pathname={pathname} />
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          advancedNavItems.map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} />
          ))
        )}
      </div>

      <div className="w-full px-2 pt-2 border-t border-border mt-2 space-y-2">
        <p
          className="hidden lg:block px-3 text-[11px] text-muted-foreground truncate"
          title={user?.email || ""}
        >
          {user?.email || "Signed out"}
          {user?.role ? ` · ${user.role}` : ""}
        </p>
        <Link
          href="/login"
          onClick={() => logout()}
          className="flex items-center justify-center lg:justify-start gap-3 px-3 py-2.5 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          <span className="hidden lg:block text-sm">Sign out</span>
        </Link>
      </div>
    </nav>
  );
}
