import axios from 'axios';

// const BASE_URL = 'https://assistapi.wavepredict.com';
const BASE_URL = 'http://127.0.0.1:8000';


export const loginAPI = async (username: string, password: string): Promise<any> => {
  const url = `${BASE_URL}/login/`;
  const headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
  const body = new URLSearchParams({ username: username, password: password });

  try {
    const response = await axios.post(url, body, { headers });
    const response_dict = response.data;
    if (response_dict.success === "1") {
        if (response_dict && response_dict.data) {
            return response_dict.data
          } else {
            throw new Error('Invalid response structure');
          }
    }
    else{
        throw new Error('Login failed');
    }
  } catch (error) {
    console.error('Error with login:', error);
    throw error;
  }
};

