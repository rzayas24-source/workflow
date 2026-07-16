// src/ScreenManager.tsx
import type { CSSProperties } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams } from "react-router-dom";

import ApprovedList from "./Screens/approvedlist";
import AttachmentReviewScreen from "./Screens/attachmentreview";
import BalanceCheck from "./Screens/balancecheck";
import Balsheet from "./Screens/balsheet";
import BalanceSheetMenu from "./Screens/balancesheetmenu";
import CompletionLabel from "./Screens/completionlabel";
import IntroScreen from "./Screens/introscreen";
import Itemization from "./Screens/itemization";
import Keyproof from "./Screens/keyproof";
import MainScreen from "./Screens/mainscreen";
import NextLoader from "./Screens/nextloader";
import Queue from "./Screens/queue";
import RejectList from "./Screens/rejectlist";
import SitesScreen from "./Screens/sitescreen";

function parseAmount(value: unknown) {
  const parsed = Number.parseFloat(String(value || "").replace(/[$,]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function readKeyproofTotal(attachmentId: string | null) {
  if (!attachmentId) return 0;

  const saved = window.localStorage.getItem(`keyproof:${attachmentId}`);
  if (!saved) return 0;

  try {
    const keyproof = JSON.parse(saved) as Record<string, string>;
    return ["cash", "check", "creditCard", "foreignCheck", "wireTransfer", "misc"].reduce(
      (total, field) => total + parseAmount(keyproof[field]),
      0
    );
  } catch {
    window.localStorage.removeItem(`keyproof:${attachmentId}`);
    return 0;
  }
}

function readItemizationTotal(attachmentId: string | null) {
  if (!attachmentId) return 0;

  const saved = window.localStorage.getItem(`itemization:${attachmentId}`);
  if (!saved) return 0;

  try {
    const items = JSON.parse(saved) as Array<{ amount?: number | string }>;
    return items.reduce((total, item) => total + Number(item.amount || 0), 0);
  } catch {
    window.localStorage.removeItem(`itemization:${attachmentId}`);
    return 0;
  }
}

function buildReviewParams(attachmentId: string | null, day: string | null, site?: string | null) {
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

  return params;
}

function QueueScreen() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const day = searchParams.get("day");

  return (
    <Queue
      onSelect={(id) => {
        const params = buildReviewParams(String(id), day);
        navigate(`/keyproof?${params.toString()}`);
      }}
    />
  );
}

function RejectListScreen() {
  return <RejectList />;
}

function BalanceCheckScreen() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const attachmentId = searchParams.get("attachmentId");
  const day = searchParams.get("day");
  const site = searchParams.get("site");
  const keyproofTotal = readKeyproofTotal(attachmentId);
  const itemizationTotal = readItemizationTotal(attachmentId);
  const flowParams = buildReviewParams(attachmentId, day, site);
  const itemizationParams = buildReviewParams(attachmentId, day, site);

  if (attachmentId) {
    itemizationParams.set("requiredTotal", keyproofTotal.toFixed(2));
  }

  const returnToQueue = day ? `/attachments?day=${encodeURIComponent(day)}` : "/attachments";

  return (
    <main style={balanceStyles.page}>
      <BalanceCheck
        keyproofTotal={keyproofTotal}
        itemizationTotal={itemizationTotal}
        onEditKeyproof={() => navigate(`/keyproof?${flowParams.toString()}`)}
        onEditItemization={() => navigate(`/itemization?${itemizationParams.toString()}`)}
        onAccept={() => navigate(returnToQueue)}
      />
    </main>
  );
}

function CompletionLabelScreen() {
  const navigate = useNavigate();

  return (
    <main style={balanceStyles.page}>
      <section style={balanceStyles.card}>
        <CompletionLabel />
        <button style={balanceStyles.button} type="button" onClick={() => navigate("/attachments")}>
          Back to Pending
        </button>
      </section>
    </main>
  );
}

function NextLoaderScreen() {
  const navigate = useNavigate();

  return (
    <main style={balanceStyles.page}>
      <NextLoader loadNext={() => navigate("/attachments")} />
    </main>
  );
}

export default function ScreenManager() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainScreen />} />
        <Route path="/home" element={<MainScreen />} />
        <Route path="/approved" element={<ApprovedList />} />
        <Route path="/attachments" element={<AttachmentReviewScreen />} />
        <Route path="/balance-sheet" element={<BalanceSheetMenu />} />
        <Route path="/balancecheck" element={<BalanceCheckScreen />} />
        <Route path="/balsheet" element={<Balsheet mode="view" />} />
        <Route path="/balsheet/view" element={<Balsheet mode="view" />} />
        <Route path="/balsheet/entry" element={<Balsheet mode="entry" />} />
        <Route path="/balsheet/bulk" element={<Balsheet mode="bulk" />} />
        <Route path="/completionlabel" element={<CompletionLabelScreen />} />
        <Route path="/keyproof" element={<Keyproof />} />
        <Route path="/itemization" element={<Itemization />} />
        <Route path="/nextloader" element={<NextLoaderScreen />} />
        <Route path="/site" element={<IntroScreen />} />
        <Route path="/queue" element={<QueueScreen />} />
        <Route path="/rejectlist" element={<RejectListScreen />} />
        <Route path="/sites" element={<SitesScreen />} />
      </Routes>
    </BrowserRouter>
  );
}

const balanceStyles: Record<string, CSSProperties> = {
  page: {
    minHeight: "100vh",
    boxSizing: "border-box",
    padding: "28px",
    background: "#f6f7f9",
    color: "#1f2933",
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
  },
  card: {
    maxWidth: "760px",
    border: "1px solid #d9dee7",
    borderRadius: "8px",
    background: "#ffffff",
    padding: "20px",
  },
  button: {
    marginTop: "18px",
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
};
