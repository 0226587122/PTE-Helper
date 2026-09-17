import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useMe } from "../api/hooks";
import { Loading } from "./Loading";

export function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe();
  const location = useLocation();
  if (me.isLoading) return <Loading />;
  if (!me.data) return <Navigate to={`/signin?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return <>{children}</>;
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const me = useMe();
  if (me.isLoading) return <Loading />;
  if (!me.data) return <Navigate to="/signin?next=/admin" replace />;
  if (me.data.role !== "admin") return <p>You need an admin account to see the question bank.</p>;
  return <>{children}</>;
}
