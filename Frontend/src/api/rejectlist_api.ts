import axios from "axios";
const API = "http://127.0.0.1:8000";

export interface RejectedBatch {
  id: number;
  filename: string;
  reason: string | null;
  date: string | null;
}

export const getRejectList = () => axios.get<RejectedBatch[]>(`${API}/rejectlist`);
