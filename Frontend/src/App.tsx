import React from "react";
import ScreenManager from "./ScreenManager";

const App: React.FC = () => {
  return (
    <div style={{ width: "100%", minHeight: "100vh", overflowY: "auto" }}>
      <ScreenManager />
    </div>
  );
};

export default App;
