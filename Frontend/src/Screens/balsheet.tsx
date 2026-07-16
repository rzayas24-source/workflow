import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  addBalsheetEntries,
  addBalsheetEntry,
  deleteBalsheetEntry,
  getBalsheet,
  getBalsheetWorkday,
  updateBalsheetEntry,
  type BalsheetEntry,
} from "../api/balsheet_api";

type ItemizationItem = Record<string, string | number>;
type BalsheetMode = "view" | "entry" | "bulk";

interface BalsheetProps {
  mode?: BalsheetMode;
}

const blankEntry: BalsheetEntry = {
  posting_date: "",
  type: "",
  amount: 0,
  payer: "",
  check_number: "",
  edi: "N",
  poster: "N",
  eob: "",
  unposted: 0,
  misc: 0,
  misc_type: "",
  notes: "",
  nick: 0,
  raul: 0,
  needs: "",
  from_date: "",
  to_date: "",
};

const columns: Array<{ key: keyof BalsheetEntry; label: string; numeric?: boolean }> = [
  { key: "posting_date", label: "Posting Date" },
  { key: "type", label: "Type" },
  { key: "amount", label: "Amount", numeric: true },
  { key: "payer", label: "Payer" },
  { key: "check_number", label: "Check/CC Number" },
  { key: "edi", label: "EDI" },
  { key: "poster", label: "Poster" },
  { key: "eob", label: "EOB" },
  { key: "unposted", label: "UnPosted", numeric: true },
  { key: "misc", label: "Misc", numeric: true },
  { key: "misc_type", label: "Misc-Type" },
  { key: "notes", label: "Notes" },
  { key: "nick", label: "Nick", numeric: true },
  { key: "raul", label: "Raul", numeric: true },
  { key: "needs", label: "Needs" },
  { key: "from_date", label: "From" },
  { key: "to_date", label: "To" },
];

