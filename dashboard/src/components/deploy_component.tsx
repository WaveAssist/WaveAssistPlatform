import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import "./deploy_component.css";
import axios from "axios";
import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import 'bootstrap/dist/css/bootstrap.min.css';


const DeployComponent: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [deployInfo, setDeployInfo] = useState({
    repoUrl: "",
    title: "",
    description: "",
    imageUrl: "",
  });

  const [isDeploying, setIsDeploying] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [createdProject, setCreatedProject] = useState<any>(null);

  useEffect(() => {
    const uid = localStorage.getItem("uid");

    if (!uid) {
      const currentPath = window.location.pathname + window.location.search;
      navigate(`/login?redirect=${encodeURIComponent(currentPath)}`);
      return;
    }

    const repoUrl = searchParams.get("repo_url") || "";
    const title = searchParams.get("title") || "";
    const description = searchParams.get("description") || "";
    const imageUrl = searchParams.get("image_url") || "";

    setDeployInfo({
      repoUrl: decodeURIComponent(repoUrl),
      title: decodeURIComponent(title),
      description: decodeURIComponent(description),
      imageUrl: decodeURIComponent(imageUrl),
    });
  }, [searchParams, navigate]);

  const handleDeploy = async () => {
    const uid = localStorage.getItem("uid");
    if (!uid) return;

    setIsDeploying(true);

    try {
      const formData = new FormData();
      formData.append("repo_url", deployInfo.repoUrl);
      formData.append("uid", uid);

      const response = await axios.post(
        "http://127.0.0.1:8000/template/deploy_template/",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      if (response.data.success === "1") {
        setCreatedProject(response.data.data);
        setShowSuccessModal(true);
      } else {
        alert("❌ Failed to deploy project.");
      }
    } catch (error) {
      console.error("Deploy failed:", error);
      alert("Something went wrong while deploying. Please try again.");
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <div className="deploy-container">
      <div className="content">
        <div className="deploy-card">
          {deployInfo.imageUrl && (
            <div className="deploy-image">
              <img src={deployInfo.imageUrl} alt={deployInfo.title} />
            </div>
          )}
          <div className="deploy-content">
            <h1>{deployInfo.title}</h1>
            <p className="description">{deployInfo.description}</p>
            <div className="repo-info mb-4">
              <h3>Repository URL:</h3>
              <a
                href={deployInfo.repoUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                {deployInfo.repoUrl}
              </a>
            </div>
            <button
              onClick={handleDeploy}
              className="btn btn-primary"
              disabled={isDeploying}
            >
              {isDeploying ? (
                <>
                  <Spinner
                    animation="border"
                    size="sm"
                    className="me-2"
                    role="status"
                  />
                  Deploying...
                </>
              ) : (
                "🚀 Deploy Now"
              )}
            </button>

            {isDeploying && (
              <div className="text-center mt-4">
                <Spinner animation="border" variant="light" className="me-2" role="status" />
                <p className="mt-3" style={{ color: "rgba(255,255,255,0.75)" }}>
                  Deploying your project. This may take a few minutes...
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="text-center mt-4">
          <button
            className="btn btn-outline-light"
            onClick={() => navigate("/manage")}
          >
            ← Go to All Projects
          </button>
        </div>
      </div>

      <Modal
        show={showSuccessModal}
        onHide={() => setShowSuccessModal(false)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>🎉 Project Deployed</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            Project <strong>{createdProject?.name}</strong> was created
            successfully with key{" "}
            <code>{createdProject?.project_key}</code>.
          </p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="success" onClick={() => navigate("/manage")}>
            Go to All Projects
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default DeployComponent;
