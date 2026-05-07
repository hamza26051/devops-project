import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { CarSlideshow } from "@/components/CarSlideshow";
import { SiteHeader } from "@/components/SiteHeader";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "@/lib/firebase";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    setIsAdmin(!!localStorage.getItem("admin_token"));
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      navigate({ to: "/" });
    } catch (err: any) {
      setError(err.message || "Login failed.");
      setLoading(false);
    }
  };

  if (isAdmin) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <SiteHeader />
        <CarSlideshow />
        <main className="relative z-10 mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 pb-20 pt-32 text-center">
          <h1 className="mt-3 font-display text-4xl leading-none text-danger">Access Denied</h1>
          <p className="mt-4 text-muted-foreground">
            You are currently logged in as an Admin. Please log out first to sign in as a user.
          </p>
        </main>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SiteHeader />
      <CarSlideshow />

      <main className="relative z-10 mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 pb-20 pt-32">
        <div className="mb-8 text-center">
          <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">
            Welcome back
          </div>
          <h1 className="mt-3 font-display text-4xl leading-none md:text-5xl">
            Log In
          </h1>
          <p className="mx-auto mt-4 text-muted-foreground">
            Sign in to view your analyses and notifications.
          </p>
        </div>

        <form onSubmit={handleLogin} className="glass rounded-2xl border border-white/10 p-8 backdrop-blur">
          <div className="mb-4">
            <label className="mb-2 block font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-border bg-background/60 px-4 py-3 text-sm text-foreground focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
              placeholder="you@example.com"
              required
            />
          </div>
          <div className="mb-6">
            <label className="mb-2 block font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-border bg-background/60 px-4 py-3 text-sm text-foreground focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
              placeholder="Your password"
              required
            />
          </div>

          {error && (
            <div className="mb-4 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-full bg-gradient-ember py-4 font-semibold uppercase tracking-[0.15em] text-primary-foreground shadow-ember transition hover:scale-[1.01] active:scale-95 disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            No account?{" "}
            <a href="/signup" className="text-ember hover:underline">
              Sign up
            </a>
          </p>
        </form>
      </main>
    </div>
  );
}
