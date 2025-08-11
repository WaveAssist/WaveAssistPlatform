import React, { useEffect, useState } from "react";
import "./login_component.css";
import WALogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import { useLocation, useNavigate } from "react-router-dom";
import { auth, googleProvider } from "../components/firebase";
// import { xProvider } from "../components/firebase";
import { signInWithPopup, signInWithRedirect, getRedirectResult, sendSignInLinkToEmail } from "firebase/auth";
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
	const uid = searchParams.get("uid");
	const isCLILogin = !!session_id;

	const [cliLoginComplete, setCliLoginComplete] = useState(false);

	const [loading, setLoading] = useState<boolean>(false);
	const [loaderMessage, setLoaderMessage] = useState("");
	const [email, setEmail] = useState<string>("");
	const [emailSent, setEmailSent] = useState<boolean>(false);
	const [emailError, setEmailError] = useState<string | null>(null);
	const is_test = false; // ALWAYS KEEP as FALSE

	useEffect(() => {
		// Handle uid parameter from URL
		if (uid) {
			localStorage.setItem("uid", uid);
			const storedRedirect = localStorage.getItem("postLoginRedirect");
			if (storedRedirect) {
				localStorage.removeItem("postLoginRedirect");
				navigate(storedRedirect);
			} else {
				navigate(redirect);
			}
			return;
		}

		if (isCLILogin) return; // skip redirect if CLI login
		const storedUid = localStorage.getItem("uid");
		if (storedUid) {
			const storedRedirect = localStorage.getItem("postLoginRedirect");
			if (storedRedirect) {
				localStorage.removeItem("postLoginRedirect");
				navigate(storedRedirect);
			} else {
				navigate(redirect);
			}
		}
	}, [navigate, redirect, isCLILogin, uid]);

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
				localStorage.setItem("is_premium", data.user_data.is_premium ? "true" : "false");
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
			localStorage.setItem("is_premium", data.user_data.is_premium ? "true" : "false");

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

	const handleEmailSignIn = async () => {
		if (!email || !email.trim()) {
			setEmailError("Please enter a valid email address");
			return;
		}

		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!emailRegex.test(email)) {
			setEmailError("Please enter a valid email address");
			return;
		}

		try {
			setLoading(true);
			setEmailError(null);

			// Configure email link settings
			const actionCodeSettings = {
				url: `${window.location.origin}/finish-signin${window.location.search}`,
				handleCodeInApp: true,
			};

			// Send the sign-in link
			await sendSignInLinkToEmail(auth, email, actionCodeSettings);

			// Save the email for later use
			localStorage.setItem("emailForSignIn", email);

			setEmailSent(true);
			setLoading(false);

			// ✅ Fire GA4 event for email link sent
			ReactGA.event("email_link_sent", {
				method: "WaveAssist",
			});
		} catch (error: any) {
			console.error("Email sign-in failed:", error);
			setEmailError("Failed to send sign-in link. Please try again.");
			setLoading(false);
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

				{!emailSent ? (
					<>
						<div className="email-input-container mb-3">
							<input
								type="email"
								className={`form-control ${emailError ? "is-invalid" : ""}`}
								placeholder="Enter your email address"
								value={email}
								onChange={(e) => {
									setEmail(e.target.value);
									if (emailError) setEmailError(null);
								}}
								onKeyPress={(e) => {
									if (e.key === "Enter") {
										handleEmailSignIn();
									}
								}}
							/>
							{emailError && <div className="invalid-feedback">{emailError}</div>}
						</div>

						<div className="login-buttons">
							<button onClick={handleEmailSignIn} className="btn btn-primary w-100 mb-3" disabled={loading}>
								<i className="bi bi-envelope me-2"></i> Continue with Email
							</button>

							<div className="divider-container">
								<div className="divider"></div>
								<span className="divider-text">or</span>
								<div className="divider"></div>
							</div>

							<button onClick={handleGoogleSignIn} className="btn btn-light w-100 mb-3" disabled={loading}>
								<i className="bi bi-google me-2"></i> Continue with Google
							</button>
							{/* <button onClick={handleXSignIn} className="btn btn-dark w-100 mb-3">
								<i className="bi bi-twitter-x me-2"></i> Continue with X
							</button> */}
						</div>
					</>
				) : (
					<div className="email-sent-container text-center">
						<div className="email-sent-icon mb-3">
							<i className="bi bi-envelope-check text-success" style={{ fontSize: "3rem" }}></i>
						</div>
						<h4 className="text-success mb-3">Check your email!</h4>
						<p className="text-muted mb-3">
							We've sent a sign-in link to <strong>{email}</strong>
						</p>
						<p className="text-muted small mb-4">Click the link in your email to complete the sign-in.</p>
						<button
							onClick={() => {
								setEmailSent(false);
								setEmail("");
								setEmailError(null);
							}}
							className="btn btn-outline-light">
							Try a different email
						</button>
					</div>
				)}

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
