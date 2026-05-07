interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  accent?: boolean;
}

export function StatCard({ label, value, hint, accent }: StatCardProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-lg border p-5 transition ${
        accent
          ? "border-primary/40 bg-primary/5"
          : "border-border bg-card/40"
      } backdrop-blur-md hover:border-primary/40`}
    >
      <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-3 font-display text-4xl leading-none text-foreground">
        {value}
      </div>
      {hint && (
        <div className="mt-2 font-mono text-[11px] text-muted-foreground">
          {hint}
        </div>
      )}
      <div className="pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full bg-gradient-ember opacity-0 blur-2xl transition group-hover:opacity-30" />
    </div>
  );
}
