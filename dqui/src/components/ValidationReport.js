import React from "react";

const ValidationResult = ({ isOpen, onClose, results }) => {
  if (!isOpen || !results || results.length === 0) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white w-full max-w-4xl p-6 rounded-lg shadow-lg">
        <div className="border-b mb-4">
          <h2 className="text-xl font-semibold">Validation Summary</h2>
        </div>

        <div className="space-y-4">
          {results.map((item, index) => (
            <div
              key={index}
              className={`border-l-4 rounded-lg p-4 shadow-sm break-words ${
                item.Success ? "border-green-500 bg-green-50" : "border-red-500 bg-red-50"
              }`}
            >
              <h4 className="text-lg font-semibold">
                {item.Column ? `Column: ${item.Column}` : "Unnamed Column"} — {item.Expectation}
              </h4>
              <p className="text-sm">
                <strong>Status:</strong>{" "}
                <span className={item.Success ? "text-green-600" : "text-red-600"}>
                  {item.Success ? "✅ Passed" : "❌ Failed"}
                </span>
              </p>

              <ul className="text-sm mt-2 list-disc ml-5">
                <li><strong>Failed %:</strong> {item["Failed %"] ?? "-"}</li>
                <li><strong>Failed Records:</strong> {item["Failed Records"] ?? "-"}</li>
                <li><strong>Passed %:</strong> {item["Passed %"] ?? "-"}</li>
                <li><strong>Passed Records:</strong> {item["Passed Records"] ?? "-"}</li>
                <li><strong>Total Records:</strong> {item["Total Records"] ?? "-"}</li>
              </ul>

              {item["Sample Failures"] && item["Sample Failures"].length > 0 && (
                <div className="mt-2">
                  <strong>Sample Failures:</strong>
                  <ul className="list-disc ml-6">
                    {item["Sample Failures"].slice(0, 5).map((fail, i) => (
                      <li key={i}>{fail}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-500 text-white rounded-md"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ValidationResult;
