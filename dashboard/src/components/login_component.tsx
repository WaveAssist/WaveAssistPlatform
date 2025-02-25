import React, { useEffect, useState } from "react";
import "./login_component.css";
import WALogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import { useLocation, useNavigate } from "react-router-dom";
import { auth, googleProvider, xProvider } from "../components/firebase";
import { signInWithPopup, signInWithRedirect, getRedirectResult } from "firebase/auth";
import { loginAPI } from "../services/login_services";

import Button from "react-bootstrap/Button";
import Modal from "react-bootstrap/Modal";

const LoginComponent: React.FC = () => {
	const navigate = useNavigate();
	const location = useLocation();
	const [showGetStarted, setShowGetStarted] = useState(false);
	const handleClose = () => setShowGetStarted(false);
	const handleShow = () => setShowGetStarted(true);

	useEffect(() => {
		const uid = localStorage.getItem("uid");
		if (uid) {
			navigate("/manage");
		}
	}, []);

	const handleSuccessfulSignIn = async (user: any) => {
		try {
			localStorage.setItem("user_data", JSON.stringify(user));
			console.log(user);
			console.log("Login successful! Redirecting to /manage");
			var firebase_token = user.accessToken;
			const data = await loginAPI(firebase_token);
			//Check if data has key action
			if (data.action === "PERFORM_GET_STARTED") {
				handleShow();
				return;
			} else {
				localStorage.setItem("user_data", JSON.stringify(data.user_data));
				localStorage.setItem("project_array", JSON.stringify(data.project_array));
				localStorage.setItem("uid", data.user_data.uid);
				//Get from location state
				const from_location = location.state as any;
				if (from_location) {
					navigate(from_location.from);
				} else {
					navigate("/manage");
				}
			}
		} catch (error) {
			console.error("Login failed:", error);
			alert("Login failed. Please check your username and password.");
		}
	};

	const handleGetStarted = async () => {
		return;
	};

	const handleGoogleSignIn = async () => {
		try {
			const result = await signInWithPopup(auth, googleProvider);
			handleSuccessfulSignIn(result.user);
		} catch (error: any) {
			if (error.code === "auth/popup-blocked") {
				console.log("Popup blocked, trying redirect...");
				try {
					await signInWithRedirect(auth, googleProvider);
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

	const handleXSignIn = async () => {
		try {
			// Attempt sign-in with popup
			const result = await signInWithPopup(auth, xProvider);
			handleSuccessfulSignIn(result.user);
		} catch (error: any) {
			if (error.code === "auth/invalid-credential") {
				console.error("Invalid credentials. Please check your API keys and secrets.");
				alert("Authentication failed. Please try again or contact support.");
			} else if (error.code === "auth/popup-blocked") {
				console.log("Popup blocked, trying redirect...");
				try {
					// Attempt sign-in with redirect
					await signInWithRedirect(auth, xProvider);
					const result = await getRedirectResult(auth);
					if (result) {
						handleSuccessfulSignIn(result.user);
					} else {
						console.error("No redirect result");
						alert("X sign-in failed. Please try again.");
					}
				} catch (redirectError: any) {
					console.error("X sign-in redirect failed:", redirectError);
					if (redirectError.code === "auth/invalid-credential") {
						alert("Authentication failed. Please check your X account settings.");
					} else {
						alert("X sign-in failed. Please check your browser settings and try again.");
					}
				}
			} else if (error.code === "auth/cancelled-popup-request") {
				console.log("Authentication cancelled by user");
				// No need to show an alert as this is a user action
			} else if (error.code === "auth/account-exists-with-different-credential") {
				alert("An account already exists with the same email address but different sign-in credentials. Try signing in using a different method.");
			} else {
				console.error("X sign-in failed:", error);
				alert(`X sign-in failed: ${error.message}. Please try again.`);
			}
		}
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
					<button onClick={handleXSignIn} className="btn btn-dark w-100 mb-3">
						<i className="bi bi-twitter-x me-2"></i> Sign in with X
					</button>
				</div>
			</div>

			<Modal show={showGetStarted} onHide={handleClose}>
				<Modal.Header closeButton>
					<Modal.Title className="modal-title">Create new account</Modal.Title>
				</Modal.Header>
				<Modal.Body>Your account does not exist with WaveAssist, Would you like to create a new account?</Modal.Body>
				<Modal.Footer>
					<Button variant="secondary" onClick={handleClose}>
						Close
					</Button>
					<Button variant="primary" onClick={handleGetStarted}>
						Create
					</Button>
				</Modal.Footer>
			</Modal>
		</div>
	);
};

export default LoginComponent;
