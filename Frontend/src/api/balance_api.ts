import axios from "axios";
const API = "http://127.0.0.1:8000";

export const getBalanceCheck = () => axios.get(`${API}/balancecheck`);
export const updateBalanceCheck = (id: string | number, data: unknown) =>
  axios.put(`${API}/balancecheck/${id}`, data);
