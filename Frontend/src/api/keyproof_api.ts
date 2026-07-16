import axios from "axios";
const API = "http://127.0.0.1:8000";

export interface KeyproofDraft {
  attachmentId: number;
  site: string;
  cash: string;
  check: string;
  creditCard: string;
  eft: string;
  lockbox: string;
  foreignCheck: string;
  wireTransfer: string;
  misc: string;
  miscDescription: string;
}

export interface SiteOption {
  id: number;
  name: string;
  description: string | null;
  active: number;
}

export const getKeyproof = () => axios.get(`${API}/keyproof`);
export const addKeyproof = (data: KeyproofDraft) => axios.post(`${API}/keyproof`, data);
export const updateKeyproof = (id: number, data: KeyproofDraft) => axios.put(`${API}/keyproof/${id}`, data);
export const deleteKeyproof = (id: number) => axios.delete(`${API}/keyproof/${id}`);
export const getSites = () => axios.get<SiteOption[]>(`${API}/sites`);
