import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, TwitterAuthProvider } from "firebase/auth";
import { getBrand } from "../config/branding";

// Firebase web config per brand. These are PUBLIC client keys (safe to ship in the bundle),
// so we hardcode them keyed by brand — the build only needs VITE_BRAND, nothing else.
const FIREBASE_CONFIGS = {
	waveassist: {
		apiKey: "REMOVED_CREDENTIAL",
		authDomain: "app.waveassist.io",
		projectId: "waveassistdashboard",
		storageBucket: "waveassistdashboard.firebasestorage.app",
		messagingSenderId: "754862556966",
		appId: "1:754862556966:web:559a10830e1170adf363e7",
		measurementId: "G-914HXG50T6",
	},
	gitzoid: {
		apiKey: "REMOVED_CREDENTIAL",
		authDomain: "app.gitzoid.com",
		projectId: "gitzoid-dashboard",
		storageBucket: "gitzoid-dashboard.firebasestorage.app",
		messagingSenderId: "785810865022",
		appId: "1:785810865022:web:f9af2710761f839a9ed12f",
		measurementId: "G-9BBL3KD4DV",
	},
} as const;

const firebaseConfig = FIREBASE_CONFIGS[getBrand().id] ?? FIREBASE_CONFIGS.waveassist;

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export const xProvider = new TwitterAuthProvider();
