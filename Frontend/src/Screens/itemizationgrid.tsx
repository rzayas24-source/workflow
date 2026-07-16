interface Item {
    id: number;
    type: string | number;
    amount: number;
    payer?: string | number;
    check_number?: string | number;
    poster?: string | number;
    misc?: string | number;
    misc_type?: string | number;
    notes?: string | number;
}

interface Props {
    items: Item[];
    onEdit: (id: number) => void;
}

const posters = ["Nick", "Raul"];

function formatAmount(value: number) {
    return value.toLocaleString(undefined, {
        style: "currency",
        currency: "USD",
    });
}

export default function ItemizationGrid({ items, onEdit }: Props) {
    return (
        <div style={{ marginTop: "20px" }}>
            <h3>Itemization Entries</h3>

            {posters.map((poster) => {
                const posterItems = items.filter((item) => item.poster === poster);
                const total = posterItems.reduce((sum, item) => sum + Number(item.amount || 0), 0);

                return (
                    <section key={poster} style={{ marginTop: "16px" }}>
                        <h4 style={{ marginBottom: "8px" }}>
                            {poster} Total: {formatAmount(total)}
                        </h4>

                        {posterItems.length === 0 ? (
                            <div style={{ color: "#666", marginBottom: "8px" }}>
                                No entries for {poster}.
                            </div>
                        ) : (
                            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                                <thead>
                                    <tr>
                                        <th>Type</th>
                                        <th>Amount</th>
                                        <th>Payer</th>
                                        <th>Check #</th>
                                        <th>Misc</th>
                                        <th>Misc Desc</th>
                                        <th>Notes</th>
                                        <th>Edit</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {posterItems.map(item => (
                                        <tr key={item.id}>
                                            <td>{item.type}</td>
                                            <td>{formatAmount(item.amount)}</td>
                                            <td>{item.payer}</td>
                                            <td>{item.check_number}</td>
                                            <td>{item.misc || 0}</td>
                                            <td>{item.misc_type}</td>
                                            <td>{item.notes}</td>
                                            <td>
                                                <button onClick={() => onEdit(item.id)}>Edit</button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </section>
                );
            })}
        </div>
    );
}
