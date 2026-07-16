import React, { useEffect, useState } from "react";
import axios from "axios";

interface Row {
    id: number;
    filename: string;
    snapshot_path: string;
    review_status: string;
}

interface Props {
    onSelect: (id: number, img: string) => void;
}

const Queue: React.FC<Props> = ({ onSelect }) => {
    const [rows, setRows] = useState<Row[]>([]);

    useEffect(() => {
        loadPending();
    }, []);

    const loadPending = async () => {
        const res = await axios.get("http://localhost:8000/attachments/pending");
        if (Array.isArray(res.data)) {
            setRows(res.data);
        } else {
            setRows([res.data]);
        }
    };

    return (
        <div style={{ padding: "20px" }}>
            <h2>Pending Attachments</h2>

            {rows.map(row => (
                <div key={row.id} style={{ marginBottom: "20px" }}>
                    <div>ID: {row.id}</div>
                    <div>File: {row.filename}</div>

                    <button
                        onClick={() =>
                            onSelect(
                                row.id,
                                `http://localhost:8000/attachments/${row.id}/snapshot`
                            )
                        }
                        style={{ padding: "10px 20px", marginTop: "10px" }}
                    >
                        Review
                    </button>
                </div>
            ))}
        </div>
    );
};

export default Queue;
