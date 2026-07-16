import type { CSSProperties } from "react";
import { useNavigate } from "react-router-dom";

type WidgetTone = "blue" | "pink" | "mist" | "pearl";

interface WidgetCard {
  title: string;
  meta: string;
  tone: WidgetTone;
  action: string;
  path: string;
  footnote: string;
}

interface StatCard {
  label: string;
  value: string;
  detail: string;
}

export default function MainScreen() {
  const navigate = useNavigate();

  const widgets: WidgetCard[] = [
    {
      title: "Site Review",
      meta: "Open pending batches, review attachments, and keep the queue moving.",
      tone: "blue",
      action: "Open Site",
      path: "/site",
      footnote: "Pending queue",
    },
    {
      title: "Balance Sheet",
      meta: "Jump into Balsheet tools, entries, and the bulk posting flow.",
      tone: "pink",
      action: "Open Balance Sheet",
      path: "/balance-sheet",
      footnote: "Worksheet hub",
    },
    {
      title: "Approved Batches",
      meta: "Check completed files, confirmations, and review history.",
      tone: "mist",
      action: "Open Approved",
      path: "/approved",
      footnote: "Review complete",
    },
    {
      title: "Image Renfrew",
      meta: "A preview tile for the restored icon and banner system.",
      tone: "pearl",
      action: "View Preview",
      path: "/site",
      footnote: "Brand tile",
    },
  ];

  const stats: StatCard[] = [
    {
      label: "Focus",
      value: "Pending review",
      detail: "Keep the attachment queue moving with a calmer workspace.",
    },
    {
      label: "Flow",
      value: "Keyproof + Itemization",
      detail: "One smooth route from review to balance check.",
    },
    {
      label: "Theme",
      value: "Baby blue / pink / grey",
      detail: "Soft contrast, airy spacing, and a more premium feel.",
    },
  ];

  return (
    <main style={styles.shell}>
      <div style={styles.glowBlue} />
      <div style={styles.glowPink} />

      <aside style={styles.sidebar}>
        <div style={styles.brandWrap}>
          <div style={styles.brandMark} aria-hidden="true">
            <img src="/favicon.svg" alt="" style={styles.brandMarkImage} />
          </div>
          <div style={styles.brandWomenMark} aria-hidden="true">
            <img src="/renfrew-womenline.png" alt="" style={styles.brandWomenImage} />
          </div>
        </div>

        <p style={styles.sidebarCopy}>
          A soft, polished command center for the review flow, balance sheet, and completed batches.
        </p>

        <nav style={styles.navStack} aria-label="Main navigation">
          <button className="sidebar-nav-button" style={styles.navButton} type="button" onClick={() => navigate("/")}>
            <span style={styles.navButtonLabel}>Main</span>
            <span className="sidebar-nav-button__glyph" style={styles.navButtonGlyph}>↗</span>
          </button>
          <button className="sidebar-nav-button" style={styles.navButton} type="button" onClick={() => navigate("/site")}>
            <span style={styles.navButtonLabel}>Site</span>
            <span className="sidebar-nav-button__glyph" style={styles.navButtonGlyph}>↗</span>
          </button>
          <button className="sidebar-nav-button" style={styles.navButton} type="button" onClick={() => navigate("/balance-sheet")}>
            <span style={styles.navButtonLabel}>Balance Sheet</span>
            <span className="sidebar-nav-button__glyph" style={styles.navButtonGlyph}>↗</span>
          </button>
          <button className="sidebar-nav-button" style={styles.navButton} type="button" onClick={() => navigate("/approved")}>
            <span style={styles.navButtonLabel}>Approved Batches</span>
            <span className="sidebar-nav-button__glyph" style={styles.navButtonGlyph}>↗</span>
          </button>
        </nav>

        <div style={styles.sidebarCard}>
          <div style={styles.sidebarCardLabel}>Today</div>
          <div style={styles.sidebarCardValue}>Gentle, focused, clear</div>
          <div style={styles.sidebarCardMeta}>
            The whole workspace is tuned to feel lighter and more modern without losing the workflow.
          </div>
        </div>
      </aside>

      <section style={styles.content}>
        <section style={styles.heroShell}>
          <div style={styles.heroCopy}>
            <div style={styles.kicker}>Main screen</div>
            <div style={styles.heroWordmarkWrap}>
              <img
                src="/renfrewplus-banner.png"
                alt="RenfrewPlus wordmark"
                style={styles.heroWordmark}
              />
            </div>
            <p style={styles.subtitle}>
              A calm workspace for review, approvals, and balance-sheet work.
            </p>

            <div style={styles.heroActions}>
              <button style={styles.primaryButton} type="button" onClick={() => navigate("/site")}>
                Continue Review
              </button>
              <button style={styles.secondaryButton} type="button" onClick={() => navigate("/balance-sheet")}>
                Balance Sheet
              </button>
            </div>
          </div>

          <div style={styles.heroArt}>
            <div style={styles.heroLogoCard}>
              <img src="/renfrew-gazebo.png" alt="Renfrew gazebo mark" style={styles.heroLogoImage} />
            </div>

            <div style={styles.heroStatusCard}>
              <div style={styles.heroStatusTop}>
                <span style={styles.statusPill}>Live workspace</span>
                <span style={styles.statusDot} />
              </div>
              <div style={styles.heroStatusTitle}>Soft launch look</div>
              <div style={styles.heroStatusText}>
                Baby blue, pink, and light grey for a calmer first impression.
              </div>
            </div>
          </div>
        </section>

        <section style={styles.statsGrid}>
          {stats.map((stat) => (
            <article key={stat.label} style={styles.statCard}>
              <div style={styles.statLabel}>{stat.label}</div>
              <div style={styles.statValue}>{stat.value}</div>
              <div style={styles.statDetail}>{stat.detail}</div>
            </article>
          ))}
        </section>

        <section style={styles.widgetSection}>
          <div style={styles.sectionHeader}>
            <div>
              <div style={styles.sectionKicker}>Widgets</div>
              <h2 style={styles.sectionTitle}>Everything feels connected</h2>
            </div>
            <div style={styles.sectionMeta}>
              The four main paths are still here, but now they live in a much softer, more premium frame.
            </div>
          </div>

          <div style={styles.widgetGrid}>
            {widgets.map((widget) => (
              <button
                key={widget.title}
                type="button"
                onClick={() => navigate(widget.path)}
                style={{
                  ...styles.widgetCard,
                  ...toneStyles[widget.tone],
                }}
              >
                <div style={styles.widgetTop}>
                  <div style={styles.widgetBadge}>{widget.footnote}</div>
                </div>
                <div style={styles.widgetBody}>
                  <div style={styles.widgetTitle}>{widget.title}</div>
                  <div style={styles.widgetMeta}>{widget.meta}</div>
                </div>
                <div style={styles.widgetAction}>{widget.action}</div>
              </button>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  shell: {
    minHeight: "100vh",
    padding: "18px",
    display: "grid",
    gridTemplateColumns: "250px minmax(0, 1fr)",
    gap: "18px",
    position: "relative",
    overflow: "hidden",
    color: "#16304d",
  },
  glowBlue: {
    position: "absolute",
    top: "-120px",
    left: "-120px",
    width: "360px",
    height: "360px",
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(146, 198, 255, 0.45) 0%, rgba(146, 198, 255, 0) 70%)",
    filter: "blur(10px)",
    pointerEvents: "none",
  },
  glowPink: {
    position: "absolute",
    right: "-100px",
    top: "110px",
    width: "320px",
    height: "320px",
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(255, 186, 213, 0.42) 0%, rgba(255, 186, 213, 0) 72%)",
    filter: "blur(10px)",
    pointerEvents: "none",
  },
  sidebar: {
    position: "relative",
    zIndex: 1,
    padding: "18px 16px",
    borderRadius: "28px",
    border: "1px solid rgba(140, 160, 184, 0.22)",
    background: "rgba(255, 255, 255, 0.72)",
    backdropFilter: "blur(18px)",
    boxShadow: "0 24px 60px rgba(52, 84, 120, 0.10)",
  },
  brandWrap: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    justifyContent: "flex-start",
    paddingBottom: "14px",
    marginBottom: "16px",
    borderBottom: "1px solid rgba(140, 160, 184, 0.18)",
  },
  brandMark: {
    width: "52px",
    height: "52px",
    borderRadius: "14px",
    display: "grid",
    placeItems: "center",
    background: "rgba(255,255,255,0.76)",
    border: "1px solid rgba(140, 160, 184, 0.14)",
    boxShadow: "0 12px 22px rgba(95, 128, 172, 0.08)",
    overflow: "hidden",
    flexShrink: 0,
  },
  brandMarkImage: {
    width: "88%",
    height: "88%",
    objectFit: "contain",
    objectPosition: "center",
  },
  brandWomenMark: {
    width: "104px",
    height: "52px",
    borderRadius: "14px",
    display: "grid",
    placeItems: "center",
    background: "rgba(255,255,255,0.64)",
    border: "1px solid rgba(140, 160, 184, 0.10)",
    boxShadow: "0 10px 18px rgba(95, 128, 172, 0.06)",
    overflow: "hidden",
    flexShrink: 0,
  },
  brandWomenImage: {
    width: "100%",
    height: "100%",
    objectFit: "contain",
  },
  sidebarCopy: {
    margin: "0 0 16px",
    fontSize: "14px",
    lineHeight: 1.6,
    color: "#516579",
  },
  navStack: {
    display: "grid",
    gap: "10px",
  },
  navButton: {
    height: "46px",
    border: "1px solid rgba(140, 160, 184, 0.20)",
    borderRadius: "16px",
    background:
      "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(236,245,255,0.95) 54%, rgba(255,236,244,0.92) 100%)",
    color: "#16304d",
    textAlign: "left",
    padding: "0 14px",
    fontWeight: 700,
    cursor: "pointer",
    boxShadow: "0 12px 26px rgba(52, 84, 120, 0.08)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    letterSpacing: "0.01em",
  },
  navButtonLabel: {
    fontSize: "14px",
    fontWeight: 800,
  },
  navButtonGlyph: {
    width: "22px",
    height: "22px",
    display: "grid",
    placeItems: "center",
    borderRadius: "999px",
    background: "rgba(255,255,255,0.76)",
    color: "#8aa5c6",
    fontSize: "12px",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.7)",
  },
  sidebarCard: {
    marginTop: "18px",
    padding: "16px",
    borderRadius: "20px",
    background: "linear-gradient(135deg, rgba(235, 245, 255, 0.95) 0%, rgba(255, 234, 243, 0.90) 100%)",
    border: "1px solid rgba(176, 194, 218, 0.22)",
  },
  sidebarCardLabel: {
    fontSize: "12px",
    textTransform: "uppercase",
    letterSpacing: "0.12em",
    color: "#6d7f93",
    fontWeight: 800,
    marginBottom: "8px",
  },
  sidebarCardValue: {
    fontSize: "18px",
    fontWeight: 800,
    marginBottom: "8px",
  },
  sidebarCardMeta: {
    fontSize: "13px",
    lineHeight: 1.55,
    color: "#5d7187",
  },
  content: {
    position: "relative",
    zIndex: 1,
    minWidth: 0,
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  heroShell: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.2fr) minmax(300px, 0.9fr)",
    gap: "18px",
    alignItems: "stretch",
    padding: "24px",
    borderRadius: "32px",
    border: "1px solid rgba(140, 160, 184, 0.20)",
    background: "linear-gradient(135deg, rgba(255,255,255,0.90) 0%, rgba(248,250,253,0.88) 50%, rgba(255,244,248,0.92) 100%)",
    boxShadow: "0 24px 60px rgba(52, 84, 120, 0.08)",
  },
  heroCopy: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    minWidth: 0,
  },
  heroWordmarkWrap: {
    maxWidth: "540px",
    padding: "0 0 6px",
  },
  heroWordmark: {
    display: "block",
    width: "100%",
    height: "auto",
  },
  kicker: {
    textTransform: "uppercase",
    letterSpacing: "0.2em",
    fontSize: "12px",
    fontWeight: 800,
    color: "#74879c",
    marginBottom: "10px",
  },
  subtitle: {
    margin: "8px 0 0",
    maxWidth: "760px",
    fontSize: "16px",
    lineHeight: 1.7,
    color: "#536579",
  },
  heroActions: {
    display: "flex",
    flexWrap: "wrap",
    gap: "12px",
    marginTop: "22px",
  },
  primaryButton: {
    height: "46px",
    padding: "0 18px",
    border: 0,
    borderRadius: "16px",
    background: "#98d4ff",
    color: "#0f2238",
    fontWeight: 800,
    boxShadow: "0 14px 26px rgba(152, 212, 255, 0.24)",
    cursor: "pointer",
  },
  secondaryButton: {
    height: "46px",
    padding: "0 18px",
    border: "1px solid rgba(140, 160, 184, 0.24)",
    borderRadius: "16px",
    background: "rgba(255,255,255,0.76)",
    color: "#16304d",
    fontWeight: 800,
    boxShadow: "0 12px 24px rgba(52, 84, 120, 0.06)",
    cursor: "pointer",
  },
  heroArt: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  heroLogoCard: {
    flex: 1,
    minHeight: "210px",
    padding: "18px",
    borderRadius: "28px",
    background: "rgba(255,255,255,0.94)",
    border: "1px solid rgba(140, 160, 184, 0.12)",
    display: "grid",
    placeItems: "center",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.55), 0 18px 34px rgba(52, 84, 120, 0.08)",
  },
  heroLogoImage: {
    width: "100%",
    maxWidth: "320px",
    height: "auto",
    display: "block",
  },
  heroStatusCard: {
    padding: "16px 18px",
    borderRadius: "24px",
    background: "linear-gradient(135deg, rgba(226, 243, 255, 0.98) 0%, rgba(255, 235, 244, 0.96) 100%)",
    border: "1px solid rgba(140, 160, 184, 0.18)",
  },
  heroStatusTop: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "10px",
    marginBottom: "10px",
  },
  statusPill: {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: "999px",
    padding: "6px 10px",
    background: "rgba(255,255,255,0.8)",
    color: "#4f647a",
    fontSize: "12px",
    fontWeight: 800,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  statusDot: {
    width: "11px",
    height: "11px",
    borderRadius: "50%",
    background: "#95c6ff",
    boxShadow: "0 0 0 6px rgba(149, 198, 255, 0.20)",
    flexShrink: 0,
  },
  heroStatusTitle: {
    fontSize: "18px",
    fontWeight: 800,
    marginBottom: "8px",
    color: "#16304d",
  },
  heroStatusText: {
    fontSize: "14px",
    lineHeight: 1.6,
    color: "#5d7187",
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    gap: "14px",
  },
  statCard: {
    padding: "18px",
    borderRadius: "24px",
    background: "rgba(255,255,255,0.78)",
    border: "1px solid rgba(140, 160, 184, 0.18)",
    boxShadow: "0 18px 36px rgba(52, 84, 120, 0.06)",
    minHeight: "142px",
  },
  statLabel: {
    textTransform: "uppercase",
    letterSpacing: "0.16em",
    fontSize: "11px",
    color: "#74879c",
    fontWeight: 800,
    marginBottom: "10px",
  },
  statValue: {
    fontSize: "20px",
    fontWeight: 800,
    color: "#10253d",
    marginBottom: "8px",
  },
  statDetail: {
    fontSize: "14px",
    lineHeight: 1.6,
    color: "#5d7187",
  },
  widgetSection: {
    padding: "22px",
    borderRadius: "30px",
    border: "1px solid rgba(140, 160, 184, 0.18)",
    background: "rgba(255,255,255,0.64)",
    boxShadow: "0 24px 60px rgba(52, 84, 120, 0.06)",
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "14px",
    alignItems: "end",
    marginBottom: "16px",
  },
  sectionKicker: {
    textTransform: "uppercase",
    letterSpacing: "0.16em",
    fontSize: "11px",
    color: "#74879c",
    fontWeight: 800,
    marginBottom: "8px",
  },
  sectionTitle: {
    margin: 0,
    fontSize: "28px",
    lineHeight: 1.08,
    letterSpacing: "-0.03em",
    color: "#10253d",
  },
  sectionMeta: {
    maxWidth: "460px",
    fontSize: "14px",
    lineHeight: 1.6,
    color: "#5d7187",
  },
  widgetGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: "14px",
  },
  widgetCard: {
    minHeight: "190px",
    border: "0",
    borderRadius: "28px",
    padding: "18px",
    textAlign: "left",
    cursor: "pointer",
    boxShadow: "0 22px 40px rgba(52, 84, 120, 0.08)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    transition: "transform 160ms ease, box-shadow 160ms ease",
  },
  widgetTop: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
  },
  widgetBadge: {
    alignSelf: "start",
    borderRadius: "999px",
    padding: "7px 12px",
    fontSize: "11px",
    fontWeight: 800,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    background: "rgba(255,255,255,0.70)",
    color: "#16304d",
  },
  widgetBody: {
    paddingTop: "18px",
  },
  widgetTitle: {
    fontSize: "24px",
    fontWeight: 800,
    marginBottom: "8px",
    color: "#10253d",
  },
  widgetMeta: {
    fontSize: "15px",
    lineHeight: 1.6,
    color: "#526579",
    maxWidth: "360px",
  },
  widgetAction: {
    alignSelf: "start",
    marginTop: "18px",
    fontSize: "14px",
    fontWeight: 800,
    color: "#10253d",
  },
};

const toneStyles: Record<WidgetTone, CSSProperties> = {
  blue: {
    background:
      "linear-gradient(135deg, rgba(220, 239, 255, 0.98) 0%, rgba(246, 251, 255, 0.98) 100%)",
    border: "1px solid rgba(143, 200, 255, 0.22)",
  },
  pink: {
    background:
      "linear-gradient(135deg, rgba(255, 228, 240, 0.98) 0%, rgba(255, 248, 251, 0.98) 100%)",
    border: "1px solid rgba(255, 184, 214, 0.20)",
  },
  mist: {
    background:
      "linear-gradient(135deg, rgba(232, 244, 247, 0.98) 0%, rgba(249, 253, 254, 0.98) 100%)",
    border: "1px solid rgba(175, 215, 224, 0.18)",
  },
  pearl: {
    background:
      "linear-gradient(135deg, rgba(241, 242, 247, 0.98) 0%, rgba(252, 252, 255, 0.98) 100%)",
    border: "1px solid rgba(176, 194, 218, 0.20)",
  },
};
