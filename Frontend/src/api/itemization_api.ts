import axios from "axios";
const API = "http://127.0.0.1:8000";

export const getItemization = () => axios.get(`${API}/itemization`);
export const addItem = (data: unknown) => axios.post(`${API}/itemization`, data);
export const updateItem = (id: string | number, data: unknown) =>
  axios.put(`${API}/itemization/${id}`, data);
export const deleteItem = (id: string | number) => axios.delete(`${API}/itemization/${id}`);
