import React, { useEffect, useState } from "react";
import "./login_component.css";
import WALogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import { loginAPI } from "../services/login_services";
import { useNavigate, useLocation } from "react-router-dom";

const LoginComponent: React.FC = () => {
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const navigate = useNavigate();
	const location = useLocation();

	useEffect(() => {
		const uid = localStorage.getItem("uid");
		if (uid) {
			navigate("/manage");
		}
	}, []);

	const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		try {
			const data = await loginAPI(username, password);
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
		} catch (error) {
			console.error("Login failed:", error);
			alert("Login failed. Please check your username and password.");
		}
	};

	// Function to show the password showPassword
	const showPassword = () => {
		var x = document.getElementById("password");
		if (x!.getAttribute("type") === "password") {
			x!.setAttribute("type", "text");
		} else {
			x!.setAttribute("type", "password");
		}
	};

	return (
		<div className="container vh-100 d-flex flex-column justify-content-center">
			<div className="row">
				<div className="col text-center mb-3" style={{ marginTop: "-20vh" }}>
					<img src={WALogo} alt="WavePredict Logo" className="img-fluid mb-4 wp_logo" />
					<h2 className="title-message">WaveAssist Management Console</h2>
				</div>
			</div>

			<div className="row justify-content-center">
				<div className="col-8 col-md-5 col-lg-3 text-center">
					<form onSubmit={handleSubmit}>
						<div className="form-group mb-3">
							<input
								type="text"
								className="form-control"
								id="username"
								value={username}
								onChange={(e) => setUsername(e.target.value)}
								placeholder="Username"
								data-bs-theme="dark"
							/>
						</div>
						<div className="form-group mb-3">
							<div className="input-group">
								<input
									type="password"
									className="form-control"
									id="password"
									value={password}
									onChange={(e) => setPassword(e.target.value)}
									placeholder="Password"
									data-bs-theme="dark"
								/>
								<button className="btn btn-outline-secondary" type="button" onClick={showPassword}>
									<i className="bi bi-eye"></i>
								</button>
							</div>
						</div>
						<button type="submit" className="btn btn-success w-50 mt-3">
							Login
						</button>
					</form>
				</div>
			</div>
		</div>
	);
};

export default LoginComponent;
