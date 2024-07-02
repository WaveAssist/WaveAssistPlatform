import axios from 'axios';

// const BASE_URL = 'https://assistapi.wavepredict.com';
const BASE_URL = 'http://127.0.0.1:8000/manage';


export const fetchAllProjectsAPI = async (): Promise<any> => {
  const url = `${BASE_URL}/fetch_all_projects/`;
  const headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
  const body = new URLSearchParams({
    uid: localStorage.getItem('uid') || '',
  });
  try {
    const response = await axios.post(url, body, { headers });
    const responseDict = response.data;
    if (responseDict.success === "1") {
      if (responseDict && responseDict.data) {
        return responseDict.data;
      } else {
        throw new Error('Invalid response structure');
      }
    }
    else{
        var error_message = responseDict.message;
        throw new Error(error_message)
    }
  } catch (error) {
    console.error(error);
    throw error;
  }
};



export const createProjectAPI = async (projectKey: string): Promise<any> => {
  const url = `${BASE_URL}/create_project/`;
  const headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
  const body = new URLSearchParams({
    uid: localStorage.getItem('uid') || '',
    project_key: projectKey,
  });
  try {
    const response = await axios.post(url, body, { headers });
    const responseDict = response.data;
    if (responseDict.success === "1") {
      if (responseDict && responseDict.data) {
        return responseDict.data;
      } else {
        throw new Error('Invalid response structure');
      }
    } else {
      var error_message = responseDict.message;
      throw new Error(error_message);
    }
  } catch (error) {
    console.error(error);
    throw error;
  }
};


export const deleteProjectApi = async (projectKey: string): Promise<any> => {
  const url = `${BASE_URL}/delete_project/`;
  const headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
  const body = new URLSearchParams({
    uid: localStorage.getItem('uid') || '',
    project_key: projectKey,
  });
  try {
    const response = await axios.post(url, body, { headers });
    const responseDict = response.data;
    if (responseDict.success === "1") {
      if (responseDict && responseDict.data) {
        return responseDict.data;
      } else {
        throw new Error('Invalid response structure');
      }
    } else {
      var error_message = responseDict.message;
      throw new Error(error_message);
    }
  } catch (error) {
    console.error(error);
    throw error;
  }
};
