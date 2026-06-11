import { FormEvent, useState } from "react";
import { BarChart3, BookOpenCheck, GraduationCap, ShieldCheck } from "lucide-react";

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
      <section className="login-hero">
        <div className="brand-lockup">
          <span className="brand-icon">
            <BookOpenCheck aria-hidden="true" size={28} />
          </span>
          <div>
            <p className="eyebrow">Asistente educativo SBS</p>
            <h1>UNPRG</h1>
          </div>
        </div>

        <div className="login-hero-copy">
          <p className="eyebrow">Resolución SBS N. 11356-2008</p>
          <h2>
            Aprende clasificación crediticia SBS con simulaciones, casos y
            retroalimentación normativa.
          </h2>
          <p>
            Una plataforma académica para practicar criterios regulatorios,
            defender decisiones y revisar evidencia de aprendizaje.
          </p>
        </div>

        <div className="login-feature-list">
          <span>
            <ShieldCheck aria-hidden="true" size={20} />
            Respuestas con citas normativas
          </span>
          <span>
            <GraduationCap aria-hidden="true" size={20} />
            Casos adaptativos para estudiantes
          </span>
          <span>
            <BarChart3 aria-hidden="true" size={20} />
            Analíticas para docentes
          </span>
        </div>
      </section>

      <section className="login-panel">
        <div className="login-panel-header">
          <p className="eyebrow">Acceso institucional</p>
          <h2>Ingresa a tu cuenta</h2>
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
          Usa el usuario asignado por el equipo del proyecto. El acceso docente
          se habilita solo para correos autorizados.
        </p>
      </section>
    </main>
  );
}
