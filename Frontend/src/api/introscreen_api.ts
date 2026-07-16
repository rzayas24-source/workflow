// src/api/introscreen_api.ts

export async function fetchPendingByDay() {
  const response = await fetch("http://127.0.0.1:8000/pending/by-day");

  if (!response.ok) {
    throw new Error("Failed to load pending items");
  }

  return await response.json();
}
