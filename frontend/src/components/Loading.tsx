export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <p role="status" style={{ color: "var(--muted)" }}>
      {label}
    </p>
  );
}

export function ErrorMessage({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Something went wrong. Please refresh the page.";
  return (
    <p role="alert" style={{ color: "var(--red)", fontWeight: 600 }}>
      {message}
    </p>
  );
}
