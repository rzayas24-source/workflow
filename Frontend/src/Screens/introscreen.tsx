// src/Screens/introscreen.tsx

import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchPendingByDay } from "../api/introscreen_api";

interface PendingItem {
  id: number;
  filename: string;
}

interface PendingByDay {
  [day: string]: PendingItem[];
}

function formatDay(day: string) {
  if (!day || day === "Unknown") {
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

export default function IntroScreen() {
  const navigate = useNavigate();
  const [pending, setPending] = useState<PendingByDay>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    fetchPendingByDay()
      .then((data) => {
        setPending(data);
        setError(null);
      })
      .catch((err) => {
        setPending({});
        setError(err instanceof Error ? err.message : "Failed to load pending items");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const days = useMemo(() => Object.keys(pending), [pending]);
  const totalPending = useMemo(
    () => days.reduce((total, day) => total + pending[day].length, 0),
    [days, pending]
  );

  if (loading) {
    return (
      <main style={styles.page}>
        <div style={styles.statusText}>Loading pending items...</div>
      </main>
    );
  }

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>Pending Items</h1>
          <div style={styles.subtitle}>{totalPending} file{totalPending === 1 ? "" : "s"} waiting</div>
        </div>
        <div style={styles.menu}>
          <button
            style={styles.menuButton}
            type="button"
            onClick={() => setMenuOpen((current) => !current)}
            title="More options"
            aria-label="More options"
            aria-expanded={menuOpen}
          >
            ...
          </button>
          {menuOpen && (
            <div style={styles.menuDropdown}>
              <button
                style={styles.menuItem}
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/balance-sheet");
                }}
              >
                Balsheet
              </button>
              <button
                style={styles.menuItem}
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/approved");
                }}
              >
                Approved Batches
              </button>
            </div>
          )}
        </div>
      </header>

      {error && <div style={styles.errorText}>{error}</div>}

      {days.length === 0 && !error && (
        <div style={styles.statusText}>No pending items found.</div>
      )}

      <section style={styles.dayList}>
        {days.map((day) => (
          <div key={day} style={styles.dayGroup}>
            <div style={styles.dayHeader}>
              <h2 style={styles.dayTitle}>{formatDay(day)}</h2>
              <div style={styles.dayActions}>
                <span style={styles.count}>{pending[day].length}</span>
                <button
                  style={styles.smallButton}
                  onClick={() => navigate(`/attachments?day=${encodeURIComponent(day)}`)}
                >
                  Review
                </button>
              </div>
            </div>

            <ul style={styles.fileList}>
              {pending[day].map((item) => (
                <li key={item.id} style={styles.fileItem}>{item.filename}</li>
              ))}
            </ul>
          </div>
        ))}
      </section>
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
    marginBottom: "24px",
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
  menu: {
    position: "relative",
  },
  menuButton: {
    width: "36px",
    height: "34px",
    border: "1px solid #c8d0dc",
    borderRadius: "6px",
    background: "#ffffff",
    color: "#1f2933",
    cursor: "pointer",
    fontSize: "18px",
    fontWeight: 700,
    lineHeight: 1,
  },
  menuDropdown: {
    position: "absolute",
    top: "40px",
    right: 0,
    zIndex: 5,
    minWidth: "170px",
    border: "1px solid #c8d0dc",
    borderRadius: "6px",
    background: "#ffffff",
    boxShadow: "0 8px 18px rgba(31, 41, 51, 0.12)",
    overflow: "hidden",
  },
  menuItem: {
    width: "100%",
    padding: "10px 12px",
    border: 0,
    background: "#ffffff",
    color: "#1f2933",
    cursor: "pointer",
    textAlign: "left",
    fontSize: "14px",
  },
  dayList: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  dayGroup: {
    border: "1px solid #d9dee7",
    borderRadius: "8px",
    background: "#ffffff",
    overflow: "hidden",
  },
  dayHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
    padding: "14px 16px",
    borderBottom: "1px solid #edf0f4",
    background: "#fbfcfe",
  },
  dayTitle: {
    margin: 0,
    fontSize: "17px",
    fontWeight: 700,
  },
  dayActions: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  smallButton: {
    height: "32px",
    padding: "0 12px",
    border: "1px solid #1f6feb",
    borderRadius: "6px",
    background: "#1f6feb",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
  },
  count: {
    minWidth: "28px",
    height: "24px",
    padding: "0 8px",
    borderRadius: "999px",
    background: "#eef4ff",
    color: "#1f4e91",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "13px",
    fontWeight: 700,
  },
  fileList: {
    listStyle: "none",
    margin: 0,
    padding: 0,
  },
  fileItem: {
    padding: "10px 16px",
    borderBottom: "1px solid #f0f2f5",
    fontSize: "15px",
    overflowWrap: "anywhere",
  },
  statusText: {
    fontSize: "18px",
    color: "#4b5563",
  },
  errorText: {
    marginBottom: "18px",
    padding: "12px 14px",
    border: "1px solid #f0b4b4",
    borderRadius: "6px",
    background: "#fff5f5",
    color: "#a32121",
    fontSize: "15px",
  },
};
