import { NavLink, Outlet } from "react-router-dom";

import styles from "./Admin.module.css";

export function AdminLayout() {
  const tab = ({ isActive }: { isActive: boolean }) => (isActive ? styles.tabActive : styles.tab);
  return (
    <div>
      <h1>Question bank</h1>
      <nav className={styles.tabs} aria-label="Admin">
        <NavLink to="/admin" end className={tab}>
          Pool summary
        </NavLink>
        <NavLink to="/admin/questions" className={tab}>
          Questions
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
