import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./components/Home";
import TableView from "./components/TableView";
import FileState from "./context/File/FileState";

function App() {
  return (
    <FileState>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/table-view" element={<TableView />} />
        </Routes>
      </Router>
    </FileState>
  );
}

export default App;
