import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import ItemizationGrid from "./itemizationgrid";

type ItemizationForm = Record<string, string | number>;
type ItemizationItem = ItemizationForm & {
  id: number;
  importId: number;
  type: string;
  amount: number;
  misc: number;
};

const posterOptions = ["Nick", "Raul"];
const yesNoOptions = ["Yes", "No"];
const numericFields = ["amount", "unposted", "misc", "nick", "raul"] as const;
const currencyFields = ["amount", "unposted", "misc", "nick", "raul"] as const;

function fieldLabel(field: string) {
  if (field === "check_number") {
    return "check/cc number";
  }

  return field.replace("_", " ");
}

const itemizationRequiredFields = [
  "cash",
  "check",
  "creditCard",
  "foreignCheck",
  "wireTransfer",
  "misc",
] as const;

function parseAmount(value: unknown) {
  const parsed = Number.parseFloat(String(value || "").replace(/[$,]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrency(value: unknown) {
  return parseAmount(value).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}

function isCurrencyField(field: string) {
  return currencyFields.includes(field as (typeof currencyFields)[number]);
}

function keyproofStorageKey(id: string) {
  return `keyproof:${id}`;
}

function getRequiredTotal(attachmentId: string | null, fallback: string | null) {
  if (attachmentId) {
    const saved = window.localStorage.getItem(keyproofStorageKey(attachmentId));

    if (saved) {
      try {
        const keyproof = JSON.parse(saved) as Record<string, string>;
        return itemizationRequiredFields.reduce(
          (total, field) => total + parseAmount(keyproof[field]),
          0
        );
      } catch {
        window.localStorage.removeItem(keyproofStorageKey(attachmentId));
      }
    }
  }

  return parseAmount(fallback);
}

function makeInitialForm(type: string): ItemizationForm {
  return {
    type,
    amount: 0,
    payer: "",
    check_number: "",
    edi: "",
    poster: "",
    eob: "",
    unposted: 0,
    misc: 0,
    misc_type: "",
    notes: "",
    nick: 0,
    raul: 0,
    needs: "",
    from: "",
    to: "",
  };
}

function applyPosterBalance(form: ItemizationForm) {
  const amount = parseAmount(form.amount);
  const poster = String(form.poster || "");

  if (poster === "Nick") {
    return { ...form, nick: formatCurrency(amount), raul: formatCurrency(0) };
  }

  if (poster === "Raul") {
    return { ...form, nick: formatCurrency(0), raul: formatCurrency(amount) };
  }

  return { ...form, nick: formatCurrency(0), raul: formatCurrency(0) };
}

export default function Itemization() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const attachmentId = searchParams.get("attachmentId");
  const day = searchParams.get("day");
  const site = searchParams.get("site") || "";
  const requiredTotal = getRequiredTotal(attachmentId, searchParams.get("requiredTotal"));
  const importId = Number(attachmentId || 0);
  const storageKey = attachmentId ? `itemization:${attachmentId}` : "";
  const [items, setItems] = useState<ItemizationItem[]>(() => {
    if (!storageKey) return [];

    const saved = window.localStorage.getItem(storageKey);
    if (!saved) return [];

    try {
      return JSON.parse(saved) as ItemizationItem[];
    } catch {
      window.localStorage.removeItem(storageKey);
      return [];
    }
  });
  const [form, setForm] = useState<ItemizationForm>(() => makeInitialForm(site));
  const [editingId, setEditingId] = useState<number | null>(null);

  const fieldNames = useMemo(() => Object.keys(form), [form]);

  const saveItems = (nextItems: ItemizationItem[]) => {
    setItems(nextItems);

    if (storageKey) {
      window.localStorage.setItem(storageKey, JSON.stringify(nextItems));
    }
  };

  const updateField = (field: string, value: string) => {
    setForm((prev) => {
      const next = { ...prev, [field]: value };

      if (field === "amount" || field === "poster") {
        return applyPosterBalance(next);
      }

      return next;
    });
  };

  const addItem = async () => {
    const normalizedForm = { ...form };

    numericFields.forEach((field) => {
      normalizedForm[field] = parseAmount(normalizedForm[field]);
    });

    const newItem: ItemizationItem = {
      ...normalizedForm,
      id: editingId || Date.now(),
      importId,
      type: String(normalizedForm.type || ""),
      amount: Number(normalizedForm.amount || 0),
      misc: Number(normalizedForm.misc || 0),
    };

    if (editingId) {
      saveItems(items.map((item) => (item.id === editingId ? newItem : item)));
    } else {
      saveItems([...items, newItem]);
    }

    setEditingId(null);
    setForm(makeInitialForm(site));
  };

  const formatCurrencyField = (field: string) => {
    if (!isCurrencyField(field)) return;

    setForm((prev) => ({ ...prev, [field]: formatCurrency(prev[field]) }));
  };

  const total = items.reduce((sum, item) => sum + Number(item.amount), 0);
  const remaining = requiredTotal - total;

  const startEdit = (id: number) => {
    const item = items.find((entry) => entry.id === id);
    if (!item) return;

    setEditingId(id);
    setForm(applyPosterBalance({ ...makeInitialForm(site), ...item, type: site }));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(makeInitialForm(site));
  };

  const goBackToKeyproof = () => {
    const params = new URLSearchParams();

    if (attachmentId) {
      params.set("attachmentId", attachmentId);
    }

    if (day) {
      params.set("day", day);
    }

    if (site) {
      params.set("site", site);
    }

    navigate(`/keyproof${params.toString() ? `?${params.toString()}` : ""}`);
  };

  const goToBalsheet = () => {
    const params = new URLSearchParams();

    if (attachmentId) {
      params.set("attachmentId", attachmentId);
    }

    if (day) {
      params.set("day", day);
    }

    if (site) {
      params.set("site", site);
    }

    navigate(`/balsheet/bulk${params.toString() ? `?${params.toString()}` : ""}`);
  };

  return (
    <div style={{ padding: "20px", textAlign: "left" }}>
      <h2>Itemization</h2>
      {attachmentId && (
        <div style={{ marginBottom: "16px", color: "#555" }}>
          Attachment #{attachmentId}
        </div>
      )}

      <div
        style={{
          marginBottom: "20px",
          padding: "12px 14px",
          border: "1px solid #c8d0dc",
          borderRadius: "6px",
          background: "#fff",
          display: "flex",
          gap: "20px",
          flexWrap: "wrap",
          fontWeight: 700,
        }}
      >
        <span>Requires Itemization: ${requiredTotal.toFixed(2)}</span>
        <span>Itemized: ${total.toFixed(2)}</span>
        <span style={{ color: Math.abs(remaining) < 0.005 ? "#1f6b2a" : "#a15c00" }}>
          Difference: ${remaining.toFixed(2)}
        </span>
      </div>

      <div style={{ marginBottom: "20px" }}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {fieldNames.map((field) => (
            <div
              key={field}
              style={{
                display: "grid",
                gridTemplateColumns: "180px 240px",
                columnGap: "12px",
                alignItems: "center",
              }}
            >
              <label
                style={{
                  textAlign: "right",
                  paddingRight: "4px",
                }}
              >
                {fieldLabel(field)}
              </label>
              {field === "poster" ? (
                <select
                  value={form.poster}
                  style={{ width: "220px", justifySelf: "start" }}
                  onChange={(event) => updateField("poster", event.target.value)}
                >
                  <option value="">Select poster</option>
                  {posterOptions.map((poster) => (
                    <option key={poster} value={poster}>
                      {poster}
                    </option>
                  ))}
                </select>
              ) : field === "edi" || field === "eob" ? (
                <select
                  value={form[field]}
                  style={{ width: "220px", justifySelf: "start" }}
                  onChange={(event) => updateField(field, event.target.value)}
                >
                  <option value="">Select</option>
                  {yesNoOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : field === "from" || field === "to" ? (
                <input
                  type="date"
                  value={form[field]}
                  style={{ width: "220px", justifySelf: "start" }}
                  onChange={(event) => updateField(field, event.target.value)}
                />
              ) : (
                <input
                type="text"
                inputMode={isCurrencyField(field) ? "decimal" : undefined}
                value={form[field]}
                readOnly={field === "type" || field === "nick" || field === "raul"}
                  style={{
                    width: "220px",
                    justifySelf: "start",
                    ...(field === "type" || field === "nick" || field === "raul"
                      ? { background: "#f2f5f9", color: "#555" }
                      : {}),
                }}
                onChange={(event) => updateField(field, event.target.value)}
                onBlur={() => formatCurrencyField(field)}
              />
              )}
            </div>
          ))}
        </div>

        <button
          onClick={addItem}
          style={{ padding: "10px 20px", marginTop: "10px" }}
        >
          {editingId ? "Save Item" : "Add Item"}
        </button>
        {editingId && (
          <button
            onClick={cancelEdit}
            style={{ padding: "10px 20px", marginTop: "10px", marginLeft: "10px" }}
          >
            Cancel Edit
          </button>
        )}
      </div>

      <ItemizationGrid
        items={items}
        onEdit={startEdit}
      />

      <div style={{ marginTop: "20px", fontSize: "20px", fontWeight: "bold" }}>
        Total: ${total.toFixed(2)}
      </div>

      <button
        onClick={goBackToKeyproof}
        style={{ padding: "10px 20px", marginTop: "20px" }}
      >
        Back to Keyproof
      </button>
      <button
        onClick={goToBalsheet}
        style={{ padding: "10px 20px", marginTop: "20px", marginLeft: "10px" }}
      >
        Go to Balsheet
      </button>
    </div>
  );
}
