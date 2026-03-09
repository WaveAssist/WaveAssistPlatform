import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, TwitterAuthProvider } from "firebase/auth";

const firebaseConfig = {
	apiKey: "REMOVED_CREDENTIAL",
	authDomain: "app.waveassist.io",
	projectId: "waveassistdashboard",
	storageBucket: "waveassistdashboard.firebasestorage.app",
	messagingSenderId: "754862556966",
	appId: "1:754862556966:web:559a10830e1170adf363e7",
	measurementId: "G-914HXG50T6",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export const xProvider = new TwitterAuthProvider();
