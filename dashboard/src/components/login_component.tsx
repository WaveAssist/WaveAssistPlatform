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

// Safari detection utility
const isSafari = () => {
	const userAgent = navigator.userAgent.toLowerCase();
	// More comprehensive Safari detection including iOS Safari
	return (
		(userAgent.includes("safari") && !userAgent.includes("chrome")) ||
		userAgent.includes("iphone") ||
		userAgent.includes("ipad") ||
		userAgent.includes("ipod")
	);
};

// Get the current domain for Safari compatibility
const getCurrentDomain = () => {
	// For Safari, we need to be more explicit about the domain
	if (isSafari()) {
		// Use the full origin including protocol
		return window.location.origin;
	}
	return window.location.origin;
};

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
					// Navigate to the stored redirect URL which should preserve all parameters
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
				// Navigate to the stored redirect URL which should preserve all parameters
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

		// Prepare search parameters with redirect and email
		const searchParams = new URLSearchParams(window.location.search);
		const storedRedirect = localStorage.getItem("postLoginRedirect");
		if (storedRedirect) {
			searchParams.set("redirect", storedRedirect);
		}
		// Add email as URL parameter for better cross-browser compatibility
		searchParams.set("email", encodeURIComponent(email));
		const searchParamsString = searchParams.toString();
		const finalSearchParams = searchParamsString ? `?${searchParamsString}` : "";

		try {
			setLoading(true);
			setEmailError(null);

			const currentDomain = getCurrentDomain();

			// Safari-specific configuration for email link settings
			const actionCodeSettings = {
				url: `${currentDomain}/finish-signin${finalSearchParams}`,
				handleCodeInApp: true,
				// Safari-specific settings to ensure compatibility
				...(isSafari() && {
					// Use a more explicit URL format for Safari
					url: `${window.location.protocol}//${window.location.host}/finish-signin${finalSearchParams}`,
				}),
			};

			console.log("Action code settings:", actionCodeSettings);

			// Send the sign-in link with Safari-specific error handling
			await sendSignInLinkToEmail(auth, email, actionCodeSettings);

			setEmailSent(true);
			setLoading(false);

			// ✅ Fire GA4 event for email link sent
			ReactGA.event("email_link_sent", {
				method: "WaveAssist",
			});
		} catch (error: any) {
			console.error("Email sign-in failed:", error);
			console.error("Error code:", error.code);
			console.error("Error message:", error.message);

			// Safari-specific error handling with multiple fallback strategies
			if (isSafari()) {
				console.log("Attempting Safari fallback strategies...");

				// Try multiple fallback strategies for Safari
				const fallbackStrategies = [
					// Strategy 1: Simplified settings with current domain
					{
						url: `${getCurrentDomain()}/finish-signin${finalSearchParams}`,
						handleCodeInApp: true,
					},
					// Strategy 2: Absolute URL with search params
					{
						url: `${getCurrentDomain()}/finish-signin${finalSearchParams}`,
						handleCodeInApp: true,
					},
					// Strategy 3: Protocol-relative URL
					{
						url: `//${window.location.host}/finish-signin${finalSearchParams}`,
						handleCodeInApp: true,
					},
					// Strategy 4: Full URL with protocol
					{
						url: `${window.location.protocol}//${window.location.host}/finish-signin${finalSearchParams}`,
						handleCodeInApp: true,
					},
					// Strategy 5: Minimal settings with search params
					{
						url: `${window.location.origin}/finish-signin${finalSearchParams}`,
						handleCodeInApp: true,
					},
				];

				for (let i = 0; i < fallbackStrategies.length; i++) {
					try {
						console.log(`Trying Safari fallback strategy ${i + 1}:`, fallbackStrategies[i]);
						await sendSignInLinkToEmail(auth, email, fallbackStrategies[i]);
						setEmailSent(true);
						setLoading(false);

						console.log(`Safari fallback strategy ${i + 1} succeeded!`);

						ReactGA.event("email_link_sent", {
							method: "WaveAssist",
						});
						return;
					} catch (retryError: any) {
						console.error(`Safari fallback strategy ${i + 1} failed:`, retryError);
						console.error(`Retry error code:`, retryError.code);
						console.error(`Retry error message:`, retryError.message);

						if (i === fallbackStrategies.length - 1) {
							// All fallback strategies failed
							console.error("All Safari fallback strategies failed");
						}
					}
				}
			}

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
