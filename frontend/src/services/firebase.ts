import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

const missingConfig = Object.entries(firebaseConfig)
  .filter(([key]) => key !== "appId")
  .filter(([, value]) => !value)
  .map(([key]) => key);

export const isFirebaseConfigured = missingConfig.length === 0;
export const firebaseConfigError = missingConfig.length
  ? `Faltan variables Firebase: ${missingConfig.join(", ")}.`
  : null;

export const firebaseApp = isFirebaseConfigured
  ? initializeApp(firebaseConfig)
  : null;

export const firebaseAuth = firebaseApp ? getAuth(firebaseApp) : null;
