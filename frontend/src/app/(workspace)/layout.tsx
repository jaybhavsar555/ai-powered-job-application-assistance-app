import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <WorkspaceLayout>{children}</WorkspaceLayout>;
}
