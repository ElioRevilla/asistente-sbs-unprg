import { useEffect } from "react";
import { LogOut } from "lucide-react";

import { useAuthStore } from "../features/auth/authStore";
import { AssistantChat } from "../features/chat/AssistantChat";

const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;
const ACTIVITY_EVENTS = ["click", "keydown", "mousemove", "scroll", "touchstart"];

export function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const userLabel = user?.email ?? user?.uid ?? "";

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

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Reglamento SBS N. 11356-2008</p>
          <h1>Asistente educativo</h1>
        </div>
        <div className="session-chip" title={userLabel}>
          <span className="session-email">{userLabel}</span>
          <button
            aria-label="Cerrar sesión"
            className="logout-button"
            type="button"
            onClick={() => void logout()}
          >
            <LogOut aria-hidden="true" size={18} />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </header>

      <AssistantChat userKey={user?.uid ?? user?.email ?? "local-user"} />
    </main>
  );
}
