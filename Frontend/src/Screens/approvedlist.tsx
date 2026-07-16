import { useEffect, useState } from "react";
import { getApprovedList } from "../api/approvedlist_api";
import type { ApprovedBatch } from "../api/approvedlist_api";

const ApprovedList = () => {
    const [approved, setApproved] = useState<ApprovedBatch[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        getApprovedList()
            .then(res => {
                setApproved(res.data);
                setError(null);
            })
            .catch(err => {
                setApproved([]);
                setError(err instanceof Error ? err.message : "Failed to load approved batches");
            });
    }, []);

    return (
        <div style={{ padding: "20px" }}>
            <h2>Approved Site Batches</h2>
            {error && <div style={{ marginBottom: "12px", color: "#a32121" }}>{error}</div>}

            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                    <tr>
                        <th>Import ID</th>
                        <th>Filename</th>
                        <th>Site</th>
                        <th>Detail</th>
                        <th>Total</th>
                        <th>Date</th>
                    </tr>
                </thead>

                <tbody>
                    {approved.map(row => (
                        <tr key={row.id}>
                            <td>{row.id}</td>
                            <td>{row.filename}</td>
                            <td>{row.site}</td>
                            <td>{row.detail}</td>
                            <td>{Number(row.total || 0).toLocaleString(undefined, { style: "currency", currency: "USD" })}</td>
                            <td>{row.date}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default ApprovedList;

