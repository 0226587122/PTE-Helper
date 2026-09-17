import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useSignUp } from "../api/hooks";
import styles from "./Pages.module.css";

export default function SignUp() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const signUp = useSignUp();
  const navigate = useNavigate();
  const error = signUp.error as ApiError | null;

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    signUp.mutate({ display_name: name, email, password }, { onSuccess: () => navigate("/", { replace: true }) });
  };

  return (
    <div className={styles.authCard}>
      <h1>Create your account</h1>
      <p className={styles.hint}>Practise all 22 PTE Academic task types with real exam timing.</p>
      <form className={styles.form} onSubmit={onSubmit}>
        {error && (
          <div className={styles.errorBox}>
            {error.message}
            {error.details.length > 0 && (
              <ul>
                {error.details.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        <label className={styles.field}>
          Your name
          <input autoComplete="name" required maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className={styles.field}>
          Email
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className={styles.field}>
          Password
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <span className={styles.hint}>At least 8 characters.</span>
        </label>
        <button type="submit" className={styles.startButton} disabled={signUp.isPending}>
          {signUp.isPending ? "Creating your account…" : "Create account"}
        </button>
      </form>
      <p className={styles.hint}>
        Already have an account? <Link to="/signin">Sign in</Link>
      </p>
    </div>
  );
}
