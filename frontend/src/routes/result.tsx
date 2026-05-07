import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useRef } from "react";
import { CarSlideshow } from "@/components/CarSlideshow";
import { SiteHeader } from "@/components/SiteHeader";
import { RiskGauge } from "@/components/RiskGauge";
import { StatCard } from "@/components/StatCard";

export const Route = createFileRoute("/result")({
  head: () => ({
    meta: [
      { title: "Decision — VeriDrive" },
      { name: "description", content: "Risk score and decision for the analyzed profile." },
    ],
  }),
  component: ResultPage,
});

function ResultPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  const handleDownloadPDF = async () => {
    console.log("Download PDF triggered via jsPDF Text Generator");
    
    const { jsPDF } = typeof window !== "undefined" ? (window as any).jspdf || {} : {};
    if (!jsPDF) {
        console.error("jsPDF library not loaded");
        if (typeof window !== "undefined") alert("PDF Engine loading. Please try again in 1 second.");
        return;
    }

    try {
        const { user, analysis, recent_posts } = data;
        const score = analysis.risk_score / 100;
        
        const rawDecision = analysis.decision.toUpperCase();
        let displayDecision = "REVIEW";
        if (rawDecision.includes("APPROVE")) displayDecision = "APPROVE";
        else if (rawDecision.includes("REJECT") || rawDecision.includes("DECLINE")) displayDecision = "DECLINE";

        const pdf = new jsPDF("p", "mm", "a4");
        
        // Header styling
        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(24);
        pdf.setTextColor(40, 40, 40);
        pdf.text("VeriDrive Decision Report", 20, 25);
        
        pdf.setDrawColor(200, 200, 200);
        pdf.line(20, 32, 190, 32);

        // User Info Block
        pdf.setFontSize(16);
        pdf.setTextColor(20, 20, 20);
        pdf.text(`@${user.username}`, 20, 45);
        
        pdf.setFontSize(11);
        pdf.setFont("helvetica", "normal");
        pdf.setTextColor(100, 100, 100);
        pdf.text(`Display Name: ${user.display_name}`, 20, 52);
        pdf.text(`Date Generated: ${new Date().toLocaleDateString()}`, 20, 58);

        // Decision Block
        pdf.setFillColor(245, 245, 245);
        pdf.roundedRect(20, 68, 170, 35, 3, 3, "F");

        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(12);
        pdf.setTextColor(100, 100, 100);
        pdf.text("FINAL DECISION", 25, 78);

        pdf.setFontSize(22);
        if (displayDecision === "APPROVE") pdf.setTextColor(46, 160, 67); // Green
        else if (displayDecision === "DECLINE") pdf.setTextColor(218, 54, 51); // Red
        else pdf.setTextColor(210, 153, 34); // Yellow
        pdf.text(displayDecision, 25, 88);

        pdf.setFontSize(16);
        pdf.setTextColor(40, 40, 40);
        pdf.text(`Risk Score: ${(score * 100).toFixed(0)} / 100`, 120, 88);

        // Stats Grid
        pdf.setFontSize(10);
        pdf.setTextColor(150, 150, 150);
        pdf.text("Confidence", 25, 120);
        pdf.text("Model Latency", 65, 120);
        pdf.text("Account Age", 110, 120);
        pdf.text("Followers", 155, 120);

        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(14);
        pdf.setTextColor(40, 40, 40);
        pdf.text(`${analysis.confidence}`, 25, 128);
        pdf.text(`${analysis.latency}`, 65, 128);
        pdf.text(user.account_age ? `${user.account_age} days` : "N/A", 110, 128);
        pdf.text(user.followers != null ? `${user.followers}` : "N/A", 155, 128);

        pdf.line(20, 140, 190, 140);

        // Rationale Section
        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(16);
        pdf.text("AI Rationale", 20, 155);

        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(11);
        let yPos = 165;
        
        analysis.reasons.forEach((reason: string) => {
            if (yPos > 270) {
                pdf.addPage();
                yPos = 20;
            }
            pdf.setTextColor(60, 60, 60);
            pdf.text("•", 20, yPos);
            const lines = pdf.splitTextToSize(reason, 160);
            pdf.text(lines, 26, yPos);
            yPos += (lines.length * 5) + 4;
        });

        // Recent Activity Section
        yPos += 10;
        if (yPos > 260) {
            pdf.addPage();
            yPos = 25;
        }

        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(16);
        pdf.setTextColor(40, 40, 40);
        pdf.text("Posts Reviewed", 20, yPos);
        
        yPos += 12;
        pdf.setFontSize(10);
        
        recent_posts.forEach((post: any, idx: number) => {
            if (yPos > 270) {
                pdf.addPage();
                yPos = 20;
            }
            pdf.setFont("helvetica", "bold");
            pdf.setTextColor(150, 150, 150);
            pdf.text(`Sample #${idx + 1}`, 20, yPos);
            yPos += 5;

            pdf.setFont("helvetica", "normal");
            pdf.setTextColor(80, 80, 80);
            const lines = pdf.splitTextToSize(post.text, 170);
            pdf.text(lines, 20, yPos);
            yPos += (lines.length * 5) + 6;
        });

        pdf.save(`VeriDrive_Report_${user.username || "manual"}.pdf`);
        console.log("PDF saved successfully");
    } catch (error) {
        console.error("PDF text generation failed:", error);
        alert("Failed to generate PDF. Please try again.");
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    
    // Use the current host to ensure consistency (localhost vs 127.0.0.1)
    const backendHost = window.location.hostname;
    const backendUrl = `http://${backendHost}:8000`;

    let retryCount = 0;
    const maxRetries = 30; // 30 seconds of polling
    let interval: any;

    const fetchResult = () => {
      if (!id) return;
      
      fetch(`${backendUrl}/get_analysis/${id}`)
        .then((res) => {
          if (res.status === 404) {
            // Not ready yet, keep polling
            retryCount++;
            if (retryCount >= maxRetries) {
              clearInterval(interval);
              setError("Analysis timed out. Please try again.");
            }
            return null;
          }
          return res.json();
        })
        .then((json) => {
          if (!json) return;
          
          if (!json.error) {
            setData(json);
            clearInterval(interval);
          } else {
            console.error("Backend error:", json.error);
            setError(json.error);
            clearInterval(interval);
          }
        })
        .catch((err) => {
          console.error("Failed to fetch analysis", err);
          // Don't clear interval on network error, might be a temporary hiccup
          if (retryCount >= maxRetries) {
            setError("Network error. Backend might be down.");
            clearInterval(interval);
          }
        });
    };

    if (id) {
      fetchResult();
      interval = setInterval(fetchResult, 2000); // Poll every 2 seconds
    } else if (typeof window !== "undefined") {
      const saved = localStorage.getItem("veridrive_result");
      if (saved) {
        try {
          setData(JSON.parse(saved).result_data);
        } catch (e) {
          console.error("Failed to parse analysis data", e);
        }
      } else {
        setError("No analysis ID provided.");
      }
    }

    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Analysis Failed</h1>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
          <div className="mt-6">
            <a href="/" className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90">
              Back to Safety
            </a>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-ember border-t-transparent mx-auto" />
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Loading Analysis Results...
          </p>
        </div>
      </div>
    );
  }

  const { user, analysis, recent_posts } = data;
  const score = analysis.risk_score / 100;
  
  // Normalize decision labels
  const rawDecision = analysis.decision.toUpperCase();
  let displayDecision = "REVIEW";
  let decisionColor = "var(--warning)";

  if (rawDecision.includes("APPROVE")) {
    displayDecision = "APPROVE";
    decisionColor = "var(--success)";
  } else if (rawDecision.includes("REJECT") || rawDecision.includes("DECLINE")) {
    displayDecision = "DECLINE";
    decisionColor = "var(--danger)";
  }

  const tweetsPerDay =
    user.total_posts != null && user.account_age != null
      ? (user.total_posts / Math.max(1, parseInt(user.account_age))).toFixed(2)
      : null;
  const ratio = user.ff_ratio != null ? user.ff_ratio : null;
  const isManual = data.platform === "Manual";

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SiteHeader />
      <CarSlideshow intensity="soft" />

      {/* Floating Action Button for PDF */}
      <div className="fixed bottom-8 right-8 z-[1000] animate-float-up print:hidden" style={{ animationDelay: '1s' }}>
        <button 
          onClick={(e) => {
            console.log("Floating Export PDF clicked");
            e.preventDefault();
            e.stopPropagation();
            handleDownloadPDF();
          }}
          className="group relative flex items-center gap-3 overflow-hidden rounded-full bg-gradient-ember px-8 py-4 font-mono text-xs font-bold uppercase tracking-[0.2em] text-primary-foreground shadow-ember transition-all hover:scale-105 active:scale-95 pointer-events-auto cursor-pointer"
        >
          <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          <span>Export PDF Report</span>
          <div className="absolute inset-0 -z-10 bg-white/10 opacity-0 transition-opacity group-hover:opacity-10" />
        </button>
      </div>

      <main ref={reportRef} className="relative z-10 mx-auto max-w-7xl px-6 pb-20 pt-32">
        {/* Header strip */}
        <div className="relative z-[110] mb-10 flex flex-wrap items-end justify-between gap-6 animate-float-up">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">
              Decision report · {new Date().toLocaleDateString()}
            </div>
            <h1 className="mt-2 font-display text-6xl leading-none md:text-7xl">
              {isManual ? user.display_name : `@${user.username}`}
            </h1>
            <div className="mt-2 text-muted-foreground">{isManual ? "Manual Entry" : user.display_name}</div>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={isManual ? "/manual" : "http://localhost:8000/login/mastodon"}
              className="relative z-30 rounded-full border border-border bg-card/60 px-5 py-2 font-mono text-[10px] uppercase tracking-[0.3em] backdrop-blur transition hover:border-primary/60 pointer-events-auto print:hidden"
            >
              ↻ Re-run
            </a>
            <button 
              onClick={(e) => {
                console.log("Export PDF button clicked");
                e.preventDefault();
                e.stopPropagation();
                handleDownloadPDF();
              }}
              className="relative z-[999] cursor-pointer rounded-full bg-gradient-ember px-5 py-2 font-mono text-[10px] uppercase tracking-[0.3em] text-primary-foreground shadow-ember pointer-events-auto active:scale-95 transition-all print:hidden"
            >
              Export PDF
            </button>
          </div>
        </div>

        {/* Hero row: gauge + decision */}
        <div className="grid gap-6 lg:grid-cols-12">
          <div
            className="glass animate-float-up rounded-2xl p-8 lg:col-span-5"
            style={{ animationDelay: "0.1s" }}
          >
            <div className="flex flex-col items-center">
              <RiskGauge score={score} size={340} />
              <div className="mt-8 grid w-full grid-cols-3 gap-2 text-center font-mono text-[10px] uppercase tracking-[0.25em]">
                <div className="rounded-md border border-border py-2 text-[color:var(--success)]">Low<br />0–33</div>
                <div className="rounded-md border border-border py-2 text-[color:var(--warning)]">Medium<br />34–66</div>
                <div className="rounded-md border border-border py-2 text-[color:var(--danger)]">High<br />67–100</div>
              </div>
            </div>
          </div>

          <div
            className="relative animate-float-up overflow-hidden rounded-2xl border bg-card/60 p-8 backdrop-blur lg:col-span-7"
            style={{
              animationDelay: "0.2s",
              borderColor: decisionColor,
              boxShadow: `0 0 80px -20px ${decisionColor}`,
            }}
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-muted-foreground">
              Final decision
            </div>
            <div
              className="mt-4 font-display text-[clamp(4rem,11vw,9rem)] leading-[0.85]"
              style={{ color: decisionColor }}
            >
              {displayDecision}
            </div>
            <p className="mt-4 max-w-md text-sm text-muted-foreground">
              {displayDecision === "APPROVE"
                ? "Profile looks consistent with a normal user. Proceed with rental."
                : displayDecision === "REVIEW"
                ? "Profile shows mixed signals. Manual verification recommended."
                : "Multiple high-risk indicators detected. Decline or request additional documents."}
            </p>

            <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Mini label="Confidence" value={analysis.confidence} />
              <Mini label="Model" value="Risk Engine v3" />
              <Mini label="Latency" value={analysis.latency} />
              <Mini label="Signals" value={recent_posts.length} />
            </div>

            <div
              className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full blur-3xl"
              style={{ background: decisionColor, opacity: 0.18 }}
            />
          </div>
        </div>

        {/* Stats grid */}
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-float-up" style={{ animationDelay: "0.3s" }}>
          <StatCard label="Followers" value={user.followers ?? "N/A"} hint={ratio != null ? `F/F ratio · ${ratio}` : undefined} />
          <StatCard label="Following" value={user.following ?? "N/A"} />
          <StatCard label="Posts" value={user.total_posts ?? "N/A"} hint={tweetsPerDay != null ? `${tweetsPerDay} / day` : undefined} />
          <StatCard label="Account age" value={user.account_age ?? "N/A"} hint={user.account_age ? "created recently" : undefined} accent />
        </div>

        {/* Explanation + posts */}
        <div className="mt-6 grid gap-6 lg:grid-cols-12">
          <div
            className="glass animate-float-up rounded-2xl p-8 lg:col-span-7"
            style={{ animationDelay: "0.4s" }}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-ember">
                  AI rationale
                </div>
                <h2 className="mt-1 font-display text-3xl">Why this decision</h2>
              </div>
              <span className="rounded-full border border-border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                Explainable
              </span>
            </div>

            <ul className="mt-6 space-y-3">
              {analysis.reasons.map((reason: string, idx: number) => {
                const isPositive = reason.toLowerCase().includes("low risk") || reason.toLowerCase().includes("human");
                const sevColor = isPositive ? "var(--success)" : "var(--danger)";
                return (
                  <li
                    key={idx}
                    className="group relative overflow-hidden rounded-lg border border-border bg-background/40 p-4 transition hover:border-primary/40"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <span
                          className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-md font-mono text-[11px]"
                          style={{
                            color: sevColor,
                            background: `${sevColor.replace(")", " / 0.12)")}`,
                            border: `1px solid ${sevColor.replace(")", " / 0.4)")}`,
                          }}
                        >
                          {isPositive ? "+" : "!"}
                        </span>
                        <div>
                          <div className="font-semibold">{reason}</div>
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          <div
            className="glass animate-float-up rounded-2xl p-8 lg:col-span-5"
            style={{ animationDelay: "0.5s" }}
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-ember">
              Recent activity
            </div>
            <h2 className="mt-1 font-display text-3xl">Posts reviewed</h2>

            <ul className="mt-6 space-y-3">
              {recent_posts.map((p: any, i: number) => (
                <li
                  key={i}
                  className="rounded-lg border border-border bg-background/40 p-4 text-sm"
                >
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
                    Sample · #{i + 1}
                  </div>
                  <div className="text-foreground line-clamp-3">{p.text}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-border bg-background/40 p-3 text-center">
      <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-display text-xl">{value}</div>
    </div>
  );
}
