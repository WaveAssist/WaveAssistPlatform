// src/Sidebar.js
import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import './sidebar.css';
import GreenLogo from '../assets/Logo/GreenLogo_Full_white_no_w.png';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();

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

  return (
    <div className="d-flex flex-column flex-shrink-0 p-3 text-bg-dark vh-100" style={{ width: '280px' }}>
      <a className="d-flex align-items-center mb-3 me-md-auto text-white text-decoration-none">
        <img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
      </a>
      <ul className="nav nav-pills flex-column mb-auto">
        <li className="nav-item">
          <Link to="/manage/nodes" className={`nav-link ${location.pathname === '/manage/nodes' ? 'active' : 'text-white'} mb-1`} aria-current="page">
            <i className="bi bi-bezier2 me-2"></i>
            Nodes
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/manage/variables" className={`nav-link ${location.pathname === '/manage/variables' ? 'active' : 'text-white'} mb-1`}>
            <i className="bi bi-table me-2"></i>
            Variables
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/manage/environments" className={`nav-link ${location.pathname === '/manage/environments' ? 'active' : 'text-white'} mb-1`}>
            <i className="bi bi-stack me-2"></i>
            Environments
          </Link>
        </li>
      </ul>
      <hr />
      <div>
        <button className="btn btn-outline-light w-100" type="button" onClick={handleLogout}>
          <i className="bi bi-box-arrow-right me-2"></i>
          Logout
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
