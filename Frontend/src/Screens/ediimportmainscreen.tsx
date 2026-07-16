import type { CSSProperties, ChangeEvent } from "react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

const brandIconSrc = "/favicon.svg?v=renfrewplus-white-blue-20260706";

type ArchiveDetail = {
  file_name: string;
  html_files: number;
  trn_files: number;
  era_files: number;
  skipped_files: number;
  extracted_files?: string[];
};

type ArchiveSummary = {
  archives: ArchiveDetail[];
  totals: {
    archives: number;
    html_files: number;
    trn_files: number;
    era_files: number;
    skipped_files: number;
  };
};

type TrnQueue = {
  count: number;
  files: string[];
};

type EdiStageSummary = {
  staged_rows: number;
  batchnum?: string | null;
  first_transnum?: string | null;
  last_transnum?: string | null;
  message: string;
};

type EdiVettingSummary = {
  vetted_rows: number;
  accepted_rows?: number;
  duplicate_checks: string[];
  batchnum?: string | null;
  can_import: boolean;
  message: string;
};

export default function EdiImportMainScreen() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [highestEdiDate, setHighestEdiDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [selectedFileNames, setSelectedFileNames] = useState<string[]>([]);
  const [preview, setPreview] = useState<ArchiveSummary | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewExpanded, setPreviewExpanded] = useState(true);
  const [fileSelectedComplete, setFileSelectedComplete] = useState(false);
  const [loadComplete, setLoadComplete] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [trnQueue, setTrnQueue] = useState<TrnQueue>({ count: 0, files: [] });
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueComplete, setQueueComplete] = useState(false);
  const [queueMessage, setQueueMessage] = useState<string | null>(null);
  const [duplicateProtectionRows, setDuplicateProtectionRows] = useState<string[]>([]);
  const [duplicateProtectionExpanded, setDuplicateProtectionExpanded] = useState(true);
  const [queueExpanded, setQueueExpanded] = useState(true);
  const [staging, setStaging] = useState(false);
  const [stageComplete, setStageComplete] = useState(false);
  const [stageSummary, setStageSummary] = useState<EdiStageSummary | null>(null);
  const [stageMessage, setStageMessage] = useState<string | null>(null);
  const [vettingLoading, setVettingLoading] = useState(false);
  const [catalogComplete, setCatalogComplete] = useState(false);
  const [vettingSummary, setVettingSummary] = useState<EdiVettingSummary | null>(null);
  const [vettingMessage, setVettingMessage] = useState<string | null>(null);
  const [vettingDuplicatesExpanded, setVettingDuplicatesExpanded] = useState(true);
  const [confirmingImport, setConfirmingImport] = useState(false);
  const [confirmComplete, setConfirmComplete] = useState(false);
  const [resettingBatch, setResettingBatch] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadLatestDate() {
      try {
        const response = await fetch("http://localhost:8000/edi/latest-date");
        if (!response.ok) {
          throw new Error("Failed to load EDI date");
        }

        const data = await response.json();
        if (cancelled) return;
        setHighestEdiDate(data?.latest_date || null);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load EDI date");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadLatestDate();
    void refreshTrnQueue(true);
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshTrnQueue(clearMessage = false) {
    setQueueLoading(true);
    if (clearMessage) {
      setQueueMessage(null);
    }
    try {
      const response = await fetch("http://localhost:8000/edi/trn-queue");
      if (!response.ok) {
        throw new Error("Failed to load TRN queue");
      }

      const payload = await response.json();
      setTrnQueue({
        count: payload?.count || 0,
        files: Array.isArray(payload?.files) ? payload.files : [],
      });
    } catch (err) {
      setQueueMessage(err instanceof Error ? err.message : "Failed to load TRN queue");
    } finally {
      setQueueLoading(false);
    }
  }

  async function previewSelectedFiles(files: File[]) {
    if (files.length === 0) {
      setPreview(null);
      setUploadMessage("Please select one or more zip files first.");
      setFileSelectedComplete(false);
      return;
    }

    if (files.some((file) => !file.name.toLowerCase().endsWith(".zip"))) {
      setPreview(null);
      setUploadMessage("Please select zip files only.");
      setFileSelectedComplete(false);
      return;
    }

    setPreviewing(true);
    setUploadMessage(`Previewing ${files.length} zip file(s)...`);

    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }

      const response = await fetch("http://localhost:8000/edi/preview-selected", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Preview failed");
      }

      setPreview(payload);
      setFileSelectedComplete(true);
      setLoadComplete(false);
      setStageComplete(false);
      setCatalogComplete(false);
      setConfirmComplete(false);
      setUploadMessage(
        `Preview ready for ${payload?.totals?.archives || files.length} zip file(s).`
      );
    } catch (err) {
      setUploadMessage(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  async function uploadSelectedFiles() {
    if (selectedFiles.length === 0) {
      setUploadMessage("Please select one or more zip files first.");
      return;
    }

    setUploading(true);
    setUploadMessage(`Processing ${selectedFiles.length} zip file(s)...`);

    try {
      const formData = new FormData();
      for (const file of selectedFiles) {
        formData.append("files", file);
      }

      const response = await fetch("http://localhost:8000/edi/upload-selected", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Processing failed");
      }

      setUploadMessage(payload.message || `Processed ${selectedFiles.length} zip file(s).`);
      setPreview(payload);
      setLoadComplete(true);
      setStageComplete(false);
      setCatalogComplete(false);
      setConfirmComplete(false);
      setStageSummary(null);
      setVettingSummary(null);
      setQueueComplete(false);
      await refreshTrnQueue(true);
      await loadLatestDate();
    } catch (err) {
      setUploadMessage(err instanceof Error ? err.message : "Processing failed");
    } finally {
      setUploading(false);
    }
  }

  async function loadLatestDate() {
    try {
      const response = await fetch("http://localhost:8000/edi/latest-date");
      if (!response.ok) {
        throw new Error("Failed to load EDI date");
      }

      const data = await response.json();
      setHighestEdiDate(data?.latest_date || null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load EDI date");
    }
  }

  async function loadTrnQueue() {
    setQueueLoading(true);
    setQueueMessage("Loading TRN files into EDILoad...");
    setDuplicateProtectionRows([]);
    try {
      const response = await fetch("http://localhost:8000/edi/load-trn-queue", {
        method: "POST",
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "TRN load failed");
      }

      const duplicateRows = Array.isArray(payload?.duplicate_rows)
        ? payload.duplicate_rows.filter((value: unknown) => String(value || "").trim())
        : [];
      setDuplicateProtectionRows(duplicateRows);
      setDuplicateProtectionExpanded(true);
      setQueueMessage(null);
      setQueueComplete(true);
      setStageComplete(false);
      setCatalogComplete(false);
      setConfirmComplete(false);
      setStageSummary(null);
      setVettingSummary(null);
      await refreshTrnQueue(false);
    } catch (err) {
      setDuplicateProtectionRows([]);
      setQueueMessage(err instanceof Error ? err.message : "TRN load failed");
    } finally {
      setQueueLoading(false);
    }
  }

  async function stageEdiRows() {
    setStaging(true);
    setStageMessage("Staging EDILoad into EDIstage...");
    try {
      const response = await fetch("http://localhost:8000/edi/stage", {
        method: "POST",
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Failed to stage EDI rows");
      }

      setStageSummary(payload);
      setStageMessage(payload.message || "EDI staging complete.");
      setStageComplete(true);
      setCatalogComplete(false);
      setConfirmComplete(false);
      setVettingSummary(null);
    } catch (err) {
      setStageSummary(null);
      setStageMessage(err instanceof Error ? err.message : "Failed to stage EDI rows");
    } finally {
      setStaging(false);
    }
  }

  async function prepareEdiVetting() {
    setVettingLoading(true);
    setVettingMessage("Preparing EDI vetting catalog...");
    try {
      const response = await fetch("http://localhost:8000/edi/prepare-vetting", {
        method: "POST",
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Failed to prepare EDI vetting");
      }

      setVettingSummary(payload);
      setVettingDuplicatesExpanded(true);
      setVettingMessage(payload.message || "EDI vetting catalog ready.");
      setCatalogComplete(true);
      setConfirmComplete(false);
    } catch (err) {
      setVettingSummary(null);
      setVettingMessage(err instanceof Error ? err.message : "Failed to prepare EDI vetting");
    } finally {
      setVettingLoading(false);
    }
  }

  async function submitEdiImport(acceptNonDuplicates = false) {
    if (!vettingSummary) {
      setVettingMessage("Prepare the vetting catalog first.");
      return;
    }

    if (!acceptNonDuplicates && !vettingSummary.can_import) {
      setVettingMessage(vettingSummary.message || "Import is blocked until duplicate checks are cleared.");
      return;
    }

    const confirmed = window.confirm(
      acceptNonDuplicates
        ? `Import ${vettingSummary.accepted_rows ?? vettingSummary.vetted_rows} non-duplicate EDI row(s) now?`
        : `Import ${vettingSummary.vetted_rows} vetted EDI row(s) into EDI now?`
    );
    if (!confirmed) return;

    setConfirmingImport(true);
    setVettingMessage(acceptNonDuplicates ? "Importing non-duplicate rows into EDI..." : "Importing vetted rows into EDI...");
    try {
      const response = await fetch("http://localhost:8000/edi/confirm-import", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ accept_non_duplicates: acceptNonDuplicates }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Failed to import vetted EDI rows");
      }

      setVettingMessage(payload.message || "EDI import complete.");
      setConfirmComplete(true);
      await loadLatestDate();
    } catch (err) {
      setVettingMessage(err instanceof Error ? err.message : "Failed to import vetted EDI rows");
    } finally {
      setConfirmingImport(false);
    }
  }

  async function redoEdiBatch() {
    const confirmed = window.confirm(
      "This will clear EDILoad, EDIstage, and EDIvett. Type of file data will remain on disk. Continue?"
    );
    if (!confirmed) return;

    setResettingBatch(true);
    setVettingMessage("Clearing EDILoad, EDIstage, and EDIvett...");
    try {
      const response = await fetch("http://localhost:8000/edi/reset-working-tables", {
        method: "POST",
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || "Failed to reset EDI working tables");
      }

      setSelectedFiles([]);
      setSelectedFileNames([]);
      setPreview(null);
      setFileSelectedComplete(false);
      setLoadComplete(false);
      setStageComplete(false);
      setCatalogComplete(false);
      setConfirmComplete(false);
      setStageSummary(null);
      setVettingSummary(null);
      setVettingDuplicatesExpanded(true);
      setDuplicateProtectionRows([]);
      setDuplicateProtectionExpanded(true);
      setQueueMessage(payload.message || "Cleared EDILoad, EDIstage, and EDIvett.");
      setQueueComplete(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setVettingMessage(err instanceof Error ? err.message : "Failed to reset EDI working tables");
    } finally {
      setResettingBatch(false);
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

      setSelectedFiles(files);
      setSelectedFileNames(files.map((file) => file.name));
      setPreview(null);
      setFileSelectedComplete(false);
      setLoadComplete(false);
      setStageComplete(false);
      setCatalogComplete(false);
      setConfirmComplete(false);
      setStageSummary(null);
      setVettingSummary(null);
      setQueueComplete(false);
      setUploadMessage(null);
    void previewSelectedFiles(files);
    event.target.value = "";
  }

  function clearSelection() {
    setSelectedFiles([]);
    setSelectedFileNames([]);
    setPreview(null);
    setFileSelectedComplete(false);
    setLoadComplete(false);
    setStageComplete(false);
    setCatalogComplete(false);
    setConfirmComplete(false);
    setStageSummary(null);
    setVettingSummary(null);
    setQueueComplete(false);
    setUploadMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <main style={styles.shell}>
      <aside style={styles.sidebar}>
        <div style={styles.brandBlock}>
          <img style={styles.brandIcon} src={brandIconSrc} alt="" aria-hidden="true" />
          <div style={styles.brandText}>EDI Import</div>
        </div>
        <button className="main-nav-button" type="button" onClick={() => navigate("/eftload_main")}>
          <span className="main-nav-dot" />
          EFT Import
        </button>
        <button className="main-nav-button" type="button" onClick={() => navigate("/lockboximport_main")}>
          <span className="main-nav-dot" />
          Lockbox Import
        </button>
        <button className="main-nav-button" type="button" onClick={() => navigate("/ediimport_main")}>
          <span className="main-nav-dot" />
          EDI Import
        </button>
        <button style={styles.backButton} type="button" onClick={() => navigate("/import_main")}>
          Back
        </button>
      </aside>

      <section style={styles.content}>
        <div style={styles.panel}>
          <div style={styles.titleRow}>
            <div>
              <h1 style={styles.title}>Phase 1</h1>
              <div style={styles.subtitle}>
                Download the zip files from Optum, then select the range of zip files from Downloads.
              </div>
            </div>
            <div style={styles.dateCard}>
              <div style={styles.cardLabel}>Highest EDI Date on File</div>
              <div style={styles.cardValue}>
                {loading ? "Loading..." : error ? error : highestEdiDate || "No EDI dates found"}
              </div>
            </div>
          </div>

          <div style={styles.instructionsCard}>
            <div style={styles.sectionLabel}>How to obtain the files</div>
            <ol style={styles.stepList}>
              <li>Go to <span style={styles.mono}>https://portal.rpa.optum.com/ws_portal/login.jsp</span>.</li>
              <li>Navigate to <strong>Reporting and Metrics / Remittance Files</strong>.</li>
              <li>
                Set <strong>Process Dates = 1 month</strong>, <strong>File Workflow Status = No Status</strong>, and{" "}
                <strong>Results per page = 100</strong>.
              </li>
              <li>
                Download <strong>Ansi 835 (ERA)</strong>, <strong>Check Listing (TRN)</strong>, and{" "}
                <strong>EZ-EOB HTML</strong>.
              </li>
              <li>
                You can only download 100 at a time, so after you obtain your zips, you must archive to be able to
                obtain more. Click <strong>Show Bulk Update Options</strong>, then select <strong>Archive</strong>,
                then <strong>Submit</strong>. Repeat steps 4 and 5 for every 100 more.
              </li>
            </ol>
          </div>

          <div style={styles.noticeCard}>
            Your report should now be found in Downloads. Select the zip range and we will unpack the contents into
            the workflow folders.
          </div>

          <div style={styles.phaseCard}>
            <div style={styles.sectionLabel}>Phase 2</div>
            <h2 style={styles.phaseTitle}>Process zip files</h2>
            <div style={styles.phaseBody}>
              Pick the zip files from Downloads. We will extract only the files inside the zip and place them into{" "}
              <strong>1_HTML-EOB</strong>, <strong>2_ERA-835</strong>, or <strong>3_TRN_Bulk_Check</strong>.
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              multiple
              style={styles.hiddenInput}
              onChange={handleFileChange}
            />
            <div style={styles.phaseActionStack}>
              <div style={styles.phaseActionRow}>
                <button
                  style={styles.uploadButton}
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading || previewing}
                >
                  {previewing ? "Previewing..." : buttonLabel("Select Zip Files", fileSelectedComplete)}
                </button>
                {fileSelectedComplete && <span style={styles.completeBadge}>Selected</span>}
              </div>
              <div style={styles.phaseActionRow}>
                <button
                  style={styles.uploadButton}
                  type="button"
                  onClick={() => void uploadSelectedFiles()}
                  disabled={!selectedFiles.length || uploading}
                >
                  {uploading ? "Processing..." : buttonLabel("Extract Files to Folders", loadComplete)}
                </button>
                {loadComplete && <span style={styles.completeBadge}>Processed</span>}
              </div>
              <div style={styles.phaseActionRow}>
                <button style={styles.clearButton} type="button" onClick={clearSelection}>
                  Clear All
                </button>
                <button
                  style={styles.clearButton}
                  type="button"
                  onClick={() => setPreviewExpanded((value) => !value)}
                  aria-expanded={previewExpanded}
                  disabled={previewing}
                >
                  {previewExpanded ? "Hide Previews" : "Show Previews"}
                </button>
              </div>
            </div>

            {previewExpanded && (
              <>
                {selectedFileNames.length > 0 && (
                  <div style={styles.selectedFileList}>
                    <div style={styles.previewTitle}>Selected zip files</div>
                    {selectedFileNames.map((name) => (
                      <div key={name} style={styles.previewLine}>
                        {name}
                      </div>
                    ))}
                  </div>
                )}

                {preview && (
                  <div style={styles.previewCard}>
                    <div style={styles.previewTitle}>Preview</div>
                    <div style={styles.previewLine}>Zip files: {preview.totals.archives}</div>
                    <div style={styles.previewLine}>HTML files: {preview.totals.html_files}</div>
                    <div style={styles.previewLine}>TRN files: {preview.totals.trn_files}</div>
                    <div style={styles.previewLine}>ERA files: {preview.totals.era_files}</div>
                    <div style={styles.previewLine}>Skipped files: {preview.totals.skipped_files}</div>
                    {preview.archives?.length ? (
                      <div style={styles.archiveList}>
                        {preview.archives.map((archive) => (
                          <div key={archive.file_name} style={styles.archiveItem}>
                            <div style={styles.archiveName}>{archive.file_name}</div>
                            <div style={styles.previewLine}>
                              HTML {archive.html_files} | TRN {archive.trn_files} | ERA {archive.era_files} | Skipped{" "}
                              {archive.skipped_files}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                )}
              </>
            )}

            {uploadMessage && <div style={styles.uploadMessage}>{uploadMessage}</div>}
          </div>

          <div style={styles.phaseCard}>
            <div style={styles.sectionLabel}>Phase 3</div>
            <h2 style={styles.phaseTitle}>Queue TRN files</h2>
            <div style={styles.phaseBody}>
              The TRN files already sitting in <strong>3_TRN_Bulk_Check</strong> are queued below. Load them into
              <strong> EDILoad</strong>, and after a successful insert we will move each file to{" "}
              <strong>3_TRN_Bulk_Check/Loaded</strong>.
            </div>
            <div style={styles.buttonRow}>
              <button
                style={styles.uploadButton}
                type="button"
                onClick={() => void loadTrnQueue()}
                disabled={queueLoading || trnQueue.count === 0}
              >
                {queueLoading ? "Loading..." : buttonLabel("Load TRN to EDILoad", queueComplete)}
              </button>
              {queueComplete && <span style={styles.completeBadge}>Loaded</span>}
              <button
                style={styles.clearButton}
                type="button"
                onClick={() => setQueueExpanded((value) => !value)}
                disabled={queueLoading && trnQueue.count === 0}
              >
                {queueExpanded ? "Hide Queue" : "Show Queue"}
              </button>
            </div>
            {queueExpanded && (
              <div style={styles.previewCard}>
                <div style={styles.previewTitle}>TRN queue</div>
                <div style={styles.previewLine}>
                  Files waiting: {queueLoading ? "Loading..." : trnQueue.count}
                </div>
                {trnQueue.files.length > 0 ? (
                  <div style={styles.archiveList}>
                    {trnQueue.files.map((fileName) => (
                      <div key={fileName} style={styles.archiveItem}>
                        <div style={styles.archiveName}>{fileName}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={styles.previewLine}>No TRN files are waiting right now.</div>
                )}
              </div>
            )}
            {duplicateProtectionRows.length > 0 && (
              <div style={styles.previewCard}>
                <div style={styles.previewTitle}>Duplicate protection</div>
                <div style={styles.phaseActionRow}>
                  <div style={styles.previewLine}>
                    {duplicateProtectionRows.length} TRN row(s) were rejected because the check number already exists.
                  </div>
                  <button
                    style={styles.clearButton}
                    type="button"
                    onClick={() => setDuplicateProtectionExpanded((value) => !value)}
                    aria-expanded={duplicateProtectionExpanded}
                  >
                    {duplicateProtectionExpanded ? "Hide Results" : "Show Results"}
                  </button>
                </div>
                {duplicateProtectionExpanded && (
                  <div style={styles.archiveList}>
                    {duplicateProtectionRows.map((checkNumber) => (
                      <div key={checkNumber} style={styles.archiveItem}>
                        <div style={styles.archiveName}>{checkNumber}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {queueMessage && <div style={styles.uploadMessage}>{queueMessage}</div>}
          </div>

          <div style={styles.phaseCard}>
            <div style={styles.sectionLabel}>Phase 4</div>
            <h2 style={styles.phaseTitle}>Stage, vet, and approve</h2>
            <div style={styles.phaseBody}>
              Stage the loaded TRN rows into <strong>EDIstage</strong>, build the vetting catalog into{" "}
              <strong>EDIvett</strong>, and approve the final import into <strong>EDI</strong> only after you are
              happy with the results.
            </div>
            <div style={styles.phaseActionStack}>
              <div style={styles.phaseActionRow}>
                <button
                  style={styles.uploadButton}
                  type="button"
                  onClick={() => void stageEdiRows()}
                  disabled={staging}
                >
                  {staging ? "Staging..." : buttonLabel("Stage TRN to EDIstage", stageComplete)}
                </button>
                {stageComplete && <span style={styles.completeBadge}>Staged</span>}
              </div>
              <div style={styles.phaseActionRow}>
                <button
                  style={styles.uploadButton}
                  type="button"
                  onClick={() => void prepareEdiVetting()}
                  disabled={vettingLoading || !stageComplete}
                >
                  {vettingLoading ? "Preparing..." : buttonLabel("Build Import Catalog", catalogComplete)}
                </button>
                {catalogComplete && <span style={styles.completeBadge}>Catalog built</span>}
              </div>
              <div style={styles.phaseActionRow}>
                {vettingSummary?.duplicate_checks.length ? (
                  <>
                    <button
                      style={styles.uploadButton}
                      type="button"
                      onClick={() => void submitEdiImport(true)}
                      disabled={vettingLoading || confirmingImport || resettingBatch || confirmComplete}
                    >
                      {confirmingImport
                        ? "Importing..."
                        : buttonLabel("Accept Non-Duplicates", confirmComplete)}
                    </button>
                    <button
                      style={styles.clearButton}
                      type="button"
                      onClick={() => void redoEdiBatch()}
                      disabled={vettingLoading || confirmingImport || resettingBatch}
                    >
                      {resettingBatch ? "Clearing..." : "Redo Batch"}
                    </button>
                    {confirmComplete && <span style={styles.completeBadge}>Imported</span>}
                  </>
                ) : (
                  <>
                    <button
                      style={styles.confirmButton}
                      type="button"
                      onClick={() => void submitEdiImport(false)}
                      disabled={!vettingSummary?.can_import || vettingLoading || confirmingImport}
                    >
                      {confirmingImport ? "Importing..." : buttonLabel("Confirm Import to EDI", confirmComplete)}
                    </button>
                    {confirmComplete && <span style={styles.completeBadge}>Imported</span>}
                  </>
                )}
              </div>
            </div>
            {stageSummary && (
              <div style={styles.previewCard}>
                <div style={styles.previewTitle}>Stage summary</div>
                <div style={styles.previewLine}>Staged rows: {stageSummary.staged_rows}</div>
                <div style={styles.previewLine}>Batch: {stageSummary.batchnum || "None"}</div>
                <div style={styles.previewLine}>First transnum: {stageSummary.first_transnum || "None"}</div>
                <div style={styles.previewLine}>Last transnum: {stageSummary.last_transnum || "None"}</div>
              </div>
            )}
            {stageMessage && <div style={styles.uploadMessage}>{stageMessage}</div>}
            {vettingMessage && <div style={styles.uploadMessage}>{vettingMessage}</div>}
            {vettingSummary && (
              <div style={styles.previewCard}>
                <div style={styles.previewTitle}>Import diagnostics</div>
                <div style={styles.previewLine}>Total rows: {vettingSummary.vetted_rows}</div>
                <div style={styles.previewLine}>
                  Accepted rows: {vettingSummary.accepted_rows ?? vettingSummary.vetted_rows}
                </div>
                {vettingSummary.duplicate_checks.length > 0 && (
                  <div style={styles.previewLine}>
                    Duplicate rejections: {vettingSummary.duplicate_checks.length}
                  </div>
                )}
                <div style={styles.previewLine}>Batch: {vettingSummary.batchnum || "None"}</div>
                <div style={styles.previewLine}>Import allowed: {vettingSummary.can_import ? "Yes" : "No"}</div>
                {vettingSummary.duplicate_checks.length > 0 && (
                  <div style={styles.previewCard}>
                    <div style={styles.previewTitle}>Duplicate rejections</div>
                    <div style={styles.phaseActionRow}>
                      <div style={styles.previewLine}>
                        {vettingSummary.duplicate_checks.length} check number(s) already existed in EDI.
                      </div>
                      <button
                        style={styles.clearButton}
                        type="button"
                        onClick={() => setVettingDuplicatesExpanded((value) => !value)}
                        aria-expanded={vettingDuplicatesExpanded}
                      >
                        {vettingDuplicatesExpanded ? "Hide Results" : "Show Results"}
                      </button>
                    </div>
                    {vettingDuplicatesExpanded && (
                      <div style={styles.archiveList}>
                        {vettingSummary.duplicate_checks.map((checkNumber) => (
                          <div key={checkNumber} style={styles.archiveItem}>
                            <div style={styles.archiveName}>{checkNumber}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

function buttonLabel(label: string, complete: boolean) {
  return (
    <>
      {label}
      {complete ? <span style={styles.checkmark}>{" ✓"}</span> : null}
    </>
  );
}

const styles: Record<string, CSSProperties> = {
  shell: {
    minHeight: "100vh",
    display: "grid",
    gridTemplateColumns: "220px 1fr",
    background: "#f5f8fb",
    color: "#1f2933",
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
    textAlign: "left",
  },
  sidebar: {
    borderRight: "1px solid #9fc5df",
    background: "#cfeeff",
    padding: "18px 0 18px 14px",
    boxSizing: "border-box",
    boxShadow: "8px 0 22px rgba(42, 91, 122, 0.08)",
    backgroundImage: "linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,255,255,0))",
  },
  brandBlock: {
    display: "flex",
    alignItems: "center",
    gap: "9px",
    margin: "0 14px 24px 0",
  },
  brandIcon: {
    width: "34px",
    height: "34px",
    borderRadius: "8px",
    display: "block",
    boxShadow: "0 6px 14px rgba(18, 56, 77, 0.12)",
  },
  brandText: {
    color: "#12384d",
    fontSize: "15px",
    fontWeight: 900,
  },
  importButton: {
    width: "calc(100% - 14px)",
    height: "38px",
    marginTop: "12px",
    border: "1px solid #12384d",
    borderRadius: "6px",
    background: "#12384d",
    color: "#ffffff",
    textAlign: "left",
    padding: "0 10px",
    fontWeight: 700,
    cursor: "pointer",
  },
  backButton: {
    width: "calc(100% - 14px)",
    height: "38px",
    marginTop: "12px",
    border: "1px solid #000000",
    borderRadius: "6px",
    background: "#000000",
    color: "#ffffff",
    textAlign: "left",
    padding: "0 10px",
    fontWeight: 700,
    cursor: "pointer",
  },
  content: {
    padding: "26px 30px",
  },
  panel: {
    maxWidth: "980px",
    background: "#ffffff",
    border: "1px solid #c8d9e6",
    borderRadius: "14px",
    padding: "24px 26px",
    boxShadow: "0 18px 40px rgba(41, 72, 92, 0.08)",
  },
  titleRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "20px",
  },
  title: {
    margin: 0,
    fontSize: "30px",
    fontWeight: 900,
    color: "#163a52",
  },
  subtitle: {
    marginTop: "10px",
    color: "#4a6677",
    fontSize: "15px",
    lineHeight: 1.55,
  },
  dateCard: {
    minWidth: "260px",
    borderRadius: "12px",
    padding: "16px 18px",
    background: "linear-gradient(180deg, #f7fbff, #edf6fb)",
    border: "1px solid #cfe0ec",
    boxShadow: "0 10px 22px rgba(38, 74, 98, 0.08)",
  },
  cardLabel: {
    color: "#4d7287",
    fontSize: "11px",
    fontWeight: 800,
    letterSpacing: "0.11em",
    textTransform: "uppercase",
    marginBottom: "8px",
  },
  cardValue: {
    color: "#163a52",
    fontSize: "18px",
    fontWeight: 800,
    lineHeight: 1.25,
  },
  instructionsCard: {
    marginTop: "18px",
    padding: "16px 18px",
    borderRadius: "12px",
    background: "#f8fbfd",
    border: "1px solid #d8e6ef",
  },
  noticeCard: {
    marginTop: "18px",
    padding: "14px 16px",
    borderRadius: "10px",
    background: "#eef8ff",
    border: "1px solid #cce4f4",
    color: "#23485c",
    lineHeight: 1.6,
  },
  phaseCard: {
    marginTop: "18px",
    borderRadius: "14px",
    border: "1px solid #d6e3ec",
    background: "#ffffff",
    padding: "18px 18px 20px",
    boxShadow: "0 10px 20px rgba(35, 62, 82, 0.06)",
  },
  sectionLabel: {
    color: "#1f5672",
    fontSize: "12px",
    fontWeight: 800,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    marginBottom: "10px",
  },
  phaseTitle: {
    margin: 0,
    fontSize: "22px",
    fontWeight: 900,
    color: "#163a52",
  },
  phaseBody: {
    marginTop: "8px",
    color: "#355264",
    lineHeight: 1.6,
  },
  stepList: {
    margin: 0,
    paddingLeft: "20px",
    color: "#2f4f62",
    lineHeight: 1.7,
    display: "grid",
    gap: "8px",
  },
  mono: {
    fontFamily: '"Cascadia Mono", "Consolas", "Courier New", monospace',
    fontSize: "0.95em",
  },
  hiddenInput: {
    display: "none",
  },
  buttonRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    marginTop: "18px",
    alignItems: "center",
  },
  phaseActionStack: {
    display: "grid",
    gap: "12px",
    marginTop: "18px",
  },
  phaseActionRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    alignItems: "center",
  },
  uploadButton: {
    minHeight: "40px",
    padding: "0 14px",
    borderRadius: "8px",
    border: "1px solid #12384d",
    background: "#12384d",
    color: "#ffffff",
    fontWeight: 800,
    cursor: "pointer",
  },
  confirmButton: {
    minHeight: "40px",
    padding: "0 14px",
    borderRadius: "8px",
    border: "1px solid #000000",
    background: "#000000",
    color: "#ffffff",
    fontWeight: 800,
    cursor: "pointer",
  },
  clearButton: {
    minHeight: "40px",
    padding: "0 14px",
    borderRadius: "8px",
    border: "1px solid #c1d3df",
    background: "#ffffff",
    color: "#163a52",
    fontWeight: 800,
    cursor: "pointer",
  },
  completeBadge: {
    minHeight: "28px",
    padding: "0 10px",
    borderRadius: "999px",
    background: "#e6f7ec",
    color: "#116a39",
    display: "inline-flex",
    alignItems: "center",
    fontSize: "12px",
    fontWeight: 800,
  },
  checkmark: {
    marginLeft: "6px",
  },
  selectedFileList: {
    marginTop: "18px",
    padding: "14px 16px",
    borderRadius: "10px",
    background: "#f8fbfd",
    border: "1px solid #d8e6ef",
  },
  previewCard: {
    marginTop: "18px",
    padding: "14px 16px",
    borderRadius: "10px",
    background: "#f8fbfd",
    border: "1px solid #d8e6ef",
  },
  previewTitle: {
    color: "#1f5672",
    fontSize: "12px",
    fontWeight: 800,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    marginBottom: "10px",
  },
  previewLine: {
    color: "#2f4f62",
    lineHeight: 1.7,
  },
  archiveList: {
    marginTop: "12px",
    display: "grid",
    gap: "10px",
  },
  archiveItem: {
    padding: "10px 12px",
    borderRadius: "8px",
    background: "#ffffff",
    border: "1px solid #e0e9f0",
  },
  archiveName: {
    color: "#163a52",
    fontWeight: 800,
    marginBottom: "4px",
  },
  uploadMessage: {
    marginTop: "18px",
    padding: "12px 14px",
    borderRadius: "10px",
    background: "#eef8ff",
    border: "1px solid #cce4f4",
    color: "#23485c",
    lineHeight: 1.55,
  },
};
