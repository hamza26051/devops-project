import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { onAuthStateChanged, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { CarSlideshow } from "@/components/CarSlideshow";
import { SiteHeader } from "@/components/SiteHeader";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "VeriDrive — AI Risk Analyzer for Car Rentals" },
      {
        name: "description",
        content:
          "Verify rental customers in seconds with social-signal AI. Login with Mastodon, get an instant risk score and decision.",
      },
      { property: "og:title", content: "VeriDrive — Smart Rental Risk Analyzer" },
      {
        property: "og:description",
        content: "AI-powered customer verification using Mastodon signals.",
      },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false); // Set to false by default to bypass landing hang

  useEffect(() => {
    console.log("LandingPage: Initializing auth listener");
    const unsub = onAuthStateChanged(auth, (u) => {
      console.log("LandingPage: Auth state changed", u ? "User logged in" : "No user");
      setUser(u);
      if (u) {
        localStorage.setItem("firebase_user", JSON.stringify({ uid: u.uid, email: u.email }));
      } else {
        localStorage.removeItem("firebase_user");
      }
    }, (error) => {
      console.error("LandingPage: Auth error", error);
    });

    return () => unsub();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-ember border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <SiteHeader />
        <CarSlideshow />
        <main className="relative z-10 mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 pb-20 pt-32">
          <div className="mb-8 text-center">
            <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">
              Welcome
            </div>
            <h1 className="mt-3 font-display text-4xl leading-none md:text-5xl">
              VeriDrive
            </h1>
            <p className="mx-auto mt-4 text-muted-foreground">
              Sign in to analyze rental risk with AI-powered social signal verification.
            </p>
          </div>

          <div className="glass rounded-2xl border border-white/10 p-8 backdrop-blur text-center">
            <Link
              to="/login"
              className="block w-full rounded-full bg-gradient-ember py-4 font-semibold uppercase tracking-[0.15em] text-primary-foreground shadow-ember transition hover:scale-[1.01] active:scale-95"
            >
              Log In
            </Link>
            <p className="mt-4 text-sm text-muted-foreground">
              No account?{" "}
              <Link to="/signup" className="text-ember hover:underline">
                Sign up
              </Link>
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SiteHeader />
      <CarSlideshow />
      <main className="relative z-10 mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-6 pb-20 pt-32">
        {/* Marquee strip */}
        <div className="mb-10 flex items-center gap-3 overflow-hidden font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          <span className="text-ember">●</span>
          <span>Live · Decision Engine v2.1</span>
          <span className="text-ember">●</span>
          <span className="h-px flex-1 bg-border" />
        </div>

        <div className="grid gap-12 lg:grid-cols-12 lg:items-end">
          <div className="lg:col-span-8 animate-float-up">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground backdrop-blur">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ember" />
              AI · Social Signal · Real-time
            </div>
            <h1 className="font-display text-[clamp(3.5rem,9vw,8.5rem)] leading-[0.85] tracking-tight text-foreground">
              Approve <br />
              the right <span className="text-gradient-ember">drivers.</span>
            </h1>
            <p className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground">
              VeriDrive analyzes a customer&apos;s public Mastodon footprint with a
              tuned XGBoost model — surfacing risk in under <span className="text-foreground">3 seconds</span>.
              No paperwork. No guesswork. Just a defensible decision.
            </p>

            <div className="mt-10 flex flex-wrap items-center gap-4">
              <a
                href="http://localhost:8000/login/mastodon"
                className="group relative inline-flex items-center gap-3 overflow-hidden rounded-full bg-gradient-ember px-8 py-4 font-semibold uppercase tracking-[0.2em] text-primary-foreground shadow-ember transition hover:scale-[1.02] active:scale-95"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                   <path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309-2.723.4-4.99 2.426-5.304 5.004-.314 2.578-.34 5.405-.34 5.405s.026 2.827.34 5.405c.314 2.578 2.581 4.61 5.304 5.004.453.067 1.308.309 5.288.309h.03c3.98 0 5.697-.242 6.15-.309 2.687-.394 4.954-2.426 5.304-5.004.314-2.578.34-5.405.34-5.405s-.026-2.827-.34-5.405zm-4.337 9.537c0 .542-.44.982-.982.982H6.464c-.542 0-.982-.44-.982-.982V6.464c0-.542.44-.982.982-.982h11.485c.542 0 .982.44.982.982v8.386z"/>
                </svg>
                <span>Login with Mastodon</span>
                <span className="transition group-hover:translate-x-1">→</span>
              </a>
              <a
                href="/manual"
                className="group relative inline-flex items-center gap-3 overflow-hidden rounded-full border border-border bg-card/60 px-8 py-4 font-semibold uppercase tracking-[0.2em] text-foreground backdrop-blur transition hover:border-ember/40 hover:scale-[1.02] active:scale-95"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
                <span>Enter Manually</span>
                <span className="transition group-hover:translate-x-1">→</span>
              </a>
              <a
                href="#how"
                className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground transition hover:text-foreground"
              >
                See how it works ↓
              </a>
            </div>
          </div>

          <div className="space-y-3 lg:col-span-4">
            {[
              { k: "Total checks", v: "1,284", note: "+12.4% week over week" },
              { k: "High risk", v: "412", note: "32% of all checks" },
              { k: "Low risk", v: "743", note: "58% approved" },
              { k: "Avg. latency", v: "2.3s", note: "p95 under 3s" },
            ].map((s, idx) => (
              <div
                key={s.k}
                className="glass animate-float-up rounded-xl p-5"
                style={{ animationDelay: `${0.2 + idx * 0.12}s` }}
              >
                <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                  {s.k}
                </div>
                <div className="mt-1 flex items-baseline justify-between">
                  <div className="font-display text-4xl text-foreground">{s.v}</div>
                  <div className="font-mono text-[11px] text-muted-foreground">{s.note}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom strip */}
        <div id="how" className="mt-32 space-y-32 pb-32">
          <div className="text-center">
            <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">
              The Architecture
            </div>
            <h2 className="mt-3 font-display text-5xl md:text-7xl">
              How VeriDrive Works
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
              Our system transforms raw social footprints into defensible rental decisions 
              using a sophisticated multi-stage MLOps pipeline.
            </p>
          </div>

          <div className="grid gap-12 lg:grid-cols-3">
            {[
              {
                n: "01",
                t: "Signal Harvesting",
                d: "We fetch the latest 10 posts, profile bio, and metadata from Mastodon using OAuth 2.0. We clean the data by removing HTML tags and normalizing text for model ingestion.",
                icon: "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
                color: "var(--ember)"
              },
              {
                n: "02",
                t: "Dual-Model Inference",
                d: "Two specialized models analyze the text: a Toxicity model (XGBoost) for harmful patterns and a Sentiment model (DistilBERT-style) for behavioral context.",
                icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
                color: "#ff8700"
              },
              {
                n: "03",
                t: "Context-Aware Fusion",
                d: "The Risk Engine combines signals. If a post is 'Offensive' but has 'Positive' sentiment (casual banter), the engine automatically discounts the risk to prevent false positives.",
                icon: "M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z",
                color: "#ff4d00"
              },
            ].map((step) => (
              <div key={step.n} className="glass group relative p-10 transition-all hover:-translate-y-2 hover:bg-card/80">
                <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-ember text-primary-foreground shadow-ember transition-transform group-hover:scale-110">
                  <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d={step.icon} />
                  </svg>
                </div>
                <div className="font-mono text-xs uppercase tracking-[0.4em] text-ember">
                  Phase {step.n}
                </div>
                <div className="mt-4 font-display text-4xl">{step.t}</div>
                <div className="mt-6 text-sm leading-relaxed text-muted-foreground">{step.d}</div>
                <div className="absolute bottom-0 left-0 h-1 w-0 bg-gradient-ember transition-all duration-500 group-hover:w-full" />
              </div>
            ))}
          </div>

          {/* Logic Breakdown */}
          <div className="glass overflow-hidden rounded-[2.5rem] border border-white/5">
            <div className="grid lg:grid-cols-2">
              <div className="p-16">
                <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-ember">
                  The Decision Brain
                </div>
                <h3 className="mt-2 font-display text-5xl">Risk Aggregation</h3>
                <p className="mt-8 text-base leading-relaxed text-muted-foreground">
                  VeriDrive doesn&apos;t just average scores. Our engine uses a weighted fusion formula designed to catch rare but dangerous signals while respecting overall user behavior.
                </p>
                
                <div className="mt-12 space-y-6">
                  {[
                    { l: "Toxicity Signal", p: "70%", d: "Focuses on hate speech, threats, and harassment markers.", icon: "⚠️" },
                    { l: "Sentiment Context", p: "30%", d: "Analyzes general mood to differentiate between aggression and enthusiasm.", icon: "🧠" },
                  ].map((item) => (
                    <div key={item.l} className="group rounded-2xl border border-border bg-background/40 p-6 transition hover:border-ember/40">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-xl">{item.icon}</span>
                          <span className="font-semibold text-lg">{item.l}</span>
                        </div>
                        <span className="font-mono text-xl text-ember">{item.p}</span>
                      </div>
                      <p className="mt-3 text-sm text-muted-foreground">{item.d}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-12 rounded-3xl bg-ember/5 p-8 border border-ember/20 backdrop-blur-sm">
                   <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-ember/60 mb-4">The Formula</div>
                   <code className="text-ember font-mono text-lg block bg-black/40 p-4 rounded-xl border border-white/5">
                     Score = 0.7 * max(signals) + 0.3 * mean(signals)
                   </code>
                   <p className="mt-5 text-xs leading-relaxed text-muted-foreground italic">
                     &quot;This ensures that a single high-risk post (max) correctly flags the profile, while the mean provides a buffer for generally positive users.&quot;
                   </p>
                </div>
              </div>
              
              <div className="relative min-h-[500px] bg-gradient-to-br from-card to-background p-16 flex flex-col items-center justify-center overflow-hidden border-l border-white/5">
                <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(var(--ember) 1px, transparent 1px)', backgroundSize: '30px 30px' }} />
                
                <div className="relative space-y-8 w-full max-w-md">
                   {/* Visual Example 1 */}
                   <div className="glass group p-8 rounded-[2rem] border-success/30 animate-float-up shadow-2xl transition-all hover:border-success/60" style={{ animationDelay: '0.1s' }}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="h-3 w-3 rounded-full bg-success animate-pulse" />
                          <span className="font-mono text-xs uppercase tracking-widest text-success font-bold">Safe Profile</span>
                        </div>
                        <span className="font-mono text-[10px] text-muted-foreground">Confidence: 94%</span>
                      </div>
                      <div className="mt-4 text-sm text-foreground/80">
                        &quot;I love this new rental service! Best experience ever.&quot;
                      </div>
                      <div className="mt-4 flex gap-2">
                        <span className="rounded-full bg-success/10 px-3 py-1 text-[10px] text-success border border-success/20">Positive Sentiment</span>
                        <span className="rounded-full bg-success/10 px-3 py-1 text-[10px] text-success border border-success/20">Low Toxicity</span>
                      </div>
                   </div>

                   {/* Visual Example 2 */}
                   <div className="glass group p-8 rounded-[2rem] border-danger/30 animate-float-up shadow-2xl transition-all hover:border-danger/60" style={{ animationDelay: '0.3s' }}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="h-3 w-3 rounded-full bg-danger animate-pulse" />
                          <span className="font-mono text-xs uppercase tracking-widest text-danger font-bold">High Risk</span>
                        </div>
                        <span className="font-mono text-[10px] text-muted-foreground">Confidence: 89%</span>
                      </div>
                      <div className="mt-4 text-sm text-foreground/80">
                        &quot;This is unacceptable. I will make sure everyone knows... [Flagged Content]&quot;
                      </div>
                      <div className="mt-4 flex gap-2">
                        <span className="rounded-full bg-danger/10 px-3 py-1 text-[10px] text-danger border border-danger/20">High Toxicity</span>
                        <span className="rounded-full bg-danger/10 px-3 py-1 text-[10px] text-danger border border-danger/20">Negative Sentiment</span>
                      </div>
                   </div>
                </div>

                <div className="mt-12 font-mono text-[10px] uppercase tracking-[0.5em] text-muted-foreground">
                  Real-time Decision Stream
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
