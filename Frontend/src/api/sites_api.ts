import axios from "axios";
const API = "http://127.0.0.1:8000";

export const getSites = () => axios.get(`${API}/sites`);
export const addSite = (data: unknown) => axios.post(`${API}/sites`, data);
export const updateSite = (id: string | number, data: unknown) => axios.put(`${API}/sites/${id}`, data);
export const deleteSite = (id: string | number) => axios.delete(`${API}/sites/${id}`);
