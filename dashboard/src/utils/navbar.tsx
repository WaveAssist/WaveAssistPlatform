import React, { useState } from "react";
import { Navbar, Nav, NavDropdown, Button } from "react-bootstrap";
import "./navbar.css";

const NavbarComponent: React.FC = () => {
  const [selectedProject, setSelectedProject] = useState(() => {
    return localStorage.getItem("selected_project_key") || "Project 1";
  });

  const handleProjectChange = (project_key: string) => {
    setSelectedProject(project_key);
    localStorage.setItem("selected_project_key", project_key);
  };

  //Fetch the projectsArray from localStorage and convert it to an array
  const projectsArray = JSON.parse(
    localStorage.getItem("projects_array") || "[]"
  );

  return (
    <Navbar variant="dark" expand="lg" className="px-3 navbar-main">
      <Navbar.Toggle aria-controls="navbar-nav" />
      <Navbar.Collapse id="navbar-nav">
        <Nav className="me-auto">
          <NavDropdown
            title={selectedProject}
            id="project-selector"
            className="btn btn-outline-secondary custom-dropdown"
          >
            {projectsArray.map((project: any) => (
              <NavDropdown.Item
                key={project.project_key}
                onClick={() => handleProjectChange(project.project_key)}
              >
                {project.name} - {project.project_key}
              </NavDropdown.Item>
            ))}
          </NavDropdown>
        </Nav>
        <Nav className="ms-auto">
          <NavDropdown title="Environment Selector" id="environment-selector">
            <NavDropdown.Item href="#">Development</NavDropdown.Item>
            <NavDropdown.Item href="#">Production</NavDropdown.Item>
          </NavDropdown>
          <NavDropdown
            title="Build Version Selector"
            id="build-version-selector"
          >
            <NavDropdown.Item href="#">v1.0.0</NavDropdown.Item>
            <NavDropdown.Item href="#">v2.0.0</NavDropdown.Item>
          </NavDropdown>
          <Button variant="success" className="mx-2">
            Run
          </Button>
        </Nav>
      </Navbar.Collapse>
    </Navbar>
  );
};

export default NavbarComponent;
