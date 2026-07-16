import type { CSSProperties } from "react";
import { useNavigate } from "react-router-dom";

export default function BalanceSheetMenu() {
  const navigate = useNavigate();

  return (
    <main style={styles.shell}>
      <aside style={styles.sidebar}>
        <div style={styles.brand}>Balance Sheet</div>
        <button style={styles.navButton} type="button" onClick={() => navigate("/balsheet/view")}>
          Balsheet View
        </button>
        <button style={styles.navButton} type="button" onClick={() => navigate("/balsheet/entry")}>
          Balsheet Entry
        </button>
        <button style={styles.navButton} type="button" onClick={() => navigate("/balsheet/bulk")}>
          Balsheet Bulk
        </button>
        <button style={styles.backButton} type="button" onClick={() => navigate("/")}>
          Back
        </button>
      </aside>

      <section style={styles.content}>
        <h1 style={styles.title}>Balance Sheet</h1>
        <div style={styles.menuGrid}>
          <button style={styles.menuButton} type="button" onClick={() => navigate("/balsheet/view")}>
            <span style={styles.menuTitle}>Balsheet View</span>
            <span style={styles.menuMeta}>Review and edit the master sheet.</span>
          </button>
          <button style={styles.menuButton} type="button" onClick={() => navigate("/balsheet/entry")}>
            <span style={styles.menuTitle}>Balsheet Entry</span>
            <span style={styles.menuMeta}>Post one manual entry into Balsheet.</span>
          </button>
          <button style={styles.menuButton} type="button" onClick={() => navigate("/balsheet/bulk")}>
            <span style={styles.menuTitle}>Balsheet Bulk</span>
            <span style={styles.menuMeta}>Post itemized rows into Balsheet.</span>
          </button>
        </div>
      </section>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  shell: {
    minHeight: "100vh",
    display: "grid",
    gridTemplateColumns: "220px 1fr",
    background: "#f6f7f9",
    color: "#1f2933",
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
    textAlign: "left",
  },
  sidebar: {
    borderRight: "1px solid #d9dee7",
    background: "#ffffff",
    padding: "18px 14px",
    boxSizing: "border-box",
  },
  brand: {
    fontSize: "18px",
    fontWeight: 800,
    marginBottom: "18px",
  },
  navButton: {
    width: "100%",
    height: "38px",
    marginBottom: "8px",
    border: "1px solid #c8d0dc",
    borderRadius: "6px",
    background: "#ffffff",
    color: "#1f2933",
    textAlign: "left",
    padding: "0 10px",
    fontWeight: 700,
    cursor: "pointer",
  },
  backButton: {
    width: "100%",
    height: "38px",
    marginTop: "12px",
    border: "1px solid #1f2933",
    borderRadius: "6px",
    background: "#1f2933",
    color: "#ffffff",
    textAlign: "left",
    padding: "0 10px",
    fontWeight: 700,
    cursor: "pointer",
  },
  content: {
    padding: "28px",
  },
  title: {
    margin: "0 0 20px",
    fontSize: "28px",
    fontWeight: 800,
  },
  menuGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 280px))",
    gap: "12px",
  },
  menuButton: {
    minHeight: "118px",
    border: "1px solid #d9dee7",
    borderRadius: "8px",
    background: "#ffffff",
    color: "#1f2933",
    textAlign: "left",
    padding: "16px",
    cursor: "pointer",
  },
  menuTitle: {
    display: "block",
    fontSize: "18px",
    fontWeight: 800,
    marginBottom: "8px",
  },
  menuMeta: {
    display: "block",
    color: "#5f6b7a",
    fontSize: "14px",
  },
};