function parseAmount(value: unknown) {
  const parsed = Number.parseFloat(String(value ?? "").replace(/[$,]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrency(value: unknown) {
  return parseAmount(value).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}

function normalizePoster(value: unknown) {
  const poster = String(value || "").toLowerCase();
  if (poster === "raul" || poster === "r") return "R";
  return "N";
}

function normalizeYesNo(value: unknown) {
  const cleaned = String(value || "").toLowerCase();
  if (cleaned === "yes" || cleaned === "y") return "Y";
  if (cleaned === "no" || cleaned === "n") return "N";
  return String(value || "");
}

function normalizeDisplayDate(value: string | null) {
  if (!value) return "";

  const isoMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (isoMatch) {
    return `${isoMatch[2]}/${isoMatch[3]}/${isoMatch[1]}`;
  }

  return value;
}

function calculateSplit(entry: BalsheetEntry) {
  const amount = parseAmount(entry.amount);
  const unposted = parseAmount(entry.unposted);
  const misc = parseAmount(entry.misc);
  const base = amount - unposted - misc;

  if (entry.poster === "R") {
    return { ...entry, nick: 0, raul: base };
  }

  return { ...entry, nick: base, raul: 0 };
}

function mapItemizationToBalsheet(item: ItemizationItem, postingDate: string): BalsheetEntry {
  const poster = normalizePoster(item.poster);
  return calculateSplit({
    ...blankEntry,
    posting_date: postingDate,
    type: String(item.type || ""),
    amount: parseAmount(item.amount),
    payer: String(item.payer || ""),
    check_number: String(item.check_number || ""),
    edi: normalizeYesNo(item.edi),
    poster,
    eob: String(item.eob || ""),
    unposted: parseAmount(item.unposted),
    misc: parseAmount(item.misc),
    misc_type: String(item.misc_type || ""),
    notes: String(item.notes || ""),
    needs: String(item.needs || ""),
    from_date: String(item.from || ""),
    to_date: String(item.to || ""),
  });
}

function modeTitle(mode: BalsheetMode) {
  if (mode === "entry") return "Balsheet Entry";
  if (mode === "bulk") return "Balsheet Bulk";
  return "Balsheet View";
}

export default function Balsheet({ mode = "view" }: BalsheetProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const attachmentId = searchParams.get("attachmentId");
  const day = searchParams.get("day");
  const [postingDate, setPostingDate] = useState(normalizeDisplayDate(day));
  const [rows, setRows] = useState<BalsheetEntry[]>([]);
  const [draft, setDraft] = useState<BalsheetEntry>(blankEntry);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<BalsheetEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const itemizationRows = useMemo(() => {
    if (!attachmentId) return [];
    const saved = window.localStorage.getItem(`itemization:${attachmentId}`);
    if (!saved) return [];

    try {
      return JSON.parse(saved) as ItemizationItem[];
    } catch {
      return [];
    }
  }, [attachmentId]);

  const incomingRows = useMemo(
    () => itemizationRows.map((item) => mapItemizationToBalsheet(item, postingDate)),
    [itemizationRows, postingDate]
  );

  const totals = useMemo(
    () =>
      rows.reduce(
        (acc, row) => ({
          amount: acc.amount + parseAmount(row.amount),
          nick: acc.nick + parseAmount(row.nick),
          raul: acc.raul + parseAmount(row.raul),
          unposted: acc.unposted + parseAmount(row.unposted),
          misc: acc.misc + parseAmount(row.misc),
        }),
        { amount: 0, nick: 0, raul: 0, unposted: 0, misc: 0 }
      ),
    [rows]
  );

  useEffect(() => {
    getBalsheetWorkday()
      .then((response) => {
        const currentDay = normalizeDisplayDate(day) || response.data.posting_date;
        setPostingDate(currentDay);
        setDraft({ ...blankEntry, posting_date: currentDay });
        return getBalsheet(currentDay);
      })
      .then((response) => {
        setRows(response.data);
        setError(null);
      })
      .catch((err) => {
        setRows([]);
        setError(err instanceof Error ? err.message : "Failed to load Balsheet");
      })
      .finally(() => setLoading(false));
  }, [day]);

  async function reload(date = postingDate) {
    const response = await getBalsheet(date);
    setRows(response.data);
  }

  function updateDraft(field: keyof BalsheetEntry, value: string) {
    setDraft((current) => {
      const next = { ...current, [field]: value };
      if (field === "amount" || field === "unposted" || field === "misc" || field === "poster") {
        return calculateSplit({ ...next, poster: normalizePoster(next.poster) });
      }
      return next;
    });
  }

  function updateEditDraft(field: keyof BalsheetEntry, value: string) {
    setEditDraft((current) => {
      if (!current) return current;
      const next = { ...current, [field]: value };
      if (field === "amount" || field === "unposted" || field === "misc" || field === "poster") {
        return calculateSplit({ ...next, poster: normalizePoster(next.poster) });
      }
      return next;
    });
  }

  async function saveManualEntry() {
    const entry = calculateSplit({ ...draft, posting_date: postingDate });
    await addBalsheetEntry(entry);
    setDraft({ ...blankEntry, posting_date: postingDate });
    await reload();
    setMessage("Balsheet entry posted.");
  }

  async function importItemization() {
    if (incomingRows.length === 0) {
      setError("No itemization rows found for this attachment.");
      return;
    }

    await addBalsheetEntries(incomingRows, attachmentId ? Number(attachmentId) : undefined);
    await reload();
    setMessage(`${incomingRows.length} itemization row${incomingRows.length === 1 ? "" : "s"} posted to Balsheet.`);
    setError(null);
  }

  async function saveEdit() {
    if (!editingId || !editDraft) return;
    await updateBalsheetEntry(editingId, calculateSplit(editDraft));
    setEditingId(null);
    setEditDraft(null);
    await reload();
    setMessage("Balsheet entry updated.");
  }

  async function removeEntry(entryId?: string) {
    if (!entryId) return;
    await deleteBalsheetEntry(entryId);
    await reload();
    setMessage("Balsheet entry deleted.");
  }

  if (loading) {
    return <main style={styles.page}>Loading Balsheet...</main>;
  }

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>{modeTitle(mode)}</h1>
          <div style={styles.subtitle}>Posting date {postingDate}</div>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.secondaryButton} type="button" onClick={() => navigate("/balance-sheet")}>
            Back
          </button>
          <button style={styles.primaryButton} type="button" onClick={() => reload()}>
            Refresh
          </button>
        </div>
      </header>

      {error && <div style={styles.error}>{error}</div>}
      {message && <div style={styles.message}>{message}</div>}

      <section style={styles.toolbar}>
        <label style={styles.compactLabel}>
          Posting Date
          <input
            type="text"
            placeholder="MM/DD/YYYY"
            value={postingDate}
            style={styles.input}
            onChange={(event) => {
              setPostingDate(event.target.value);
              setDraft((current) => ({ ...current, posting_date: event.target.value }));
              reload(event.target.value);
            }}
          />
        </label>
        <div style={styles.totalStrip}>
          <span>Amount {formatCurrency(totals.amount)}</span>
          <span>Nick {formatCurrency(totals.nick)}</span>
          <span>Raul {formatCurrency(totals.raul)}</span>
          <span>UnPosted {formatCurrency(totals.unposted)}</span>
          <span>Misc {formatCurrency(totals.misc)}</span>
        </div>
      </section>

      {mode === "bulk" && (
        <section style={styles.importPanel}>
          <div>
            <strong>Incoming itemization</strong>
            <div style={styles.muted}>
              {attachmentId
                ? `Attachment #${attachmentId}: ${incomingRows.length} row${incomingRows.length === 1 ? "" : "s"} ready`
                : "Open this from Itemization to post those rows into Balsheet."}
            </div>
          </div>
          <button
            style={styles.primaryButton}
            type="button"
            onClick={importItemization}
            disabled={!attachmentId}
          >
            Post Itemization to Balsheet
          </button>
        </section>
      )}

      {mode === "entry" && (
        <section style={styles.formGrid}>
          {columns
            .filter((column) => column.key !== "posting_date")
            .map((column) => (
              <label key={column.key} style={styles.label}>
                {column.label}
                <input
                  type={column.numeric ? "number" : "text"}
                  step={column.numeric ? "0.01" : undefined}
                  value={String(draft[column.key] ?? "")}
                  style={styles.input}
                  onChange={(event) => updateDraft(column.key, event.target.value)}
                />
              </label>
            ))}
          <button style={styles.primaryButton} type="button" onClick={saveManualEntry}>
            Add Manual Entry
          </button>
        </section>
      )}

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>EntryID</th>
              {columns.map((column) => (
                <th key={column.key} style={styles.th}>{column.label}</th>
              ))}
              <th style={styles.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isEditing = editingId === row.entry_id;
              const source = isEditing && editDraft ? editDraft : row;

              return (
                <tr key={row.entry_id}>
                  <td style={styles.td}>{row.entry_id}</td>
                  {columns.map((column) => (
                    <td key={column.key} style={column.numeric ? styles.numericTd : styles.td}>
                      {isEditing ? (
                        <input
                          type={column.numeric ? "number" : "text"}
                          placeholder={column.key === "posting_date" ? "MM/DD/YYYY" : undefined}
                          step={column.numeric ? "0.01" : undefined}
                          value={String(source[column.key] ?? "")}
                          style={styles.tableInput}
                          onChange={(event) => updateEditDraft(column.key, event.target.value)}
                        />
                      ) : column.numeric ? (
                        formatCurrency(source[column.key])
                      ) : (
                        String(source[column.key] ?? "")
                      )}
                    </td>
                  ))}
                  <td style={styles.actionTd}>
                    {isEditing ? (
                      <>
                        <button style={styles.smallButton} type="button" onClick={saveEdit}>
                          Save
                        </button>
                        <button
                          style={styles.smallSecondary}
                          type="button"
                          onClick={() => {
                            setEditingId(null);
                            setEditDraft(null);
                          }}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          style={styles.smallButton}
                          type="button"
                          onClick={() => {
                            setEditingId(row.entry_id || null);
                            setEditDraft(row);
                          }}
                        >
                          Edit
                        </button>
                        <button
                          style={styles.smallDanger}
                          type="button"
                          onClick={() => removeEntry(row.entry_id)}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: "100vh",
    boxSizing: "border-box",
    padding: "24px",
    background: "#f6f7f9",
    color: "#1f2933",
    textAlign: "left",
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "16px",
    marginBottom: "18px",
  },
  title: {
    margin: 0,
    fontSize: "28px",
    fontWeight: 700,
  },
  subtitle: {
    marginTop: "4px",
    color: "#5f6b7a",
    fontSize: "14px",
  },
  headerActions: {
    display: "flex",
    gap: "8px",
  },
  toolbar: {
    display: "flex",
    alignItems: "end",
    justifyContent: "space-between",
    gap: "16px",
    marginBottom: "14px",
  },
  totalStrip: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
    fontSize: "13px",
    fontWeight: 700,
  },
  importPanel: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
    padding: "12px",
    border: "1px solid #d9dee7",
    borderRadius: "8px",
    background: "#ffffff",
    marginBottom: "14px",
  },
  formGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
    gap: "10px",
    padding: "12px",
    border: "1px solid #d9dee7",
    borderRadius: "8px",
    background: "#ffffff",
    marginBottom: "14px",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    fontSize: "12px",
    fontWeight: 700,
    color: "#4b5563",
  },
  compactLabel: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    fontSize: "12px",
    fontWeight: 700,
  },
  input: {
    height: "32px",
    boxSizing: "border-box",
    border: "1px solid #c8d0dc",
    borderRadius: "6px",
    padding: "0 8px",
    background: "#ffffff",
    color: "#1f2933",
  },
  tableWrap: {
    overflowX: "auto",
    border: "1px solid #d9dee7",
    borderRadius: "8px",
    background: "#ffffff",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    minWidth: "1600px",
    fontSize: "13px",
  },
  th: {
    padding: "9px 8px",
    borderBottom: "1px solid #d9dee7",
    background: "#fbfcfe",
    textAlign: "left",
    whiteSpace: "nowrap",
  },
  td: {
    padding: "8px",
    borderBottom: "1px solid #edf0f4",
    verticalAlign: "top",
  },
  numericTd: {
    padding: "8px",
    borderBottom: "1px solid #edf0f4",
    textAlign: "right",
    whiteSpace: "nowrap",
    verticalAlign: "top",
  },
  actionTd: {
    padding: "8px",
    borderBottom: "1px solid #edf0f4",
    whiteSpace: "nowrap",
    verticalAlign: "top",
  },
  tableInput: {
    width: "120px",
    height: "28px",
    boxSizing: "border-box",
    border: "1px solid #c8d0dc",
    borderRadius: "5px",
    padding: "0 6px",
  },
  primaryButton: {
    height: "34px",
    padding: "0 12px",
    border: "1px solid #1f6feb",
    borderRadius: "6px",
    background: "#1f6feb",
    color: "#ffffff",
    fontWeight: 700,
    cursor: "pointer",
  },
  secondaryButton: {
    height: "34px",
    padding: "0 12px",
    border: "1px solid #c8d0dc",
    borderRadius: "6px",
    background: "#ffffff",
    color: "#1f2933",
    fontWeight: 700,
    cursor: "pointer",
  },
  smallButton: {
    height: "28px",
    padding: "0 8px",
    marginRight: "6px",
    border: "1px solid #1f6feb",
    borderRadius: "5px",
    background: "#1f6feb",
    color: "#ffffff",
    cursor: "pointer",
  },
  smallSecondary: {
    height: "28px",
    padding: "0 8px",
    border: "1px solid #c8d0dc",
    borderRadius: "5px",
    background: "#ffffff",
    color: "#1f2933",
    cursor: "pointer",
  },
  smallDanger: {
    height: "28px",
    padding: "0 8px",
    border: "1px solid #b42318",
    borderRadius: "5px",
    background: "#b42318",
    color: "#ffffff",
    cursor: "pointer",
  },
  message: {
    marginBottom: "12px",
    padding: "10px 12px",
    border: "1px solid #a7d7b4",
    borderRadius: "6px",
    background: "#f1fbf4",
    color: "#17612d",
  },
  error: {
    marginBottom: "12px",
    padding: "10px 12px",
    border: "1px solid #f0b4b4",
    borderRadius: "6px",
    background: "#fff5f5",
    color: "#a32121",
  },
  muted: {
    color: "#5f6b7a",
    fontSize: "13px",
  },
};
