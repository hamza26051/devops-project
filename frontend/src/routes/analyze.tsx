import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { CarSlideshow } from "@/components/CarSlideshow";
import { SiteHeader } from "@/components/SiteHeader";

export const Route = createFileRoute("/analyze")({
  head: () => ({
    meta: [
      { title: "Analyzing Profile — VeriDrive" },
      { name: "description", content: "AI is analyzing the customer's social signals." },
    ],
  }),
  component: AnalyzePage,
});

const MASTODON_STAGES = [
  "Authenticating with Mastodon",
  "Fetching profile signals",
  "Computing engagement metrics",
  "Running Risk Engine v3",
  "Generating decision rationale",
];

const MANUAL_STAGES = [
  "Ingesting manual entries",
  "Preprocessing content",
  "Running Risk Engine v3",
  "Aggregating signals",
  "Generating decision rationale",
];

function AnalyzePage() {
  const navigate = useNavigate();
  const [stage, setStage] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isManual, setIsManual] = useState(false);

  const STAGES = isManual ? MANUAL_STAGES : MASTODON_STAGES;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setIsManual(params.get("mode") === "manual");
    const resultId = params.get("id");

    const total = 4200;
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / total);
      setProgress(p);
      setStage(Math.min(STAGES.length - 1, Math.floor(p * STAGES.length)));
      if (p < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        // Navigate to result with the ID
        navigate({ 
          to: "/result", 
          search: resultId ? { id: resultId } : undefined 
        });
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [navigate]);

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SiteHeader />
      <CarSlideshow intensity="soft" />

      <div className="relative mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6 text-center">
        {/* Radar */}
        <div className="relative mb-12 h-56 w-56">
          <div className="absolute inset-0 rounded-full border border-primary/30" />
          <div className="absolute inset-4 rounded-full border border-primary/20" />
          <div className="absolute inset-10 rounded-full border border-primary/10" />
          <div className="absolute inset-0 m-auto h-3 w-3 animate-pulse-ring rounded-full bg-ember shadow-ember" />
          <div
            className="absolute inset-0 origin-center animate-spin-slow"
            style={{
              background:
                "conic-gradient(from 0deg, transparent 0deg, oklch(0.68 0.19 38 / 0.5) 30deg, transparent 60deg)",
              borderRadius: "50%",
              maskImage: "radial-gradient(circle, black 60%, transparent 62%)",
            }}
          />
          <div className="absolute inset-0 overflow-hidden rounded-full">
            <div
              className="absolute inset-x-0 h-px animate-scan bg-ember/60"
              style={{ boxShadow: "0 0 20px var(--ember)" }}
            />
          </div>
        </div>

        <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">
          Analysis in progress
        </div>
        <h1 className="mt-3 font-display text-6xl leading-none md:text-7xl">
          Reading the signals
        </h1>
        <p className="mt-4 max-w-md text-sm text-muted-foreground">
          We are scanning public activity, engagement patterns, and tenure to
          score risk.
        </p>

        {/* Progress */}
        <div className="mt-12 w-full max-w-xl">
          <div className="mb-3 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
            <span>{STAGES[stage]}</span>
            <span className="text-ember">{Math.floor(progress * 100)}%</span>
          </div>
          <div className="relative h-1 overflow-hidden rounded-full bg-border">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-ember"
              style={{ width: `${progress * 100}%`, boxShadow: "var(--shadow-ember)" }}
            />
          </div>
          <ul className="mt-6 space-y-2 text-left">
            {STAGES.map((s, idx) => {
              const done = idx < stage;
              const active = idx === stage;
              return (
                <li
                  key={s}
                  className={`flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.25em] transition ${
                    done
                      ? "text-success"
                      : active
                      ? "text-foreground"
                      : "text-muted-foreground/50"
                  }`}
                  style={{ color: done ? "var(--success)" : undefined }}
                >
                  <span
                    className={`flex h-4 w-4 items-center justify-center rounded-full border ${
                      done
                        ? "border-transparent bg-[color:var(--success)] text-background"
                        : active
                        ? "border-ember"
                        : "border-border"
                    }`}
                  >
                    {done ? "✓" : active ? <span className="h-1.5 w-1.5 rounded-full bg-ember" /> : ""}
                  </span>
                  {s}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
