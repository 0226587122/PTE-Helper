import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { useMe, useSignOut } from "../api/hooks";
import styles from "./Layout.module.css";

export function Layout() {
  const me = useMe();
  const signOut = useSignOut();
  const navigate = useNavigate();
  const user = me.data;
  const linkClass = ({ isActive }: { isActive: boolean }) => (isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink);

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/" className={styles.brand}>
            <span className={styles.logo} aria-hidden>
              P
            </span>
            PTE BluePrep
          </Link>
          <nav className={styles.nav} aria-label="Main">
            {user ? (
              <>
                <NavLink to="/" end className={linkClass}>
                  Practice
                </NavLink>
                {user.role === "admin" && (
                  <NavLink to="/admin" className={linkClass}>
                    Question bank
                  </NavLink>
                )}
                <span className={styles.user}>{user.display_name}</span>
                <button
                  type="button"
                  className={styles.signOut}
                  onClick={() => signOut.mutate(undefined, { onSuccess: () => navigate("/signin") })}
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/signin" className={linkClass}>
                  Sign in
                </NavLink>
                <NavLink to="/signup" className={linkClass}>
                  Create account
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          All scores on this site are practice estimates to help you prepare. They are not official Pearson PTE Academic
          results, and this site is not affiliated with Pearson.
        </div>
      </footer>
    </div>
  );
}
