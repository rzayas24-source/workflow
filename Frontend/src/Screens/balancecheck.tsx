import React from "react";

interface Props {
    keyproofTotal: number;
    itemizationTotal: number;
    onEditKeyproof: () => void;
    onEditItemization: () => void;
    onAccept: () => void;
}

const BalanceCheck: React.FC<Props> = ({
    keyproofTotal,
    itemizationTotal,
    onEditKeyproof,
    onEditItemization,
    onAccept
}) => {

    const matches = keyproofTotal === itemizationTotal;

    return (
        <div style={{ padding: "20px" }}>
            <h2>Balance Check</h2>

            <div style={{ fontSize: "18px", marginBottom: "20px" }}>
                Keyproof Total: ${keyproofTotal.toFixed(2)} <br />
                Itemization Total: ${itemizationTotal.toFixed(2)}
            </div>

            {!matches && (
                <div style={{ color: "red", fontWeight: "bold", marginBottom: "20px" }}>
                    Batch does not balance.
                </div>
            )}

            {matches ? (
                <button onClick={onAccept} style={{ padding: "10px 20px", fontSize: "18px" }}>
                    Accept and Move to Next Batch
                </button>
            ) : (
                <div>
                    <button onClick={onEditKeyproof} style={{ padding: "10px 20px", marginRight: "10px" }}>
                        Edit Keyproof
                    </button>

                    <button onClick={onEditItemization} style={{ padding: "10px 20px" }}>
                        Edit Itemization
                    </button>
                </div>
            )}
        </div>
    );
};

export default BalanceCheck;
