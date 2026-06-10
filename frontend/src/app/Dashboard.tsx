import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";

import { useAuthStore } from "../features/auth/authStore";
import { AssistantChat } from "../features/chat/AssistantChat";
import { TeacherDashboard } from "./TeacherDashboard";

const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;
const ACTIVITY_EVENTS = ["click", "keydown", "mousemove", "scroll", "touchstart"];

export function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const userLabel = user?.email ?? user?.uid ?? "";
  const isTeacher = user?.email?.toLowerCase() === "docente@sbs.test";
  const [path, setPath] = useState(window.location.pathname);
  const isTeacherRoute = path === "/teacher";

  useEffect(() => {
    if (!user) {
      return undefined;
    }

    let timeoutId = window.setTimeout(() => {
      void logout();
    }, INACTIVITY_TIMEOUT_MS);

    function resetInactivityTimer() {
      window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        void logout();
      }, INACTIVITY_TIMEOUT_MS);
    }

    ACTIVITY_EVENTS.forEach((eventName) => {
      window.addEventListener(eventName, resetInactivityTimer, { passive: true });
    });

    return () => {
      window.clearTimeout(timeoutId);
      ACTIVITY_EVENTS.forEach((eventName) => {
        window.removeEventListener(eventName, resetInactivityTimer);
      });
    };
  }, [logout, user]);

  useEffect(() => {
    function syncPath() {
      setPath(window.location.pathname);
    }

    window.addEventListener("popstate", syncPath);
    return () => {
      window.removeEventListener("popstate", syncPath);
    };
  }, []);

  function navigateTo(pathname: string) {
    window.history.pushState({}, "", pathname);
    setPath(pathname);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Reglamento SBS N. 11356-2008</p>
          <h1>Asistente educativo</h1>
        </div>
        <div className="topbar-actions">
          {isTeacher && !isTeacherRoute ? (
            <button
              className="teacher-link-button"
              type="button"
              onClick={() => navigateTo("/teacher")}
            >
              Panel docente
            </button>
          ) : null}
          <div className="session-chip" title={userLabel}>
            <span className="session-email">{userLabel}</span>
            <button
              aria-label="Cerrar sesion"
              className="logout-button"
              type="button"
              onClick={() => void logout()}
            >
              <LogOut aria-hidden="true" size={18} />
              <span>Cerrar sesion</span>
            </button>
          </div>
        </div>
      </header>

      {isTeacherRoute ? (
        <TeacherDashboard onBack={() => navigateTo("/")} />
      ) : (
        <AssistantChat userKey={user?.uid ?? user?.email ?? "local-user"} />
      )}
    </main>
  );
}
