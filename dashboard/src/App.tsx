// src/App.tsx
import "./index.css";
import AllProjectsComponent from "./components/all_projects_component";
import LoginComponent from "./components/login_component";
import FinishSignInComponent from "./components/finish_signin_component";
import { BrowserRouter as Router } from "react-router-dom";
import { Routes, Route } from "react-router-dom";
import PrivateRoute from "./utils/private_route";
import NodesComponent from "./components/project/nodes_component";
import VariablesComponent from "./components/project/variables_component";
import PackagesComponent from "./components/project/packages_component";
import EnvironmentsComponent from "./components/project/environments_component";
import RunsComponent from "./components/project/runs_component";
import RunDetailsComponent from "./components/project/run_details_component";
import TestComponent from "./components/test_component";
import Layout from "./utils/layout_sidebar";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import "bootstrap-icons/font/bootstrap-icons.css";
import DataViewComponent from "./components/data_view_component";
import "./App.css";
import DeploymentsComponent from "./components/project/deployments_component";
import LogsComponent from "./components/project/logs_component";
import DeployComponent from "./components/deploy_component";
import CreditsComponent from "./components/project/credits_component";
import AssistantComponent from "./components/assistant_component";
import ReactGA from "react-ga4";
ReactGA.initialize("G-RHQ9VZRVXH");

function App() {
	return (
		<Router>
			<div>
				<section>
					<Routes>
						<Route path="/login" element={<LoginComponent />} />
						<Route path="/finish-signin" element={<FinishSignInComponent />} />
						<Route path="/test" element={<TestComponent />} />
						<Route path="/" element={<PrivateRoute component={AllProjectsComponent} />} />
						<Route path="/manage" element={<PrivateRoute component={AllProjectsComponent} />} />
						<Route path="/manage/projects" element={<PrivateRoute component={AllProjectsComponent} />} />
						<Route path="/manage/assistant" element={<PrivateRoute component={AssistantComponent} layout={Layout} />} />
						<Route path="/manage/nodes" element={<PrivateRoute component={NodesComponent} layout={Layout} />} />
						<Route path="/manage/variables" element={<PrivateRoute component={VariablesComponent} layout={Layout} />} />
						<Route path="/manage/packages" element={<PrivateRoute component={PackagesComponent} layout={Layout} />} />
						<Route path="/manage/environments" element={<PrivateRoute component={EnvironmentsComponent} layout={Layout} />} />
						<Route path="/manage/runs" element={<PrivateRoute component={RunsComponent} layout={Layout} />} />
						<Route path="/manage/runs/:runId" element={<PrivateRoute component={RunDetailsComponent} layout={Layout} />} />
						<Route path="/manage/credits" element={<PrivateRoute component={CreditsComponent} layout={Layout} />} />
						<Route path="/manage/deployments" element={<PrivateRoute component={DeploymentsComponent} layout={Layout} />} />
						<Route path="/manage/data-view" element={<PrivateRoute component={DataViewComponent} layout={Layout} />} />
						<Route path="/manage/logs" element={<PrivateRoute component={LogsComponent} layout={Layout} />} />
						<Route path="/deploy" element={<DeployComponent />} />
					</Routes>
				</section>
			</div>
		</Router>
	);
}

export default App;
