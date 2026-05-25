import { LogOut } from "lucide-react";

import { useAuthStore } from "../features/auth/authStore";
import { AssistantChat } from "../features/chat/AssistantChat";

export function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Reglamento SBS N. 11356-2008</p>
          <h1>Asistente educativo</h1>
        </div>
        <div className="session-chip">
          <span>{user?.email ?? user?.uid}</span>
          <button
            aria-label="Cerrar sesión"
            type="button"
            onClick={() => void logout()}
          >
            <LogOut aria-hidden="true" size={18} />
          </button>
        </div>
      </header>

      <AssistantChat />
    </main>
  );
}
