import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api, ApiError } from "../api";
import { clearUser, getUser, setUser } from "../auth";

// App shell: brand, nav, and API key login gate.
// The role dropdown is gone — role is determined server-side by the API key.
export function Layout() {
  const [user, setUserState] = useState(getUser);
  const [keyInput, setKeyInput] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    const key = keyInput.trim();
    if (!key) return;
    setLoading(true);
    setLoginError(null);
    // Temporarily write the key so api.me() picks it up from getUser().
    setUser({ email: "", role: "sales", apiKey: key });
    try {
      // Validate the key against the backend and retrieve email + role.
      const identity = await api.me();
      const confirmed = { email: identity.email, role: identity.role as typeof user.role, apiKey: key };
      setUser(confirmed);
      setUserState(confirmed);
      setKeyInput("");
    } catch (err) {
      // Key was invalid — clear the temporary storage.
      clearUser();
      if (err instanceof ApiError && err.status === 401) {
        setLoginError("Invalid API key. Ask your Porter admin for one.");
      } else {
        setLoginError("Cannot reach the Porter API. Is it running?");
      }
    } finally {
      setLoading(false);
    }
  }

  function onLogout() {
    clearUser();
    setUserState(null);
  }

  if (!user) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#091524",
        }}
      >
        <form
          onSubmit={onLogin}
          style={{
            background: "#112036",
            border: "1px solid #1e3a5f",
            borderRadius: 10,
            padding: "2.5rem 2rem",
            width: 380,
            display: "flex",
            flexDirection: "column",
            gap: "1.1rem",
          }}
        >
          <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "#dde8ff" }}>
            Porter Verify
          </div>
          <div style={{ fontSize: "0.82rem", color: "#7aa3cc" }}>
            Enter your API key to continue. Keys are issued by your Porter admin.
          </div>
          <input
            type="password"
            autoFocus
            placeholder="sk-v1-…"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            style={{
              background: "#182d4a",
              border: "1px solid #274d7a",
              borderRadius: 6,
              padding: "0.6rem 0.8rem",
              color: "#dde8ff",
              fontSize: "0.9rem",
              outline: "none",
            }}
          />
          {loginError && (
            <div style={{ fontSize: "0.8rem", color: "#f87171" }}>{loginError}</div>
          )}
          <button
            type="submit"
            disabled={loading || !keyInput.trim()}
            style={{
              background: "#0ea5e9",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "0.6rem 1rem",
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
              opacity: loading || !keyInput.trim() ? 0.6 : 1,
            }}
          >
            {loading ? "Verifying…" : "Sign in"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <>
      <header className="header">
        <span className="brand">Porter Verify</span>
        <nav>
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/report">Verification report</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/recent">Recent businesses</NavLink>
          <NavLink to="/ucc">UCC lookup</NavLink>
          <NavLink to="/ucc/coverage">UCC coverage</NavLink>
          <NavLink to="/ucc/manual-queue">Manual UCC queue</NavLink>
        </nav>
        <div className="row" style={{ alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "0.78rem", color: "#d7e6f3" }}>{user.email}</span>
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              background: "rgba(14,165,233,.15)",
              color: "#38bdf8",
              border: "1px solid rgba(14,165,233,.3)",
              borderRadius: 4,
              padding: "0.15rem 0.45rem",
            }}
          >
            {user.role}
          </span>
          <button
            onClick={onLogout}
            style={{
              fontSize: "0.75rem",
              background: "transparent",
              color: "#7aa3cc",
              border: "1px solid #1e3a5f",
              borderRadius: 5,
              padding: "0.2rem 0.55rem",
              cursor: "pointer",
            }}
          >
            Log out
          </button>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
