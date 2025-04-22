import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./components/Home";
import TableView from "./components/TableView";
import FileState from "./context/File/FileState";
import QualityState from "./context/Qualitychecks/QualityState";

function App() {
  return (
    <QualityState>
      <FileState>
        <Router>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/table-view" element={<TableView />} />
          </Routes>
        </Router>
      </FileState>
    </QualityState>
  );
}

export default App;
