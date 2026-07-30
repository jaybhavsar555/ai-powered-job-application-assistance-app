export default function SettingsPage() {
  return (
    <div className="flex-1 p-8 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
      </div>
      <div className="rounded-xl border bg-card p-8 text-center text-muted-foreground">
        API Keys (OpenAI, Playwright) and user settings will be configured here.
      </div>
    </div>
  );
}
