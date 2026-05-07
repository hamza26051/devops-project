import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { onAuthStateChanged, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { CarSlideshow } from "@/components/CarSlideshow";
import { SiteHeader } from "@/components/SiteHeader";

export const Route = createFileRoute("/manual")({
  head: () => ({
    meta: [
      { title: "Manual Entry — VeriDrive" },
      { name: "description", content: "Enter posts manually for risk analysis." },
    ],
  }),
  component: ManualEntryPage,
});

const MAX_POSTS = 10;

function ManualEntryPage() {
  const navigate = useNavigate();
  const [bio, setBio] = useState("");
  const [textPosts, setTextPosts] = useState<string[]>([""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => setUser(u));
    return () => unsub();
  }, []);

  const updatePost = (idx: number, value: string) => {
    const next = [...textPosts];
    next[idx] = value;
    setTextPosts(next);
  };

  const addPost = () => {
    if (textPosts.length < MAX_POSTS) {
      setTextPosts([...textPosts, ""]);
    }
  };

  const removePost = (idx: number) => {
    if (textPosts.length > 1) {
      const next = textPosts.filter((_, i) => i !== idx);
      setTextPosts(next);
    }
  };

  const handleSubmit = async () => {
    const validPosts = textPosts.map((p) => p.trim()).filter((p) => p.length > 0);
    if (validPosts.length === 0) {
      setError("Enter at least one post.");
      return;
    }
    setLoading(true);
    setError("");
    
    // Use the current host to ensure consistency (localhost vs 127.0.0.1)
    const backendHost = window.location.hostname;
    const backendUrl = `http://${backendHost}:8000`;
    
    try {
      let res;
      if (user) {
        const token = await user.getIdToken();
        res = await fetch(`${backendUrl}/user/analyze`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ posts: validPosts, bio: bio.trim() }),
        });
      } else {
        res = await fetch(`${backendUrl}/analyze/manual/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ posts: validPosts, bio: bio.trim() }),
        });
      }
      const data = await res.json();
      if (data.error) {
        setError(data.error);
        setLoading(false);
        return;
      }
      navigate({ to: "/analyze", search: { id: data.result_id, mode: "manual" } });
    } catch (err) {
      setError("Network error. Ensure the backend is running.");
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SiteHeader />
      <CarSlideshow intensity="soft" />

      <main className="relative z-10 mx-auto max-w-3xl px-6 pb-20 pt-32">
        <div className="mb-10 text-center">
          <div className="font-mono text-[11px] uppercase tracking-[0.4em] text-ember">
            Manual Entry
          </div>
          <h1 className="mt-3 font-display text-5xl leading-none md:text-6xl">
            Enter posts directly
          </h1>
          <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
            Provide up to 10 text posts. Our engine will analyze them without
            requiring a social login.
          </p>
        </div>

        <div className="glass rounded-2xl border border-white/10 p-8 backdrop-blur">
          {/* Bio */}
          <div className="mb-6">
            <label className="mb-2 block font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              Profile Bio (optional)
            </label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={2}
              className="w-full rounded-xl border border-border bg-background/60 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
              placeholder="Paste a short bio if you have one..."
            />
          </div>

          {/* Posts */}
          <div className="space-y-4">
            {textPosts.map((post, idx) => (
              <div key={idx} className="relative">
                <div className="mb-1 flex items-center justify-between">
                  <label className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                    Post #{idx + 1}
                  </label>
                  {textPosts.length > 1 && (
                    <button
                      onClick={() => removePost(idx)}
                      className="text-[10px] text-danger hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <textarea
                  value={post}
                  onChange={(e) => updatePost(idx, e.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-border bg-background/60 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                  placeholder="Paste post content here..."
                />
              </div>
            ))}
            {textPosts.length < MAX_POSTS && (
              <button
                onClick={addPost}
                className="w-full rounded-xl border border-dashed border-border py-3 text-sm text-muted-foreground transition hover:border-ember hover:text-foreground"
              >
                + Add another post ({textPosts.length}/{MAX_POSTS})
              </button>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="mt-4 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="mt-6 w-full rounded-full bg-gradient-ember py-4 font-semibold uppercase tracking-[0.15em] text-primary-foreground shadow-ember transition hover:scale-[1.01] active:scale-95 disabled:opacity-60"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Analyzing...
              </span>
            ) : (
              "Run Analysis"
            )}
          </button>

          <p className="mt-4 text-center text-[11px] text-muted-foreground">
            Social metrics (followers, following, account age) will be unavailable
            for manual entries.
          </p>
        </div>
      </main>
    </div>
  );
}
