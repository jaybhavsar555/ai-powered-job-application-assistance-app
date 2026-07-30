"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrainCircuit, Database, Network, LineChart, FileText, Store, LogOut } from "lucide-react";
import { useAuthStore } from "@/store/auth";

export function WorkspaceNav() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const navItems = [
    { name: "Canvas", href: "/canvas", icon: BrainCircuit },
    { name: "Vault", href: "/vault", icon: Database },
    { name: "Approvals", href: "/approvals", icon: FileText },
    { name: "Tracker", href: "/tracker", icon: Network },
    { name: "Analytics", href: "/analytics", icon: LineChart },
    { name: "Marketplace", href: "/marketplace", icon: Store },
  ];

  return (
    <nav className="w-16 lg:w-64 flex flex-col items-center lg:items-start bg-card border-r border-border py-4">
      <div className="px-4 mb-8 flex items-center justify-center lg:justify-start w-full">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
          OS
        </div>
        <span className="hidden lg:block ml-3 font-bold text-lg">Career OS</span>
      </div>

      <div className="flex flex-col gap-2 w-full px-2 flex-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-center lg:justify-start gap-3 px-3 py-2.5 rounded-md transition-colors ${
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <item.icon className="h-5 w-5" />
              <span className="hidden lg:block text-sm">{item.name}</span>
            </Link>
          );
        })}
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
          <LogOut className="h-5 w-5" />
          <span className="hidden lg:block text-sm">Sign out</span>
        </Link>
      </div>
    </nav>
  );
}
