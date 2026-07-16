import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { approveAttachment } from "../api/attachmentreview_api";
import { getSites } from "../api/keyproof_api";
import type { KeyproofDraft, SiteOption } from "../api/keyproof_api";
import "./keyproof.css";

const snapshotUrl = (id: string) => `http://localhost:8000/attachments/${id}/snapshot`;

const emptyForm: Omit<KeyproofDraft, "attachmentId"> = {
  site: "",
  cash: "",
  check: "",
  creditCard: "",
  eft: "",
  lockbox: "",
  foreignCheck: "",
  wireTransfer: "",
  misc: "",
  miscDescription: "",
};

const moneyFields: Array<keyof Omit<KeyproofDraft, "attachmentId" | "site" | "miscDescription">> = [
  "cash",
  "check",
  "creditCard",
  "eft",
  "lockbox",
  "foreignCheck",
  "wireTransfer",
  "misc",
];

const itemizationRequiredFields = [
  "cash",
  "check",
  "creditCard",
  "foreignCheck",
  "wireTransfer",
  "misc",
] as const;

function parseAmount(value: string) {
  const parsed = Number.parseFloat(String(value || "").replace(/[$,]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrency(value: number) {
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}

function keyproofStorageKey(id: string) {
  return `keyproof:${id}`;
}

function itemizationStorageKey(id: string) {
  return `itemization:${id}`;
}

export default function Keyproof() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const attachmentId = searchParams.get("attachmentId");
  const day = searchParams.get("day");
  const siteFromParams = searchParams.get("site") || "";
  const [form, setForm] = useState({ ...emptyForm, site: siteFromParams });
  const [sites, setSites] = useState<SiteOption[]>([]);
  const [siteLoadError, setSiteLoadError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [menuOpen, setMenuOpen] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [matchWarning, setMatchWarning] = useState<string | null>(null);
  const [confirmReady, setConfirmReady] = useState(false);

  useEffect(() => {
    getSites()
      .then((response) => {
        setSites(response.data);
        setSiteLoadError(null);
      })
      .catch((err) => {
        setSites([]);
        setSiteLoadError(err instanceof Error ? err.message : "Failed to load sites");
      });
  }, []);

  useEffect(() => {
    if (!attachmentId) return;

    const saved = window.localStorage.getItem(keyproofStorageKey(attachmentId));
    if (!saved) return;

    try {
      const parsed = JSON.parse(saved) as Partial<typeof emptyForm>;
      setForm((current) => ({ ...current, ...parsed, site: parsed.site || siteFromParams || current.site }));
    } catch {
      window.localStorage.removeItem(keyproofStorageKey(attachmentId));
    }
  }, [attachmentId, siteFromParams]);

  const activeSites = useMemo(
    () => sites.filter((site) => site.active === 1),
    [sites]
  );

  function updateField(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function zoomIn() {
    setZoom((current) => Math.min(current + 0.25, 3));
  }

  function zoomOut() {
    setZoom((current) => Math.max(current - 0.25, 0.5));
  }

  function resetZoom() {
    setZoom(1);
  }

  function toggleMagnify() {
    setZoom((current) => (current === 1 ? 2 : 1));
  }

  const totalAmount = useMemo(
    () =>
      moneyFields.reduce((total, field) => {
        return total + parseAmount(form[field]);
      }, 0),
    [form]
  );

  const itemizationRequiredTotal = useMemo(
    () =>
      itemizationRequiredFields.reduce((total, field) => total + parseAmount(form[field]), 0),
    [form]
  );

  function goBackToReview() {
    const params = new URLSearchParams();

    if (day) {
      params.set("day", day);
    }

    navigate(`/attachments${params.toString() ? `?${params.toString()}` : ""}`);
  }

  function goToDefineSites() {
    const params = new URLSearchParams();

    if (attachmentId) {
      params.set("attachmentId", attachmentId);
    }

    if (day) {
      params.set("day", day);
    }

    setMenuOpen(false);
    navigate(`/sites${params.toString() ? `?${params.toString()}` : ""}`);
  }

  function goToItemization() {
    const params = new URLSearchParams();

    if (attachmentId) {
      params.set("attachmentId", attachmentId);
      window.localStorage.setItem(keyproofStorageKey(attachmentId), JSON.stringify(form));
    }

    if (day) {
      params.set("day", day);
    }

    if (form.site) {
      params.set("site", form.site);
    }

    params.set("requiredTotal", itemizationRequiredTotal.toFixed(2));

    navigate(`/itemization?${params.toString()}`);
  }

  function getSavedItemizationTotal() {
    if (!attachmentId) return 0;

    const saved = window.localStorage.getItem(itemizationStorageKey(attachmentId));
    if (!saved) return 0;

    try {
      const items = JSON.parse(saved) as Array<{ amount?: number | string }>;
      return items.reduce((total, item) => total + Number(item.amount || 0), 0);
    } catch {
      return 0;
    }
  }

  function runBalanceCheck() {
    const itemizationTotal = getSavedItemizationTotal();
    const difference = Math.abs(itemizationRequiredTotal - itemizationTotal);

    if (itemizationRequiredTotal > 0 && difference > 0.005) {
      return {
        ok: false,
        message: `Keyproof requiring itemization is $${itemizationRequiredTotal.toFixed(2)}, but itemization totals $${itemizationTotal.toFixed(2)}. EFT and Lockbox are excluded.`,
      };
    }

    return {
      ok: true,
      message: "OK for confirmation.",
    };
  }

  function saveKeyproof() {
    if (!attachmentId) return;

    window.localStorage.setItem(keyproofStorageKey(attachmentId), JSON.stringify(form));

    const result = runBalanceCheck();

    if (result.ok) {
      setMatchWarning(null);
      setConfirmReady(true);
    } else {
      setMatchWarning(result.message);
      setConfirmReady(false);
    }

    setSaveMessage("Keyproof saved.");
  }

  async function confirmAndSave() {
    if (!attachmentId) return;

    window.localStorage.setItem(keyproofStorageKey(attachmentId), JSON.stringify(form));

    const result = runBalanceCheck();

    if (!result.ok) {
      setMatchWarning(result.message);
      setConfirmReady(false);
      setSaveMessage(null);
      return;
    }

    setMatchWarning(null);
    setConfirmReady(true);
    setSaveMessage(result.message);

    await approveAttachment(Number(attachmentId));
    window.localStorage.removeItem(keyproofStorageKey(attachmentId));
    window.localStorage.removeItem(itemizationStorageKey(attachmentId));
    navigate("/");
  }

  if (!attachmentId) {
    return (
      <main className="keyproof-container">
        <section className="keyproof-empty">
          <h1 className="keyproof-title">Keyproof</h1>
          <p>No attachment selected.</p>
          <button className="keyproof-btn" onClick={goBackToReview}>
            Back
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="keyproof-container">
      <section className="keyproof-left">
        <div className="keyproof-viewer-toolbar">
          <button className="keyproof-icon-btn" type="button" onClick={zoomOut} title="Zoom out">
            -
          </button>
          <button className="keyproof-icon-btn" type="button" onClick={resetZoom} title="Reset zoom">
            {Math.round(zoom * 100)}%
          </button>
          <button className="keyproof-icon-btn" type="button" onClick={zoomIn} title="Zoom in">
            +
          </button>
          <button className="keyproof-icon-btn" type="button" onClick={toggleMagnify} title="Toggle magnify">
            Magnify
          </button>
        </div>

        <div className="keyproof-image-viewer">
          <img
            className="keyproof-image"
            src={snapshotUrl(attachmentId)}
            alt={`Attachment ${attachmentId}`}
            style={{ transform: `scale(${zoom})` }}
            onClick={toggleMagnify}
          />
        </div>

        <div className="keyproof-buttons">
          <button className="keyproof-btn cancel" onClick={goBackToReview}>
            Back
          </button>
        </div>
      </section>

      <section className="keyproof-right">
        <div className="keyproof-header">
          <h1 className="keyproof-title">Keyproof</h1>
          <div className="keyproof-menu">
            <button
              className="keyproof-menu-button"
              type="button"
              onClick={() => setMenuOpen((current) => !current)}
              title="More options"
              aria-label="More options"
              aria-expanded={menuOpen}
            >
              ...
            </button>
            {menuOpen && (
              <div className="keyproof-menu-dropdown">
                <button type="button" onClick={goToDefineSites}>
                  Define Sites
                </button>
              </div>
            )}
          </div>
        </div>
        {siteLoadError && <div className="keyproof-error">{siteLoadError}</div>}

        <div className="keyproof-total">
          Total: {formatCurrency(totalAmount)}
        </div>
        {confirmReady && <div className="keyproof-success">OK for confirmation.</div>}
        {matchWarning && <div className="keyproof-warning">{matchWarning}</div>}
        {saveMessage && <div className="keyproof-success">{saveMessage}</div>}

        <details className="keyproof-section" open>
          <summary>Site</summary>
          <div className="keyproof-section-body">
            <div className="keyproof-field">
              <label htmlFor="site">Site</label>
              <select
                id="site"
                name="site"
                value={form.site}
                onChange={(event) => updateField("site", event.target.value)}
              >
                <option value="">Select site</option>
                {activeSites.map((site) => (
                  <option key={site.id} value={site.name}>
                    {site.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </details>

        <details className="keyproof-section" open>
          <summary>Cash, Check, Credit Card</summary>
          <div className="keyproof-section-body keyproof-grid">
            <MoneyField id="cash" label="Cash" value={form.cash} onChange={updateField} />
            <MoneyField id="check" label="Check" value={form.check} onChange={updateField} />
            <MoneyField id="creditCard" label="Credit Card" value={form.creditCard} onChange={updateField} />
          </div>
        </details>

        <details className="keyproof-section">
          <summary>EFT, Lockbox</summary>
          <div className="keyproof-section-body keyproof-grid">
            <MoneyField id="eft" label="EFT" value={form.eft} onChange={updateField} />
            <MoneyField id="lockbox" label="Lockbox" value={form.lockbox} onChange={updateField} />
          </div>
        </details>

        <details className="keyproof-section">
          <summary>Foreign Check, Wire Transfer</summary>
          <div className="keyproof-section-body keyproof-grid">
            <MoneyField id="foreignCheck" label="Foreign Check" value={form.foreignCheck} onChange={updateField} />
            <MoneyField id="wireTransfer" label="Wire Transfer" value={form.wireTransfer} onChange={updateField} />
          </div>
        </details>

        <details className="keyproof-section">
          <summary>Misc, Misc Description</summary>
          <div className="keyproof-section-body">
            <div className="keyproof-grid">
              <MoneyField id="misc" label="Misc" value={form.misc} onChange={updateField} />
            </div>
            <div className="keyproof-field">
              <label htmlFor="miscDescription">Misc Description</label>
              <textarea
                id="miscDescription"
                name="miscDescription"
                rows={4}
                value={form.miscDescription}
                onChange={(event) => updateField("miscDescription", event.target.value)}
              />
            </div>
          </div>
        </details>

        <div className="keyproof-action-row">
          <button className="keyproof-save" type="button" onClick={saveKeyproof}>
            Save Keyproof
          </button>
          <button className="keyproof-confirm-action" type="button" onClick={confirmAndSave}>
            Confirm and Save
          </button>
          <button className="keyproof-secondary-action" type="button" onClick={goToItemization}>
            Edit Itemization
          </button>
        </div>
      </section>
    </main>
  );
}

interface MoneyFieldProps {
  id: keyof Omit<KeyproofDraft, "attachmentId" | "site" | "miscDescription">;
  label: string;
  value: string;
  onChange: (field: keyof Omit<KeyproofDraft, "attachmentId">, value: string) => void;
}

function MoneyField({ id, label, value, onChange }: MoneyFieldProps) {
  return (
    <div className="keyproof-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={id}
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(id, event.target.value)}
      />
    </div>
  );
}
