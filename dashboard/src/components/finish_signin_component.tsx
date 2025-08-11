import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { auth } from "./firebase";
import { isSignInWithEmailLink, signInWithEmailLink } from "firebase/auth";
import { loginAPI, getStartedAPI } from "../services/login_services";
import { Spinner } from "react-bootstrap";
import ReactGA from "react-ga4";
import WALogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import "./finish_signin_component.css";

const FinishSignInComponent: React.FC = () => {
	const navigate = useNavigate();
	const location = useLocation();
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [email, setEmail] = useState<string>("");

	useEffect(() => {
		const handleEmailLinkSignIn = async () => {
			try {
				// Check if the current URL is a sign-in link
				if (!isSignInWithEmailLink(auth, window.location.href)) {
					setError("Invalid sign-in link. Please try signing in again.");
					setLoading(false);
					return;
				}

				// Get the email from localStorage (set during the initial sign-in attempt)
				const emailForSignIn = localStorage.getItem("emailForSignIn");
				if (!emailForSignIn) {
					setError("Email not found. Please try signing in again.");
					setLoading(false);
					return;
				}

				setEmail(emailForSignIn);

				// Complete the sign-in process
				const result = await signInWithEmailLink(auth, emailForSignIn, window.location.href);

				// Clear the email from localStorage
				localStorage.removeItem("emailForSignIn");

				// Handle successful sign-in using existing logic
				await handleSuccessfulSignIn(result.user);
			} catch (error: any) {
				console.error("Email link sign-in failed:", error);
				setError("Sign-in failed. Please try again.");
				setLoading(false);
			}
		};

		handleEmailLinkSignIn();
	}, [navigate]);

	const handleSuccessfulSignIn = async (user: any) => {
		try {
			setLoading(true);
			localStorage.setItem("user_data", JSON.stringify(user));
			var firebase_token = user.accessToken;
			localStorage.setItem("firebase_uid", firebase_token);

			// Get URL parameters
			const searchParams = new URLSearchParams(location.search);
			const session_id = searchParams.get("session_id");
			const redirect = searchParams.get("redirect") || "/manage";
			const isCLILogin = !!session_id;
			const is_test = false;

			// 🌐 Standard login API flow
			const data = await loginAPI(firebase_token, session_id);
			setLoading(false);

			// ✅ Fire GA4 sign_up event
			ReactGA.event("login", {
				method: "Email Link",
			});

			if (data.action === "PERFORM_GET_STARTED" || is_test) {
				await handleGetStarted();
				return;
			} else {
				localStorage.setItem("user_data", JSON.stringify(data.user_data));
				localStorage.setItem("projects_array", JSON.stringify(data.project_array));
				localStorage.setItem("uid", data.user_data.uid);
				localStorage.setItem("is_premium", data.user_data.is_premium ? "true" : "false");
				const storedRedirect = localStorage.getItem("postLoginRedirect");
				if (isCLILogin) {
					// Handle CLI login completion
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
			setError("Login failed. Please try again.");
			setLoading(false);
		}
	};

	const handleGetStarted = async () => {
		try {
			setLoading(true);
			const searchParams = new URLSearchParams(location.search);
			const session_id = searchParams.get("session_id");
			const redirect = searchParams.get("redirect") || "/manage";
			const isCLILogin = !!session_id;
			const is_test = false;

			const firebase_uid = localStorage.getItem("firebase_uid");
			const data = await getStartedAPI(firebase_uid, is_test, session_id);
			localStorage.setItem("user_data", JSON.stringify(data.user_data));
			localStorage.setItem("projects_array", JSON.stringify(data.project_array));
			localStorage.setItem("uid", data.user_data.uid);
			localStorage.setItem("is_premium", data.user_data.is_premium ? "true" : "false");

			// ✅ Fire GA4 sign_up event
			ReactGA.event("account_created", {
				method: "Email Link",
			});
			ReactGA.event("conversion_event_purchase", {
				method: "Email Link",
			});

			setLoading(false);
			const storedRedirect = localStorage.getItem("postLoginRedirect");

			if (isCLILogin) {
				// Handle CLI login completion
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
			setError("Something went wrong creating your account, please try again.");
			setLoading(false);
		}
	};

	return (
		<div className="wa-login-page">
			<div className="wa-card">
				<div className="text-center mb-4">
					<img src={WALogo} alt="WaveAssist Logo" className="img-fluid mb-4 wp_logo_login" />
					<h1 className="wa-title">Completing Sign In</h1>
					{email && <p className="title-message">Signing in as {email}</p>}
				</div>

				{loading && (
					<div className="loader-container d-flex justify-content-center align-items-center pb-4">
						<div className="text-center">
							<Spinner animation="border" role="status" variant="success" />
							<p className="mt-2 text-success">Completing your sign-in...</p>
						</div>
					</div>
				)}

				{error && (
					<div className="text-center mt-4">
						<p className="text-danger">{error}</p>
						<button onClick={() => navigate("/login")} className="btn btn-outline-light mt-3">
							Back to Login
						</button>
					</div>
				)}
			</div>
		</div>
	);
};

export default FinishSignInComponent;
