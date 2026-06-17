import { NavLink, Outlet } from "react-router-dom";
import { getUser, ROLES, setUser, type Role } from "../auth";

// App shell: brand, nav, and the MVP role switcher (stands in for SSO).
export function Layout() {
  const user = getUser();

  function onRoleChange(role: Role) {
    setUser({ ...user, role });
    // Simplest correct refresh so all data re-fetches under the new role.
    window.location.reload();
  }

  return (
    <>
      <header className="header">
        <span className="brand">Porter Verify</span>
        <nav>
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/search">Search</NavLink>
        </nav>
        <div className="row" style={{ alignItems: "center" }}>
          <span style={{ fontSize: "0.8rem", color: "#d7e6f3" }}>{user.email}</span>
          <select
            value={user.role}
            onChange={(e) => onRoleChange(e.target.value as Role)}
            aria-label="Acting role"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
