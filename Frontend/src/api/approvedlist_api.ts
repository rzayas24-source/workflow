import axios from "axios";
const API = "http://127.0.0.1:8000";

export interface ApprovedBatch {
  id: number;
  filename: string;
  site: string | null;
  detail: string | null;
  total: number;
  date: string | null;
}

export const getApprovedList = () => axios.get<ApprovedBatch[]>(`${API}/approved`);
