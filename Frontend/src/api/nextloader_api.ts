import axios from "axios";
const API = "http://127.0.0.1:8000";

export const getNextLoader = () => axios.get(`${API}/nextloader`);
export const updateNextLoader = (id: string | number, data: unknown) =>
  axios.put(`${API}/nextloader/${id}`, data);
