import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  getNextAttachment,
  getPendingAttachment,
  rejectAttachment,
} from "../api/attachmentreview_api";
import type { PendingAttachment } from "../api/attachmentreview_api";

function formatDay(day: string | null) {
  if (!day) {
    return "All pending";
  }

  if (day === "Unknown") {
    return "Unknown date";
  }

  const parsed = new Date(`${day}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return day;
  }

  return parsed.toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const snapshotUrl = (id: number) => `http://localhost:8000/attachments/${id}/snapshot`;

export default function AttachmentReviewScreen() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const day = searchParams.get("day");
  const [attachment, setAttachment] = useState<PendingAttachment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getPendingAttachment(day)
      .then((data) => {
        setAttachment(data.done ? null : data);
        setError(null);
      })
      .catch((err) => {
        setAttachment(null);
        setError(err instanceof Error ? err.message : "Failed to load attachment");
      })
      .finally(() => setLoading(false));
  }, [day]);

  async function moveToNext(currentId: number) {
    const next = await getNextAttachment(currentId, day);
    setAttachment(next.done ? null : next);
  }

  function handleReview() {
    if (!attachment) return;
    const params = new URLSearchParams({ attachmentId: String(attachment.id) });

    if (day) {
      params.set("day", day);
    }

    navigate(`/keyproof?${params.toString()}`);
  }

  async function handleReject() {
    if (!attachment) return;
    const currentId = attachment.id;
    await rejectAttachment(currentId);
    await moveToNext(currentId);
  }

  if (loading) {
    return <main style={styles.page}>Loading...</main>;
  }

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>Attachment Review</h1>
          <div style={styles.subtitle}>{formatDay(day)}</div>
        </div>
        <button style={styles.secondaryButton} onClick={() => navigate("/site")}>Back</button>
      </header>

      {error && <div style={styles.error}>{error}</div>}

      {!attachment && !error && (
        <div style={styles.empty}>No pending attachments for this day.</div>
      )}

      {attachment && (
        <section style={styles.reviewPanel}>
          <div style={styles.filename}>{attachment.filename}</div>

          <img
            src={snapshotUrl(attachment.id)}
            alt={attachment.filename}
            style={styles.snapshot}
          />

          <div style={styles.actions}>
            <button style={styles.primaryButton} onClick={handleReview}>Review</button>
            <button style={styles.rejectButton} onClick={handleReject}>Reject</button>
          </div>
        </section>
      )}
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: "100vh",
    boxSizing: "border-box",
    padding: "28px",
    background: "#f6f7f9",
    color: "#1f2933",
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "16px",
    marginBottom: "22px",
  },
  title: {
    margin: 0,
    fontSize: "28px",
    fontWeight: 700,
  },
  subtitle: {
    marginTop: "6px",
    fontSize: "15px",
    color: "#5f6b7a",
  },
  reviewPanel: {
    maxWidth: "760px",
    border: "1px solid #d9dee7",
    borderRadius: "8px",
    background: "#ffffff",
    overflow: "hidden",
  },
  filename: {
    padding: "14px 16px",
    borderBottom: "1px solid #edf0f4",
    fontWeight: 700,
    overflowWrap: "anywhere",
  },
  snapshot: {
    display: "block",
    width: "100%",
    maxHeight: "70vh",
    objectFit: "contain",
    background: "#ffffff",
  },
  actions: {
    display: "flex",
    gap: "10px",
    padding: "14px 16px",
    borderTop: "1px solid #edf0f4",
  },
  primaryButton: {
    height: "40px",
    padding: "0 18px",
    border: "1px solid #1f6feb",
    borderRadius: "6px",
    background: "#1f6feb",
    color: "#ffffff",
    fontSize: "15px",
    fontWeight: 600,
    cursor: "pointer",
  },
  secondaryButton: {
    height: "40px",
    padding: "0 16px",
    border: "1px solid #c8d0dc",
    borderRadius: "6px",
    background: "#ffffff",
    color: "#1f2933",
    fontSize: "15px",
    fontWeight: 600,
    cursor: "pointer",
  },
  rejectButton: {
    height: "40px",
    padding: "0 18px",
    border: "1px solid #c83a3a",
    borderRadius: "6px",
    background: "#c83a3a",
    color: "#ffffff",
    fontSize: "15px",
    fontWeight: 600,
    cursor: "pointer",
  },
  empty: {
    fontSize: "18px",
    color: "#4b5563",
  },
  error: {
    marginBottom: "18px",
    padding: "12px 14px",
    border: "1px solid #f0b4b4",
    borderRadius: "6px",
    background: "#fff5f5",
    color: "#a32121",
    fontSize: "15px",
  },
};
