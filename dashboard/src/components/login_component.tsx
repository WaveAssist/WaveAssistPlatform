import React from "react";
import "./login_component.css";
import WALogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import { useNavigate } from "react-router-dom";
import { auth, googleProvider } from "../components/firebase";
import { signInWithPopup, signInWithRedirect, getRedirectResult } from "firebase/auth";



const LoginComponent: React.FC = () => {
  const navigate = useNavigate();
  

const handleGoogleSignIn = async () => {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    handleSuccessfulSignIn(result.user);
  } catch (error: any) {
    if (error.code === 'auth/popup-blocked') {
      console.log("Popup blocked, trying redirect...");
      try {
        await signInWithRedirect(auth, googleProvider);
        // The signed-in user info is available in the redirect result
        const result = await getRedirectResult(auth);
        if (result) {
          handleSuccessfulSignIn(result.user);
        }
      } catch (redirectError) {
        console.error("Google sign-in redirect failed:", redirectError);
        alert("Google sign-in failed. Please check your browser settings and try again.");
      }
    } else {
      console.error("Google sign-in failed:", error);
      alert("Google sign-in failed. Please try again.");
    }
  }
};

const handleSuccessfulSignIn = (user: any) => {
  localStorage.setItem("uid", user.uid);
  localStorage.setItem("user_data", JSON.stringify(user));
  // Dummy success navigation
  console.log("Login successful! Redirecting to /manage");
//   alert("Login successful! You would be redirected to /manage");

  // Example: Show user info
  console.log("User Info:", user);
};


  const handleGithubSignIn = () => {
    // Implement GitHub sign-in logic here
  };

  return (
    <div className="container vh-100 d-flex flex-column justify-content-center">
      <div className="row">
        <div className="col text-center mb-3" style={{ marginTop: "-20vh" }}>
          <img src={WALogo} alt="WavePredict Logo" className="img-fluid mb-4 wp_logo_login" />
          <h2 className="title-message">WaveAssist Management Console</h2>
        </div>
      </div>

      <div className="row justify-content-center">
        <div className="col-8 col-md-5 col-lg-3 text-center">
          <button onClick={handleGoogleSignIn} className="btn btn-light w-100 mb-3">
            <i className="bi bi-google me-2"></i> Sign in with Google
          </button>
          <button onClick={handleGithubSignIn} className="btn btn-dark w-100 mb-3">
            <i className="bi bi-github me-2"></i> Sign in with GitHub
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginComponent;
