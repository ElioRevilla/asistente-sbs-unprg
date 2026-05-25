import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { LoginPage } from "../features/auth/LoginPage";
import { useAuthStore } from "../features/auth/authStore";
import { Dashboard } from "./Dashboard";

const queryClient = new QueryClient();

export function App() {
  const user = useAuthStore((state) => state.user);
  const initializing = useAuthStore((state) => state.initializing);

  if (initializing) {
    return <main className="loading-shell">Cargando sesión...</main>;
  }

  return (
    <QueryClientProvider client={queryClient}>
      {user ? <Dashboard /> : <LoginPage />}
    </QueryClientProvider>
  );
}
