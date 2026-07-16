import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useSearchParams } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000";

const SitesScreen = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [sites, setSites] = useState([]);
    const [newName, setNewName] = useState("");
    const [newDesc, setNewDesc] = useState("");
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editName, setEditName] = useState("");
    const [editDesc, setEditDesc] = useState("");
    const [editActive, setEditActive] = useState(1);

    useEffect(() => {
        loadSites();
    }, []);

    const loadSites = async () => {
        try {
            const res = await axios.get(`${API_BASE}/sites`);
            setSites(res.data);
        } catch (err) {
            console.error("Failed to load sites:", err);
        }
    };

    const addSite = async () => {
        if (!newName.trim()) return;
        try {
            await axios.post(`${API_BASE}/sites`, {
                name: newName.trim(),
                description: newDesc.trim()
            });
            setNewName("");
            setNewDesc("");
            loadSites();
        } catch (err) {
            console.error("Failed to add site:", err);
        }
    };

    const startEdit = (site: any) => {
        setEditingId(site.id);
        setEditName(site.name);
        setEditDesc(site.description || "");
        setEditActive(site.active);
    };

    const saveEdit = async () => {
        if (editingId === null) return;
        try {
            await axios.put(`${API_BASE}/sites/${editingId}`, {
                name: editName.trim(),
                description: editDesc.trim(),
                active: editActive
            });
            setEditingId(null);
            loadSites();
        } catch (err) {
            console.error("Failed to update site:", err);
        }
    };

    const cancelEdit = () => {
        setEditingId(null);
    };

    const toggleActive = async (site: any) => {
        try {
            await axios.put(`${API_BASE}/sites/${site.id}`, {
                name: site.name,
                description: site.description,
                active: site.active === 1 ? 0 : 1
            });
            loadSites();
        } catch (err) {
            console.error("Failed to toggle active:", err);
        }
    };

    const deleteSite = async (siteId: number) => {
        try {
            await axios.delete(`${API_BASE}/sites/${siteId}`);
            loadSites();
        } catch (err) {
            console.error("Failed to delete site:", err);
        }
    };

    const goBack = () => {
        const attachmentId = searchParams.get("attachmentId");
        const day = searchParams.get("day");

        if (attachmentId) {
            const params = new URLSearchParams({ attachmentId });

            if (day) {
                params.set("day", day);
            }

            navigate(`/keyproof?${params.toString()}`);
            return;
        }

        navigate(-1);
    };

    return (
        <div style={{ padding: "20px", textAlign: "left" }}>
            <h2>Sites Management</h2>

            {/* Add new site */}
            <div
                style={{
                    marginBottom: "20px",
                    padding: "10px",
                    border: "1px solid #ccc",
                    borderRadius: "4px"
                }}
            >
                <h3>Add New Site</h3>
                <div style={{ marginBottom: "8px" }}>
                    <input
                        type="text"
                        placeholder="Site name"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        style={{ padding: "8px", width: "260px", marginRight: "10px" }}
                    />
                    <input
                        type="text"
                        placeholder="Description (optional)"
                        value={newDesc}
                        onChange={(e) => setNewDesc(e.target.value)}
                        style={{ padding: "8px", width: "260px" }}
                    />
                </div>
                <button
                    onClick={addSite}
                    style={{
                        padding: "8px 14px",
                        backgroundColor: "#5cb85c",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer"
                    }}
                >
                    Add Site
                </button>
            </div>

            {/* Edit site */}
            {editingId !== null && (
                <div
                    style={{
                        marginBottom: "20px",
                        padding: "10px",
                        border: "1px solid #ccc",
                        borderRadius: "4px",
                        backgroundColor: "#f9f9f9"
                    }}
                >
                    <h3>Edit Site</h3>
                    <div style={{ marginBottom: "8px" }}>
                        <input
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            style={{ padding: "8px", width: "260px", marginRight: "10px" }}
                        />
                        <input
                            type="text"
                            value={editDesc}
                            onChange={(e) => setEditDesc(e.target.value)}
                            style={{ padding: "8px", width: "260px" }}
                        />
                    </div>
                    <div style={{ marginBottom: "8px" }}>
                        <label>
                            <input
                                type="checkbox"
                                checked={editActive === 1}
                                onChange={(e) =>
                                    setEditActive(e.target.checked ? 1 : 0)
                                }
                                style={{ marginRight: "6px" }}
                            />
                            Active
                        </label>
                    </div>
                    <button
                        onClick={saveEdit}
                        style={{
                            padding: "8px 14px",
                            backgroundColor: "#0275d8",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer",
                            marginRight: "10px"
                        }}
                    >
                        Save
                    </button>
                    <button
                        onClick={cancelEdit}
                        style={{
                            padding: "8px 14px",
                            backgroundColor: "#777",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer"
                        }}
                    >
                        Cancel
                    </button>
                </div>
            )}

            {/* List sites */}
            <div>
                <h3>Existing Sites</h3>
                {sites.length === 0 && <p>No sites defined yet.</p>}
                <table
                    style={{
                        width: "100%",
                        borderCollapse: "collapse",
                        marginTop: "10px"
                    }}
                >
                    <thead>
                        <tr>
                            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Name</th>
                            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Description</th>
                            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Active</th>
                            <th style={{ borderBottom: "1px solid #ccc", textAlign: "left" }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sites.map((s: any) => (
                            <tr key={s.id}>
                                <td style={{ padding: "6px 4px" }}>{s.name}</td>
                                <td style={{ padding: "6px 4px" }}>{s.description}</td>
                                <td style={{ padding: "6px 4px" }}>
                                    {s.active === 1 ? "Yes" : "No"}
                                </td>
                                <td style={{ padding: "6px 4px" }}>
                                    <button
                                        onClick={() => startEdit(s)}
                                        style={{
                                            padding: "4px 8px",
                                            marginRight: "6px",
                                            backgroundColor: "#5bc0de",
                                            color: "white",
                                            border: "none",
                                            borderRadius: "4px",
                                            cursor: "pointer"
                                        }}
                                    >
                                        Edit
                                    </button>
                                    <button
                                        onClick={() => toggleActive(s)}
                                        style={{
                                            padding: "4px 8px",
                                            marginRight: "6px",
                                            backgroundColor: "#f0ad4e",
                                            color: "white",
                                            border: "none",
                                            borderRadius: "4px",
                                            cursor: "pointer"
                                        }}
                                    >
                                        {s.active === 1 ? "Deactivate" : "Activate"}
                                    </button>
                                    <button
                                        onClick={() => deleteSite(s.id)}
                                        style={{
                                            padding: "4px 8px",
                                            backgroundColor: "#d9534f",
                                            color: "white",
                                            border: "none",
                                            borderRadius: "4px",
                                            cursor: "pointer"
                                        }}
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <button
                onClick={goBack}
                style={{
                    marginTop: "20px",
                    padding: "10px 20px",
                    backgroundColor: "#333",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer"
                }}
            >
                Back
            </button>
        </div>
    );
};

export default SitesScreen;
