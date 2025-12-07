// src/api.js
import axios from 'axios';

export const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:9000';

export const API  = axios.create({
  baseURL: `${BASE}/api`,
  withCredentials: true,
});


// Auth
export const loginApi  = (username, password) => API.post('/auth/login', { username, password });
export const logoutApi = () => API.post('/auth/logout');
export const meApi     = () => API.get('/auth/me');

// Games
export const listGames   = () => API.get('/games');
export const getGame     = (id) => API.get(`/games/${id}`);
export const createGame  = (payload) => API.post('/games', payload);
export const updateGame  = (id, payload) => API.put(`/games/${id}`, payload);
export const deleteGame  = (id) => API.delete(`/games/${id}`);

// Upload (multipart)
export const uploadImage = async (file) => {
  const fd = new FormData();
  fd.append('file', file);
  const { data } = await API.post('/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  // data = { filename: 'archivo.ext' }
  return { image_path: `/static/uploads/${data.filename}` };

};
