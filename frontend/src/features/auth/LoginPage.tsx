import { FormEvent, useState } from "react";
import { BookOpenCheck } from "lucide-react";

import { useAuthStore } from "./authStore";

export function LoginPage() {
  const login = useAuthStore((state) => state.login);
  const authError = useAuthStore((state) => state.error);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    await login(email.trim(), password);
    setIsSubmitting(false);
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-lockup">
          <span className="brand-icon">
            <BookOpenCheck aria-hidden="true" size={28} />
          </span>
          <div>
            <p className="eyebrow">Asistente educativo SBS</p>
            <h1>UNPRG</h1>
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Correo
            <input
              autoComplete="username"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Contraseña
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {authError ? <p className="form-error">{authError}</p> : null}
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <p className="login-hint">
          Usa un usuario creado en Firebase Authentication con proveedor
          email/password.
        </p>
      </section>
    </main>
  );
}
