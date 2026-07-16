import axios from "axios";
const API = "http://127.0.0.1:8000";

export const getQueue = () => axios.get(`${API}/queue`);
export const approveItem = (id: string | number) => axios.post(`${API}/queue/${id}/approve`);
export const rejectItem = (id: string | number) => axios.post(`${API}/queue/${id}/reject`);
