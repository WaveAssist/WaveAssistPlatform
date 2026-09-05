import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, TwitterAuthProvider } from "firebase/auth";
import { getBrand } from "../config/branding";
import { AUTH_MODE } from "../config/runtime";

// Firebase client settings are public, but deployment-specific; supply them at build time.
const configs = {
    waveassist: import.meta.env.VITE_WAVEASSIST_FIREBASE_CONFIG,
    gitzoid: import.meta.env.VITE_GITZOID_FIREBASE_CONFIG,
};
const firebaseEnabled = AUTH_MODE === "firebase";
const raw = configs[getBrand().id];
if (firebaseEnabled && !raw) throw new Error("Set the Firebase configuration for the selected dashboard brand.");
const config = firebaseEnabled ? JSON.parse(raw) : { apiKey: "local-disabled", projectId: "waveassist-local" };
const app = initializeApp(config, firebaseEnabled ? undefined : "waveassist-local");
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export const xProvider = new TwitterAuthProvider();
