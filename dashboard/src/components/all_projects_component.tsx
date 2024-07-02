import React, { useEffect, useState } from 'react';

import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import Alert from 'react-bootstrap/Alert';
import axios from 'axios';
import GreenLogo from '../assets/Logo/GreenLogo_Full_white_no_w.png';
import './all_projects_component.css'; // Import the CSS file

import { useNavigate } from 'react-router-dom';
import { fetchAllProjectsAPI, createProjectAPI, deleteProjectApi } from '../services/all_projects_services';
import AutoDismissToast from '../utils/toast_component';
import { useToast } from '../utils/toast_context';



const AllProjectsComponent: React.FC = () => {
  const [newProjectName, setNewProjectName] = useState('');
  const [showAlert, setShowAlert] = useState(false);
  const [projectArray, setProjectArray] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const navigate = useNavigate();
  const { showToast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
    const data = await fetchAllProjectsAPI();
    setProjectArray(data.project_array);
    }
   catch (error) {
    console.error('FetchAllProjects failed:', error);
    showToast('Something went wrong with loading projects, please try again.', 'danger');
  }
};

  const handleLogout = async () => {
    try {
      // Add your sign-out logic here
      localStorage.removeItem('uid');
      localStorage.removeItem('project_array');
      localStorage.removeItem('selected_project_key');
      localStorage.removeItem('user_data');
      navigate('/login');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };


  const handleOpenModal = () => {
    setShowAlert(false);
    setNewProjectName('');
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
  };


  const handleDeleteProject = async (projectKey: string) => {
    //Show bootstrap alert to ask for confirmation
    const confirmDelete = window.confirm("Are you sure you want to delete this project? This action cannot be undone and will also delete all associated nodes and data. Do you want to proceed?");
    if (!confirmDelete) {
      return;
    }

    try {
      await deleteProjectApi(projectKey);
      showToast('Project deleted successfully', 'success');
      fetchData();      
    }
     catch (error) {
      console.error('Project Deletetion Failed:', error);
      var error_message = 'Something went wrong deleting the project: ' + error;
      showToast(error_message, 'danger');
    }
    
  }


  const handleCreateProject = async () => {
    try {
      await createProjectAPI(newProjectName);
      showToast('Project created successfully', 'success');
      setShowAlert(false);
      handleCloseModal();
      fetchData();      
    }
     catch (error) {
      console.error('FetchAllProjects failed:', error);
      var error_message = 'Something went wrong creating the project: ' + error;
      showToast(error_message, 'danger');
    }
  };


  const handleViewDetails = (projectKey: string) => {
    navigate(`/manage/nodes?project_key=${projectKey}`);
  };

  return (

    <div className="base_component">
      <div className="dashboard-header row">
        <div className="col-md-8">
                   <img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
        </div>
        <div className="col-md-4 d-flex justify-content-end fixed-right align-items-center">
          <button className="btn btn-outline-secondary logout_button" onClick={handleLogout}>Logout</button>
        </div>
      </div>

      <div className="separator"></div>

      <div className="admin-panel">
        <div className="content projects-row">
          <div className="header">
            <h2 className="admin-title mb-3">All Projects</h2>
          </div>

          <div className="row ">

            <div className="col-sm-4 project-card  " onClick={handleOpenModal}>
              <div className="card text-white bg-dark mb-3 add-project-card">
                <div className="card-body d-flex align-items-center justify-content-center">
                  <div className="text-center">
                    <i className="bi bi-plus-lg add-icon translucent_white"></i>
                    <p className="add-text translucent_white">Add Project</p>
                  </div>
                </div>
              </div>
            </div>
            {projectArray.map((project:any) => (
              <div className="col-sm-4 project-card ml-5" key={project.project_key} onClick={() => handleViewDetails(project.project_key)}>
                <div className="card text-white bg-dark mb-3 ml-5 mr-5">
                  <div className="card-body position-relative">
                    <h5 className="card-title translucent_white">{project.project_key}</h5>
                    
                    <button className="btn btn-dark delete-icon translucent_white" onClick={(e) => {e.stopPropagation(); handleDeleteProject(project.project_key);}}>
  <i className="bi bi-trash-fill"></i>
</button>
                    </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal show={showModal} onHide={handleCloseModal}>
        <Modal.Header closeButton>
          <Modal.Title className="modal-title">Add New Project</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="mb-3">
            <label htmlFor="projectNameInput" className="form-label">Project Key</label>
            <input type="text" className="form-control" id="projectNameInput" value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} />
            <div id="projectNameHelp" className="form-text model-text">This has to be unique, lower case & without spaces</div>
            {showAlert && <Alert variant="danger">Could not create the project, try a different name.</Alert>}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseModal}>Close</Button>
          <Button variant="primary" onClick={handleCreateProject}>Create</Button>
        </Modal.Footer>
      </Modal>
    </div>









//     <div className="base_component">
//       <div className="dashboard-header row">
//         <div className="col-md-8">
//           <img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
//         </div>
//         <div className="col-md-4 d-flex justify-content-end fixed-right align-items-center">
//           <button className="btn btn-outline-secondary logout_button" onClick={handleLogout}>Logout</button>
//         </div>
//       </div>

//       <div className="separator"></div>

//       <div className="admin-panel">
//         <div className="content">
//           <div className="header">
//             <h2 className="admin-title">All Projects</h2>
//             <button className="btn btn-primary" onClick={handleOpenModal}>Add Project</button>
//           </div>



// <div className="row">
//   {projectArray.map((project: any) => (
//     <div className="col-sm-4" key={project.project_key}>
//       <div className="card text-white bg-dark mb-3" style={{ maxWidth: "20rem" }}>
//         <div className="card-body">
//           <h5 className="card-title mb-5">{project.project_key}</h5>
//           <button className="btn btn-primary" onClick={() => handleViewDetails(project.project_key)}>View Project</button>
//           <button className="btn btn-danger" onClick={() => handleDeleteProject(project.project_key)}>Delete Project</button>
//         </div>
//       </div>
//     </div>
//   ))}
// </div>




//         </div>
//       </div>

//       <Modal show={showModal} onHide={handleCloseModal}>
//         <Modal.Header closeButton>
//           <Modal.Title className="modal-title">Add New Project</Modal.Title>
//         </Modal.Header>
//         <Modal.Body>
//           <div className="mb-3">
//             <label htmlFor="projectNameInput" className="form-label">Project Key</label>
//             <input type="text" className="form-control" id="projectNameInput" value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} />
//             <div id="projectNameHelp" className="form-text model-text">This has to be unique, lower case & without spaces</div>
//             {showAlert && <Alert variant="danger">Could not create the project, try a different name.</Alert>}
//           </div>
//         </Modal.Body>
//         <Modal.Footer>
//           <Button variant="secondary" onClick={handleCloseModal}>Close</Button>
//           <Button variant="primary" onClick={handleCreateProject}>Create</Button>
//         </Modal.Footer>
//       </Modal>

//     </div>
  );
};

export default AllProjectsComponent;
