"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrainCircuit, Database, Network, LineChart, FileText } from "lucide-react";

export function WorkspaceNav() {
  const pathname = usePathname();

  const navItems = [
    { name: "Canvas", href: "/canvas", icon: BrainCircuit },
    { name: "Vault", href: "/vault", icon: Database },
    { name: "Approvals", href: "/approvals", icon: FileText },
    { name: "Tracker", href: "/tracker", icon: Network },
    { name: "Analytics", href: "/analytics", icon: LineChart },
  ];

  return (
    <nav className="w-16 lg:w-64 flex flex-col items-center lg:items-start bg-card border-r border-border py-4">
      <div className="px-4 mb-8 flex items-center justify-center lg:justify-start w-full">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
          OS
        </div>
        <span className="hidden lg:block ml-3 font-bold text-lg">Career OS</span>
      </div>

      <div className="flex flex-col gap-2 w-full px-2">
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
    </nav>
  );
}
