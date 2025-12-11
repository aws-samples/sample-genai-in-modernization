import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export const generateBusinessCase = async ({ projectInfo, uploadedFiles, selectedAgents }) => {
  try {
    const formData = new FormData();
    
    // Add project info
    formData.append('projectInfo', JSON.stringify(projectInfo));
    formData.append('selectedAgents', JSON.stringify(selectedAgents));
    
    // Add files
    Object.entries(uploadedFiles).forEach(([key, file]) => {
      if (file) {
        // Handle multiple files (e.g., RVTools can have multiple files)
        if (Array.isArray(file)) {
          file.forEach(f => {
            if (f) formData.append(key, f);
          });
        } else {
          formData.append(key, file);
        }
      }
    });

    const response = await axios.post(`${API_BASE_URL}/generate`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 600000, // 10 minutes
    });

    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    throw new Error(error.response?.data?.message || 'Failed to generate business case');
  }
};

export const checkStatus = async (jobId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/status/${jobId}`);
    return response.data;
  } catch (error) {
    console.error('Status check error:', error);
    throw new Error('Failed to check generation status');
  }
};
