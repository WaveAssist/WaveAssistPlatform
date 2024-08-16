// src/App.tsx
import "./index.css";
import AllProjectsComponent from "./components/all_projects_component";
import LoginComponent from "./components/login_component";
import { BrowserRouter as Router } from "react-router-dom";
import { Routes, Route } from "react-router-dom";
import PrivateRoute from "./utils/private_route";
import NodesComponent from "./components/project/nodes_component";
import VariablesComponent from "./components/project/variables_component";
import EnvironmentsComponent from "./components/project/environments_component";
import Layout from "./utils/layout_sidebar";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import "bootstrap-icons/font/bootstrap-icons.css";
import DataViewComponent from "./components/data_view_component";
import "./App.css";
import DeploymentsComponent from "./components/project/deployments_component";
function App() {
	return (
		<Router>
			<div>
				<section>
					<Routes>
						<Route path="/login" element={<LoginComponent />} />
						<Route path="/" element={<PrivateRoute component={AllProjectsComponent} />} />
						<Route path="/manage" element={<PrivateRoute component={AllProjectsComponent} />} />
						<Route path="/manage/projects" element={<PrivateRoute component={AllProjectsComponent} />} />
						<Route path="/manage/nodes" element={<PrivateRoute component={NodesComponent} layout={Layout} />} />
						<Route path="/manage/variables" element={<PrivateRoute component={VariablesComponent} layout={Layout} />} />
						<Route path="/manage/environments" element={<PrivateRoute component={EnvironmentsComponent} layout={Layout} />} />
						<Route path="/manage/deployments" element={<PrivateRoute component={DeploymentsComponent} layout={Layout} />} />
						<Route path="/manage/data-view" element={<PrivateRoute component={DataViewComponent} layout={Layout} />} />
					</Routes>
				</section>
			</div>
		</Router>
	);
}

export default App;
