import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, TwitterAuthProvider} from "firebase/auth";

const firebaseConfig = {
    apiKey: "REMOVED_CREDENTIAL",
    authDomain: "waveassist-e45f3.firebaseapp.com",
    projectId: "waveassist-e45f3",
    storageBucket: "waveassist-e45f3.firebasestorage.app",
    messagingSenderId: "715748590169",
    appId: "1:715748590169:web:02c5e1ebb0c42e024be748",
    measurementId: "G-RHQ9VZRVXH"
  };

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export const xProvider = new TwitterAuthProvider();