import { create } from "zustand";
import {
  User,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut
} from "firebase/auth";
import {
  firebaseAuth,
  firebaseConfigError,
  isFirebaseConfigured
} from "../../services/firebase";

type AuthState = {
  error: string | null;
  initializing: boolean;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => {
  if (firebaseAuth) {
    onAuthStateChanged(firebaseAuth, (user) => {
      set({ user, initializing: false });
    });
  }

  return {
    error: firebaseConfigError,
    initializing: isFirebaseConfigured,
    user: null,
    login: async (email, password) => {
      if (!firebaseAuth) {
        set({ error: firebaseConfigError ?? "Firebase Auth no está configurado." });
        return;
      }
      try {
        set({ error: null });
        await signInWithEmailAndPassword(firebaseAuth, email, password);
      } catch {
        set({ error: "Usuario o contraseña incorrectos." });
      }
    },
    logout: async () => {
      if (firebaseAuth) {
        await signOut(firebaseAuth);
      }
      set({ user: null });
    }
  };
});
