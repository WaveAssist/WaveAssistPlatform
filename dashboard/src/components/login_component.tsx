import React, { useEffect, useState } from "react";
import "./login_component.css";
import WALogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import { useLocation, useNavigate } from "react-router-dom";
import { auth, googleProvider, xProvider } from "../components/firebase";
import { signInWithPopup, signInWithRedirect, getRedirectResult } from "firebase/auth";
import { loginAPI, getStartedAPI } from "../services/login_services";
import { Spinner } from "react-bootstrap"; // Assuming you're using Bootstrap

import Button from "react-bootstrap/Button";
import Modal from "react-bootstrap/Modal";

const LoginComponent: React.FC = () => {
	const navigate = useNavigate();
	const location = useLocation();
	const [showGetStarted, setShowGetStarted] = useState(false);
	const handleClose = () => setShowGetStarted(false);
	const handleShow = () => setShowGetStarted(true);
	const [loading, setLoading] = useState<boolean>(false);
	const [loaderMessage, setLoaderMessage] = useState("");

	useEffect(() => {
		const uid = localStorage.getItem("uid");
		if (uid) {
			navigate("/manage");
		}
	}, []);

	const handleSuccessfulSignIn = async (user: any) => {
		try {
			setLoading(true);
			localStorage.setItem("user_data", JSON.stringify(user));
			console.log(user);
			console.log("Login successful! Redirecting to /manage");
			var firebase_token = user.accessToken;
			localStorage.setItem("firebase_uid", firebase_token);
			const data = await loginAPI(firebase_token);
			setLoading(false);
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
		try {
			setLoading(true);
			setLoaderMessage("Setting up your account, this may take a minute..");
			handleClose();
			var firebase_uid = localStorage.getItem("firebase_uid");
			const data = await getStartedAPI(firebase_uid);
			localStorage.setItem("user_data", JSON.stringify(data.user_data));
			localStorage.setItem("project_array", JSON.stringify(data.project_array));
			localStorage.setItem("uid", data.user_data.uid);
			setLoading(false);
			setLoaderMessage("");
			navigate("/manage");
		} catch (error) {
			console.error("Get Started Failed:", error);
			alert("Something went wrong creating your account, please try again..");
		}
	};

	const handleGoogleSignIn = async () => {
		try {
			setLoading(true);
			const result = await signInWithPopup(auth, googleProvider);
			handleSuccessfulSignIn(result.user);
		} catch (error: any) {
			setLoading(false);
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
			setLoading(true);
			// Attempt sign-in with popup
			const result = await signInWithPopup(auth, xProvider);
			handleSuccessfulSignIn(result.user);
			setLoading(false);
		} catch (error: any) {
			setLoading(false);
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

			{loading ? (
				<div className="loader-container d-flex justify-content-center align-items-center pb-4">
					<div className="text-center">
						<Spinner animation="border" role="status" variant="success">
							<span className="visually-hidden">Loading...</span>
						</Spinner>
						<p className="mt-2 text-success">{loaderMessage}</p>
					</div>
				</div>
			) : (
				<div></div>
			)}

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
					<Modal.Title className="modal-title">Setup your account</Modal.Title>
				</Modal.Header>
				<Modal.Body>Your account does not exist with WaveAssist, or was not fully configured. Would you like to setup you account?</Modal.Body>
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
