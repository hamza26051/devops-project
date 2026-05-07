import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { CarSlideshow } from "@/components/CarSlideshow";
import { SiteHeader } from "@/components/SiteHeader";
import { StatCard } from "@/components/StatCard";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "@/lib/firebase";

export const Route = createFileRoute("/admin")({
  head: () => ({
    meta: [
      { title: "Admin Dashboard — VeriDrive" },
      { name: "description", content: "Operations overview for VeriDrive risk decisions." },
    ],
  }),
  component: AdminPage,
});

function AdminPage() {
  const [token, setToken] = useState<string | null>(null);
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [viewingPosts, setViewingPosts] = useState<any[] | null>(null);
  const [isFirebaseUser, setIsFirebaseUser] = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setIsFirebaseUser(!!u);
    });
    return () => unsub();
  }, []);

  useEffect(() => {
    setToken(localStorage.getItem("admin_token"));
  }, []);

  const isLoggedIn = !!token;

  const fetchRecords = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/admin/records", {
        headers: { "X-Admin-Token": token },
      });
      if (res.status === 401) {
        localStorage.removeItem("admin_token");
        setToken(null);
        setError("Session expired. Please log in again.");
        return;
      }
      const data = await res.json();
      setRecords(data.records || []);
    } catch (e) {
      setError("Failed to fetch records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchRecords();
      const interval = setInterval(fetchRecords, 10000);
      return () => clearInterval(interval);
    }
  }, [token]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    try {
      const res = await fetch("http://localhost:8000/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm),
      });
      if (!res.ok) {
        setLoginError("Invalid credentials.");
        return;
      }
      const data = await res.json();
      localStorage.setItem("admin_token", data.token);
      setToken(data.token);
    } catch {
      setLoginError("Network error.");
    }
  };

  const handleDecide = async (recordId: string, decision: "APPROVE" | "DECLINE") => {
    if (!token) return;
    try {
      const res = await fetch(`http://localhost:8000/admin/records/${recordId}/decide`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token,
        },
        body: JSON.stringify({ decision, notes: reviewNote }),
      });
      if (res.ok) {
        setReviewing(null);
        setReviewNote("");
        fetchRecords();
      }
    } catch {
      setError("Failed to submit decision.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    setToken(null);
    setRecords([]);
  };

  // Stats
  const total = records.length;
  const approved = records.filter((r) => r.status === "AUTO_APPROVED" || r.status === "ADMIN_APPROVED").length;
  const declined = records.filter((r) => r.status === "AUTO_DECLINED" || r.status === "ADMIN_DECLINED").length;
  const needsReview = records.filter((r) => r.status === "NEEDS_REVIEW").length;

  if (!isLoggedIn) {
    if (isFirebaseUser) {
      return (
        <div className="relative min-h-screen overflow-hidden">
          <SiteHeader />
          <CarSlideshow />
          <main className="relative z-10 mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 pb-20 pt-32 text-center">
            <h1 className="mt-3 font-display text-4xl leading-none text-danger">Access Denied</h1>
            <p className="mt-4 text-muted-foreground">
              You are currently logged in as a user. Please log out first to access the Admin Dashboard.
            </p>
          </main>
        </div>
      );
    }

    return (
      <div className="relative min-h-screen overflow-hidden">
        <SiteHeader />
        <CarSlideshow intensity="soft" />
        <main className="relative z-10 mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 pb-20 pt-32">
          <div className="mb-8 text-center">
            <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">Restricted</div>
            <h1 className="mt-3 font-display text-4xl leading-none md:text-5xl">Admin Access</h1>
          </div>
          <form onSubmit={handleLogin} className="glass rounded-2xl border border-white/10 p-8 backdrop-blur">
            <div className="mb-4">
              <label className="mb-2 block font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">Username</label>
              <input
                type="text"
                value={loginForm.username}
                onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                className="w-full rounded-xl border border-border bg-background/60 px-4 py-3 text-sm text-foreground focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                required
              />
            </div>
            <div className="mb-6">
              <label className="mb-2 block font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">Password</label>
              <input
                type="password"
                value={loginForm.password}
                onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                className="w-full rounded-xl border border-border bg-background/60 px-4 py-3 text-sm text-foreground focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                required
              />
            </div>
            {loginError && <div className="mb-4 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{loginError}</div>}
            <button type="submit" className="w-full rounded-full bg-gradient-ember py-4 font-semibold uppercase tracking-[0.15em] text-primary-foreground shadow-ember transition hover:scale-[1.01] active:scale-95">
              Sign In
            </button>
          </form>
        </main>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SiteHeader />
      <CarSlideshow intensity="soft" />

      <main className="relative mx-auto max-w-7xl px-6 pb-20 pt-32">
        <div className="mb-10 flex flex-wrap items-end justify-between gap-6 animate-float-up">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">
              Operations · live
            </div>
            <h1 className="mt-2 font-display text-6xl leading-none md:text-7xl">
              Command Center
            </h1>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-full border border-border bg-card/60 px-5 py-2 font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground backdrop-blur transition hover:border-danger/40 hover:text-danger"
          >
            Log Out
          </button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-float-up" style={{ animationDelay: "0.1s" }}>
          <StatCard label="Total checks" value={total} hint="All submissions" />
          <StatCard label="Needs review" value={needsReview} hint="Pending admin action" accent />
          <StatCard label="Approved" value={approved} hint="Auto + admin" />
          <StatCard label="Declined" value={declined} hint="Auto + admin" />
        </div>

        {/* Records table */}
        <div className="glass animate-float-up mt-6 overflow-hidden rounded-2xl" style={{ animationDelay: "0.2s" }}>
          <div className="flex items-center justify-between border-b border-border p-6">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-ember">Stream</div>
              <h2 className="mt-1 font-display text-3xl">Analysis Records</h2>
            </div>
            <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              <span className="h-2 w-2 animate-pulse rounded-full bg-ember" /> live
            </span>
          </div>

          {loading && records.length === 0 ? (
            <div className="p-10 text-center text-muted-foreground">Loading records...</div>
          ) : records.length === 0 ? (
            <div className="p-10 text-center text-muted-foreground">No records yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                    <th className="px-6 py-3">User</th>
                    <th className="px-6 py-3">Score</th>
                    <th className="px-6 py-3">AI Decision</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Posts</th>
                    <th className="px-6 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r) => {
                    const aiScore = r.ai_result?.risk_score ?? 0;
                    const aiDecision = r.ai_result?.decision ?? "UNKNOWN";
                    const needsAction = r.status === "NEEDS_REVIEW";
                    const color =
                      r.status === "AUTO_APPROVED" || r.status === "ADMIN_APPROVED"
                        ? "var(--success)"
                        : r.status === "AUTO_DECLINED" || r.status === "ADMIN_DECLINED"
                        ? "var(--danger)"
                        : "var(--warning)";

                    return (
                      <tr key={r.id} className="border-t border-border transition hover:bg-card/50">
                        <td className="px-6 py-4">
                          <div className="font-semibold">{r.user_email || r.user_id || "Unknown"}</div>
                          <div className="font-mono text-[10px] text-muted-foreground">{r.user_display_name}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <span className="font-display text-2xl" style={{ color }}>
                              {aiScore}
                            </span>
                            <div className="h-1 w-20 overflow-hidden rounded-full bg-border">
                              <div className="h-full" style={{ width: `${Math.min(aiScore, 100)}%`, background: color }} />
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.3em]" style={{ color, borderColor: color }}>
                            {aiDecision.replace(" CAR RENTAL", "").replace(" CUSTOMER", "")}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-mono text-xs" style={{ color }}>
                          {r.status?.replace(/_/g, " ")}
                        </td>
                        <td className="px-6 py-4 cursor-pointer hover:bg-white/5 transition" onClick={() => setViewingPosts(r.posts || [])}>
                          <div className="max-w-[200px] space-y-1">
                            {r.posts?.slice(0, 2).map((p: any, i: number) => {
                              const text = typeof p === 'string' ? p : p.text;
                              return <p key={i} className="truncate text-xs text-muted-foreground" title={text}>{text}</p>;
                            })}
                            {(r.posts?.length || 0) > 2 && (
                              <p className="text-[10px] text-ember mt-1">Click to view all {r.posts.length} posts</p>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          {needsAction ? (
                            <div className="flex items-center justify-end gap-2">
                              {reviewing === r.id ? (
                                <div className="flex items-center gap-2">
                                  <input
                                    type="text"
                                    value={reviewNote}
                                    onChange={(e) => setReviewNote(e.target.value)}
                                    placeholder="Note (optional)"
                                    className="w-32 rounded-lg border border-border bg-background/60 px-2 py-1 text-xs text-foreground"
                                  />
                                  <button
                                    onClick={() => handleDecide(r.id, "APPROVE")}
                                    className="rounded-lg bg-success/20 px-3 py-1 text-xs text-success hover:bg-success/30"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    onClick={() => handleDecide(r.id, "DECLINE")}
                                    className="rounded-lg bg-danger/20 px-3 py-1 text-xs text-danger hover:bg-danger/30"
                                  >
                                    Decline
                                  </button>
                                  <button
                                    onClick={() => { setReviewing(null); setReviewNote(""); }}
                                    className="text-[10px] text-muted-foreground hover:text-foreground"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => { setReviewing(r.id); setReviewNote(""); }}
                                  className="rounded-full bg-warning/20 px-4 py-2 text-xs font-semibold text-warning hover:bg-warning/30"
                                >
                                  Review
                                </button>
                              )}
                            </div>
                          ) : r.admin_review ? (
                            <span className="font-mono text-[10px] text-muted-foreground">
                              {r.admin_review.decision} by {r.admin_review.reviewed_by}
                            </span>
                          ) : (
                            <span className="font-mono text-[10px] text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error}
          </div>
        )}
      </main>

      {viewingPosts && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-6 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200" onClick={() => setViewingPosts(null)}>
          <div className="glass w-full max-w-2xl max-h-[80vh] overflow-hidden rounded-2xl border border-white/10 flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-border p-6 bg-card/40">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.4em] text-ember">Details</div>
                <h3 className="font-display text-2xl mt-1">User Posts</h3>
              </div>
              <button onClick={() => setViewingPosts(null)} className="text-muted-foreground hover:text-foreground p-2 rounded-full hover:bg-white/5 transition">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-4">
              {viewingPosts.map((p: any, i: number) => {
                const text = typeof p === 'string' ? p : p.text;
                return (
                  <div key={i} className="rounded-xl border border-border bg-background/40 p-4 text-sm">
                    <div className="mb-2 text-[10px] text-muted-foreground uppercase font-mono tracking-widest">Post #{i + 1}</div>
                    <div className="text-foreground/90 whitespace-pre-wrap">{text}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
