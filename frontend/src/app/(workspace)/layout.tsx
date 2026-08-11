import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";
import { AssistantChat } from "@/components/ui/AssistantChat";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <WorkspaceLayout>
      {children}
      <AssistantChat />
    </WorkspaceLayout>
  );
}
