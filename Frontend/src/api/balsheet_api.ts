import axios from "axios";

const API = "http://127.0.0.1:8000";

export interface BalsheetEntry {
  entry_id?: string;
  posting_date: string;
  type: string;
  amount: number;
  payer: string;
  check_number: string;
  edi: string;
  poster: string;
  eob: string;
  unposted: number;
  misc: number;
  misc_type: string;
  notes: string;
  nick: number;
  raul: number;
  needs: string;
  from_date: string;
  to_date: string;
}

export function getBalsheet(postingDate?: string) {
  const params = postingDate ? { posting_date: postingDate } : undefined;
  return axios.get<BalsheetEntry[]>(`${API}/balsheet`, { params });
}

export function getBalsheetWorkday() {
  return axios.get<{ posting_date: string }>(`${API}/balsheet/workday`);
}

export function addBalsheetEntry(entry: BalsheetEntry) {
  return axios.post(`${API}/balsheet`, entry);
}

export function addBalsheetEntries(entries: BalsheetEntry[], sourceAttachmentId?: number) {
  return axios.post(`${API}/balsheet/bulk`, {
    entries,
    source_attachment_id: sourceAttachmentId,
  });
}

export function updateBalsheetEntry(entryId: string, entry: BalsheetEntry) {
  return axios.put(`${API}/balsheet/${encodeURIComponent(entryId)}`, entry);
}

export function deleteBalsheetEntry(entryId: string) {
  return axios.delete(`${API}/balsheet/${encodeURIComponent(entryId)}`);
}
