import FileContext from "../context/File/FileContext";
import React, { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";

function Home() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });
  const navigate = useNavigate();
  const filecontext = useContext(FileContext);
  const { datachange } = filecontext;

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setMessage({ text: "", type: "" });
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: formData,
      });
      const json = await response.json();
      console.log(json);
      if (json.success) {
        datachange(json.data);
        setMessage({ text: "✅ File uploaded successfully!", type: "success" });
        setTimeout(() => {
          navigate("/table-view", { state: { file } });
        }, 1500);
      } else {
        setMessage({ text: "❌ File upload failed!", type: "error" });
      }
    } catch (error) {
      console.error("Error uploading file:", error);
      setMessage({ text: "❌ An error occurred while uploading.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex items-center justify-center bg-gray-100 relative">
      {/* Loader Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-white bg-opacity-60 flex items-center justify-center z-50">
          <div className="w-12 h-12 border-4 border-blue-500 border-dashed rounded-full animate-spin"></div>
        </div>
      )}

      {/* Message Alert */}
      {message.text && (
        <div
          className={`absolute top-4 px-4 py-2 rounded shadow-md text-white z-50 ${
            message.type === "success" ? "bg-green-500" : "bg-red-500"
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow-lg w-96">
        <h2 className="text-xl font-semibold mb-4 text-center">Upload File</h2>
        <input
          type="file"
          accept=".csv, .xlsx"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer focus:outline-none"
        />
        {file && (
          <div className="mt-4 flex items-center justify-between bg-gray-200 p-2 rounded-md">
            <span className="text-sm font-medium">{file.name}</span>
            <button
              className="text-red-600 text-lg"
              onClick={() => setFile(null)}
            >
              ❌
            </button>
          </div>
        )}
        <button
          onClick={handleSubmit}
          disabled={!file || loading}
          className={`mt-4 w-full py-2 text-white font-semibold rounded-md transition-colors duration-200 ${
            file && !loading
              ? "bg-blue-600 hover:bg-blue-700"
              : "bg-gray-400 cursor-not-allowed"
          }`}
        >
          {loading ? "Uploading..." : "Submit"}
        </button>
      </div>
    </div>
  );
}

export default Home;
