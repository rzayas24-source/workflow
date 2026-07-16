import axios from "axios";
const API = "http://127.0.0.1:8000";

export const getCompletionLabels = () => axios.get(`${API}/completionlabels`);
export const updateCompletionLabel = (id: string | number, data: unknown) =>
  axios.put(`${API}/completionlabels/${id}`, data);
