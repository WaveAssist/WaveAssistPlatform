import React, { useEffect, useState } from "react";
import "./login_component.css";
import WALogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import { useLocation, useNavigate } from "react-router-dom";
import { auth, googleProvider } from "../components/firebase";
// import { xProvider } from "../components/firebase";
import { signInWithPopup, signInWithRedirect, getRedirectResult } from "firebase/auth";
import { loginAPI, getStartedAPI } from "../services/login_services";
import { Spinner } from "react-bootstrap";
import ReactGA from "react-ga4";
// import Button from "react-bootstrap/Button";
// import Modal from "react-bootstrap/Modal";

const LoginComponent: React.FC = () => {
	const navigate = useNavigate();
	const location = useLocation();
	const searchParams = new URLSearchParams(location.search);
	const redirect = searchParams.get("redirect") || "/manage";

	const session_id = searchParams.get("session_id");
	const isCLILogin = !!session_id;

	const [cliLoginComplete, setCliLoginComplete] = useState(false);

	const [loading, setLoading] = useState<boolean>(false);
	const [loaderMessage, setLoaderMessage] = useState("");
	const is_test = false; // ALWAYS KEEP as FALSE

	useEffect(() => {
		if (isCLILogin) return; // skip redirect if CLI login
		const uid = localStorage.getItem("uid");
		if (uid) {
			const storedRedirect = localStorage.getItem("postLoginRedirect");
			if (storedRedirect) {
				localStorage.removeItem("postLoginRedirect");
				navigate(storedRedirect);
			} else {
				navigate(redirect);
			}
		}
	}, [navigate, redirect, isCLILogin]);

	const handleSuccessfulSignIn = async (user: any) => {
		try {
			setLoading(true);
			localStorage.setItem("user_data", JSON.stringify(user));
			var firebase_token = user.accessToken;
			localStorage.setItem("firebase_uid", firebase_token);

			// 🌐 Standard login API flow
			const data = await loginAPI(firebase_token, session_id);
			setLoading(false);
			// ✅ Fire GA4 sign_up event
			ReactGA.event("login", {
				method: "WaveAssist",
			});

			if (data.action === "PERFORM_GET_STARTED" || is_test) {
				handleGetStarted();
				return;
			} else {
				localStorage.setItem("user_data", JSON.stringify(data.user_data));
				localStorage.setItem("projects_array", JSON.stringify(data.project_array));
				localStorage.setItem("uid", data.user_data.uid);
				const storedRedirect = localStorage.getItem("postLoginRedirect");
				if (isCLILogin) {
					setCliLoginComplete(true);
					return;
				}
				if (storedRedirect) {
					localStorage.removeItem("postLoginRedirect");
					navigate(storedRedirect);
				} else {
					navigate(redirect);
				}
			}
		} catch (error) {
			console.error("Login failed:", error);
			alert("Login failed. Please check your username and password.");
			setLoading(false);
		}
	};

	const handleGetStarted = async () => {
		try {
			setLoading(true);
			setLoaderMessage("Setting up your account, this may take a minute...");

			const firebase_uid = localStorage.getItem("firebase_uid");
			const data = await getStartedAPI(firebase_uid, is_test, session_id);
			localStorage.setItem("user_data", JSON.stringify(data.user_data));
			localStorage.setItem("projects_array", JSON.stringify(data.project_array));
			localStorage.setItem("uid", data.user_data.uid);

			// ✅ Fire GA4 sign_up event
			ReactGA.event("account_created", {
				method: "WaveAssist",
			});
			ReactGA.event("conversion_event_purchase", {
				method: "WaveAssist",
			});

			setLoading(false);
			setLoaderMessage("");
			const storedRedirect = localStorage.getItem("postLoginRedirect");
			console.log("Stored Redirect:", storedRedirect);
			// If CLI login, just set the flag and return
			if (isCLILogin) {
				setCliLoginComplete(true);
				return;
			}
			if (storedRedirect) {
				localStorage.removeItem("postLoginRedirect");
				navigate(storedRedirect);
			} else {
				navigate(redirect);
			}
		} catch (error) {
			console.error("Get Started Failed:", error);
			alert("Something went wrong creating your account, please try again.");
			setLoading(false);
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
				try {
					await signInWithRedirect(auth, googleProvider);
					const result = await getRedirectResult(auth);
					if (result) handleSuccessfulSignIn(result.user);
				} catch (redirectError) {
					console.error("Google redirect failed:", redirectError);
					alert("Google sign-in failed. Please check your browser settings.");
				}
			} else {
				console.error("Google sign-in failed:", error);
				alert("Google sign-in failed. Please try again.");
			}
		}
	};

	// const handleXSignIn = async () => {
	// 	try {
	// 		setLoading(true);
	// 		const result = await signInWithPopup(auth, xProvider);
	// 		handleSuccessfulSignIn(result.user);
	// 	} catch (error: any) {
	// 		setLoading(false);
	// 		if (error.code === "auth/popup-blocked") {
	// 			try {
	// 				await signInWithRedirect(auth, xProvider);
	// 				const result = await getRedirectResult(auth);
	// 				if (result) handleSuccessfulSignIn(result.user);
	// 			} catch (redirectError: any) {
	// 				console.error("X sign-in redirect failed:", redirectError);
	// 				alert("X sign-in failed. Please check your browser settings.");
	// 			}
	// 		} else {
	// 			console.error("X sign-in failed:", error);
	// 			alert("X sign-in failed. Please try again.");
	// 		}
	// 	}
	// };

	return (
		<div className="wa-login-page">
			<div className="wa-card">
				<div className="text-center mb-4">
					<img src={WALogo} alt="WaveAssist Logo" className="img-fluid mb-4 wp_logo_login" />
					<h1 className="wa-title">Welcome to WaveAssist</h1>
					<p className="title-message">Sign up for free to access your workflows</p>
					{isCLILogin && <p className="title-message">This login flow was initiated from the CLI — complete it here to continue.</p>}
				</div>

				{loading && (
					<div className="loader-container d-flex justify-content-center align-items-center pb-4">
						<div className="text-center">
							<Spinner animation="border" role="status" variant="success" />
							<p className="mt-2 text-success">{loaderMessage}</p>
						</div>
					</div>
				)}

				<div className="login-buttons">
					<button onClick={handleGoogleSignIn} className="btn btn-light w-100 mb-3">
						<i className="bi bi-google me-2"></i> Continue with Google
					</button>
					{/* <button onClick={handleXSignIn} className="btn btn-dark w-100 mb-3">
						<i className="bi bi-twitter-x me-2"></i> Continue with X
					</button> */}
				</div>

				{cliLoginComplete && (
					<div className="text-center mt-4">
						<p className="text-success">✅ Login Successful! You may now return to your terminal.</p>
					</div>
				)}

				{/* <Modal show={showGetStarted} onHide={handleClose}>
					<Modal.Header closeButton>
						<Modal.Title className="modal-title">Setup your account</Modal.Title>
					</Modal.Header>
					<Modal.Body>Your account does not exist with WaveAssist, or was not fully configured. Would you like to setup your account?</Modal.Body>
					<Modal.Footer>
						<Button variant="secondary" onClick={handleClose}>
							Close
						</Button>
						<Button variant="primary" onClick={handleGetStarted}>
							Create
						</Button>
					</Modal.Footer>
				</Modal> */}
			</div>
		</div>
	);
};

export default LoginComponent;
