import { FormEvent, useState } from "react";
import {
  ArrowRight,
  BookOpenCheck,
  Eye,
  GitBranch,
  Lock,
  Mail,
  MessageSquareQuote,
  Swords
} from "lucide-react";

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
    <main className="login-shell sbs-dark-login">
      <nav className="login-navbar" aria-label="Navegación institucional">
        <div className="login-brand">
          <BookOpenCheck aria-hidden="true" size={18} />
          <strong>SBS · UNPRG</strong>
        </div>
        <div className="login-navlinks">
          <span>Metodología</span>
          <span>Normativa</span>
          <strong>RES. 11356-2008</strong>
        </div>
      </nav>

      <section className="login-hero">
        <div className="login-hero-copy">
          <h1>
            Aprende clasificación crediticia SBS con{" "}
            <span>simulaciones, casos y retroalimentación normativa.</span>
          </h1>
          <p>
            Practica como analista, compara criterios regulatorios y revisa
            evidencia de aprendizaje con métricas para docentes.
          </p>
        </div>

        <div className="login-pill-row">
          <span>
            <Swords aria-hidden="true" size={14} />
            Debate
          </span>
          <span>
            <MessageSquareQuote aria-hidden="true" size={14} />
            Citas
          </span>
          <span>
            <GitBranch aria-hidden="true" size={14} />
            Evidencia
          </span>
        </div>
      </section>

      <section className="login-panel">
        <div className="login-panel-header">
          <h2>Acceso institucional</h2>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            <span>
              <Mail aria-hidden="true" size={16} />
              Correo
            </span>
            <input
              autoComplete="username"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            <span>
              <Lock aria-hidden="true" size={16} />
              Contraseña
            </span>
            <div className="password-field">
              <input
                autoComplete="current-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <Eye aria-hidden="true" size={16} />
            </div>
          </label>
          {authError ? <p className="form-error">{authError}</p> : null}
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Ingresando..." : "Ingresar"}
            <ArrowRight aria-hidden="true" size={16} />
          </button>
        </form>

        <p className="login-hint">Solo correos autorizados</p>
      </section>
    </main>
  );
}
