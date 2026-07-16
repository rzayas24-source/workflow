import React, { useEffect } from "react";

interface Props {
    loadNext: () => void;
}

const NextLoader: React.FC<Props> = ({ loadNext }) => {

    useEffect(() => {
        const timer = setTimeout(() => {
            loadNext();
        }, 1500);

        return () => clearTimeout(timer);
    }, []);

    return (
        <div style={{ padding: "20px", fontSize: "20px" }}>
            Loading next site batch...
        </div>
    );
};

export default NextLoader;
