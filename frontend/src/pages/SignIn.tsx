import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useSignIn } from "../api/hooks";
import styles from "./Pages.module.css";

function safeNext(next: string | null) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const signIn = useSignIn();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    signIn.mutate({ email, password }, { onSuccess: () => navigate(safeNext(params.get("next")), { replace: true }) });
  };

  return (
    <div className={styles.authCard}>
      <h1>Welcome back</h1>
      <p className={styles.hint}>Sign in to keep practising and see your progress.</p>
      <form className={styles.form} onSubmit={onSubmit}>
        {signIn.error && <div className={styles.errorBox}>{(signIn.error as ApiError).message}</div>}
        <label className={styles.field}>
          Email
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className={styles.field}>
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" className={styles.startButton} disabled={signIn.isPending}>
          {signIn.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className={styles.hint}>
        New here? <Link to="/signup">Create a free account</Link>
      </p>
    </div>
  );
}
