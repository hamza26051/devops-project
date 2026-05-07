import { Link } from "@tanstack/react-router";

export function Logo() {
  return (
    <a href="/" className="group flex items-center gap-3">
      <div className="relative">
        <div className="h-9 w-9 rounded-md bg-gradient-ember shadow-ember" />
        <div className="absolute inset-0 m-auto h-2.5 w-2.5 rounded-full bg-background" />
      </div>
      <div className="leading-none">
        <div className="font-display text-xl tracking-[0.18em] text-foreground">
          VERIDRIVE
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
          risk · intelligence
        </div>
      </div>
    </a>
  );
}
