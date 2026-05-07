import { Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { onAuthStateChanged, signOut, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { Logo } from "./Logo";

export function SiteHeader() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifs, setShowNotifs] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsAdmin(!!localStorage.getItem("admin_token"));
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      if (u) {
        localStorage.setItem("firebase_user", JSON.stringify({ uid: u.uid, email: u.email }));
      } else {
        localStorage.removeItem("firebase_user");
      }
    });
    return () => unsub();
  }, []);

  useEffect(() => {
    if (!user) return;
    const fetchNotifs = async () => {
      try {
        const token = await user.getIdToken();
        const res = await fetch("http://localhost:8000/user/notifications", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setNotifications(data.notifications || []);
          setUnreadCount(data.unread_count || 0);
        }
      } catch (e) {
        console.error("Failed to fetch notifications", e);
      }
    };
    fetchNotifs();
    const interval = setInterval(fetchNotifs, 15000);
    return () => clearInterval(interval);
  }, [user]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowNotifs(false);
      }
    };
    if (showNotifs) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showNotifs]);

  const markRead = async (notifId: string) => {
    if (!user) return;
    try {
      const token = await user.getIdToken();
      await fetch(`http://localhost:8000/user/notifications/${notifId}/read`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) {
      console.error("Failed to mark read", e);
    }
  };

  const handleLogout = async () => {
    await signOut(auth);
    localStorage.removeItem("firebase_user");
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  };

  const isLoggedIn = !!user || isAdmin;

  return (
    <header className="fixed inset-x-0 top-0 z-[100] pointer-events-none">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 pointer-events-none">
        <div className="pointer-events-auto">
          <Link to="/">
            <Logo />
          </Link>
        </div>
        <nav className="pointer-events-auto hidden items-center gap-8 font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground md:flex">
          <Link to="/" className="transition hover:text-ember [&.active]:text-ember">Overview</Link>
          <Link to="/admin" className="transition hover:text-ember [&.active]:text-ember">Admin</Link>
          <a href="/#how" className="transition hover:text-ember">How it works</a>
        </nav>
        <div className="pointer-events-auto flex items-center gap-3">
          {user && !isAdmin && (
            <div className="relative" ref={panelRef}>
              <button
                onClick={() => setShowNotifs(!showNotifs)}
                className="relative rounded-full border border-border bg-card/60 px-3 py-2 backdrop-blur transition hover:border-ember/40"
                title="Notifications"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                  <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                </svg>
                {unreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-ember text-[9px] font-bold text-white">
                    {unreadCount}
                  </span>
                )}
              </button>
              {showNotifs && (
                <div className="absolute right-0 top-full mt-2 w-80 glass rounded-2xl border border-white/10 p-4 backdrop-blur shadow-2xl">
                  <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                    Notifications
                  </div>
                  {notifications.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No notifications.</p>
                  ) : (
                    <ul className="max-h-64 space-y-2 overflow-y-auto">
                      {notifications.map((n) => (
                        <li
                          key={n.id}
                          className={`rounded-xl border p-3 ${
                            n.read ? "border-border bg-background/20" : "border-ember/30 bg-ember/5"
                          }`}
                        >
                          <p className="text-xs">{n.message}</p>
                          <div className="mt-1 flex items-center justify-between">
                            <span className="text-[9px] text-muted-foreground">
                              {n.created_at?.toDate ? n.created_at.toDate().toLocaleString() : "Just now"}
                            </span>
                            {!n.read && (
                              <button
                                onClick={() => markRead(n.id)}
                                className="text-[9px] text-ember hover:underline"
                              >
                                Mark read
                              </button>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}
          {isLoggedIn && (
            <button
              onClick={handleLogout}
              className="rounded-full border border-border bg-card/60 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground backdrop-blur transition hover:border-danger/40 hover:text-danger"
            >
              Log Out
            </button>
          )}
          {!isLoggedIn && (
            <>
              <Link
                to="/login"
                className="rounded-full border border-border bg-card/60 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] backdrop-blur transition hover:border-ember/60"
              >
                Log In
              </Link>
              <Link
                to="/signup"
                className="group relative inline-flex items-center gap-2 overflow-hidden rounded-full border border-border bg-card/60 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] backdrop-blur transition hover:border-ember/60 active:scale-95"
              >
                <span className="relative z-10">Sign Up</span>
                <div className="absolute inset-0 -z-10 bg-gradient-ember opacity-0 transition-opacity group-hover:opacity-10" />
              </Link>
            </>
          )}
          <a
            href="http://localhost:8000/login/mastodon"
            className="group relative inline-flex items-center gap-2 overflow-hidden rounded-full border border-border bg-card/60 px-5 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] backdrop-blur transition hover:border-ember/60 active:scale-95"
          >
            <span className="relative z-10">Run Check</span>
            <span className="relative z-10 text-ember">→</span>
            <div className="absolute inset-0 -z-10 bg-gradient-ember opacity-0 transition-opacity group-hover:opacity-10" />
          </a>
        </div>
      </div>
    </header>
  );
}
