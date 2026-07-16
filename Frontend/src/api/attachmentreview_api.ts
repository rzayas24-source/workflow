// src/api/attachmentreview_api.ts

const API = "http://127.0.0.1:8000";

export interface PendingAttachment {
  id: number;
  filename: string;
  snapshot: string | null;
  status: string;
  done: false;
}

export interface DoneResponse {
  done: true;
}

export type PendingResponse = PendingAttachment | DoneResponse;

function dayQuery(day?: string | null) {
  return day ? `?day=${encodeURIComponent(day)}` : "";
}

export async function getPendingAttachment(day?: string | null): Promise<PendingResponse> {
  const response = await fetch(`${API}/attachments/pending${dayQuery(day)}`);

  if (!response.ok) {
    throw new Error("Failed to load pending attachment");
  }

  return await response.json();
}

export async function getNextAttachment(id: number, day?: string | null): Promise<PendingResponse> {
  const response = await fetch(`${API}/attachments/${id}/next${dayQuery(day)}`);

  if (!response.ok) {
    throw new Error("Failed to load next attachment");
  }

  return await response.json();
}

export async function approveAttachment(id: number) {
  const response = await fetch(`${API}/attachments/${id}/approve`, { method: "POST" });

  if (!response.ok) {
    throw new Error("Failed to approve attachment");
  }

  return await response.json();
}

export async function rejectAttachment(id: number) {
  const response = await fetch(`${API}/attachments/${id}/reject`, { method: "POST" });

  if (!response.ok) {
    throw new Error("Failed to reject attachment");
  }

  return await response.json();
}
