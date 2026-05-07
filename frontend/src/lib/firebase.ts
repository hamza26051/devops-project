import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyDqy58Jd8T9dvR7A825EqdrYzAm3L9EHuU",
  authDomain: "devops-82448.firebaseapp.com",
  projectId: "devops-82448",
  storageBucket: "devops-82448.firebasestorage.app",
  messagingSenderId: "762267427584",
  appId: "1:762267427584:web:81ae6a0224294c078f49e5",
  measurementId: "G-96PPXWM9TG",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
