import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./components/Home";
import TableView from "./components/TableView";
import FileState from "./context/File/FileState";
import QualityState from "./context/Qualitychecks/QualityState";
import ValidationReport from "./components/ValidationReport";

function App() {
  return (
    <QualityState>
      <FileState>
        <Router>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/table-view" element={<TableView />} />
            <Route path="/validation" element={<ValidationReport />} />
          </Routes>
        </Router>
      </FileState>
    </QualityState>
  );
}

export default App;
