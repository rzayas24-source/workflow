import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRejectList } from "../api/rejectlist_api";

interface RejectedBatch {
    id: number;
    filename: string;
    reason: string | null;
    date: string | null;
}

const RejectedList = () => {
    const navigate = useNavigate();
    const [rejected, setRejected] = useState<RejectedBatch[]>([]);

    useEffect(() => {
        getRejectList()
            .then((res) => setRejected(res.data))
            .catch((err) => {
                setRejected([]);
                console.error(err);
            });
    }, []);

    return (
        <div style={{ padding: "20px" }}>
            <h2>Rejected Site Batches</h2>

            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                    <tr>
                        <th>Import ID</th>
                        <th>Filename</th>
                        <th>Reason</th>
                        <th>Date</th>
                    </tr>
                </thead>

                <tbody>
                    {rejected.map(row => (
                        <tr key={row.id}>
                            <td>{row.id}</td>
                            <td>{row.filename}</td>
                            <td>{row.reason}</td>
                            <td>{row.date}</td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <button
                onClick={() => navigate("/")}
                style={{ padding: "10px 20px", marginTop: "20px" }}
            >
                Back
            </button>
        </div>
    );
};

export default RejectedList;
