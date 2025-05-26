import React, { useState, useEffect, useContext } from "react";
import { useLocation } from "react-router-dom";
import * as XLSX from "xlsx";
import Papa from "papaparse";
import FileContext from "../context/File/FileContext";
import QualityContext from "../context/Qualitychecks/QualityContext";

function TableView() {
  const location = useLocation();
  const file = location.state?.file;
  const filecontext = useContext(FileContext);
  const { data, val, setresult, columns, setColumns, rows, setRows } = filecontext;
  const qualityContext = useContext(QualityContext);
  const { ruleids } = qualityContext;

  const [genrule, setgenrule] = useState(false);
  const [generatedRules, setGeneratedRules] = useState([]);
  const [selectedColumn, setSelectedColumn] = useState("");
  const [selectedType, setSelectedType] = useState("");
  const [rules, setRules] = useState([{ type: "", value: "" }]);
  const [savedRules, setSavedRules] = useState({}); // { column: { type, rules } }
  const [validationReport, setValidationReport] = useState(null);
  const [failedIndicesMap, setFailedIndicesMap] = useState({}); // { columnName: [indices] }
  const [validationResultData, setValidationResultData] = useState(null); // New state to hold result.data
  const [isExportingWord, setIsExportingWord] = useState(false); // Loading state for Word export

  const ruleOptions = {
    string: ["not_null", "contains", "starts_with", "ends_with", "set_contain"],
    number: ["not_null", "range", "min", "max", "equal_to", "not_equal_to"],
    date: ["not_null", "before", "after", "between"],
    boolean: ["not_null", "true_ratio", "false_ratio"],
  };

  useEffect(() => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const fileType = file.name.split(".").pop();
      if (fileType === "csv") {
        const result = Papa.parse(e.target.result, { header: true });
        if (result.data.length > 0) {
          // Filter out empty rows that PapaParse might include at the end
          const filteredData = result.data.filter(row => Object.values(row).some(value => value !== null && value !== ''));
          setColumns(Object.keys(filteredData[0] || {}));
          setRows(filteredData);
        }
      } else if (fileType === "xlsx") {
        const workbook = XLSX.read(e.target.result, { type: "binary" });
        const sheet = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);
        if (sheet.length > 0) {
          setColumns(Object.keys(sheet[0]));
          setRows(sheet);
        }
      }
    };
    reader.readAsBinaryString(file);
  }, [file]);

  const handleRuleRemoval = (index, column) => {
    const updatedRules = savedRules[column].rules.filter((_, i) => i !== index);
    setSavedRules((prev) => ({
      ...prev,
      [column]: {
        ...prev[column],
        rules: updatedRules.length > 0 ? updatedRules : [{ type: "", value: "" }],
      },
    }));
    if (updatedRules.length === 0) {
      // If no rules left for the column, remove the column entry from savedRules
      const { [column]: _, ...rest } = savedRules;
      setSavedRules(rest);
    }
  };

  const handleRuleTypeChange = (index, value) => {
    const updated = [...rules];
    updated[index].type = value;
    updated[index].value = ""; // Clear value when rule type changes
    setRules(updated);
  };

  const handleRuleValueChange = (index, value) => {
    const updated = [...rules];
    updated[index].value = value;
    setRules(updated);
  };

  const handleGenerateRules = () => {
    if (!selectedColumn) return;

    // Access gen_rule from the data context
    const gen_rules = data?.file_info?.gen_rule || {};

    const rulesForColumn = gen_rules[selectedColumn];

    if (!rulesForColumn || !rulesForColumn.rules || rulesForColumn.rules.length === 0) {
      // Use a custom message box instead of alert
      // For this example, I'll use a simple alert, but in a real app,
      // you'd render a modal or toast notification.
      alert("No generative rules found for this column.");
      return;
    }

    const formattedRules = rulesForColumn.rules.map((rule) => ({
      type: rule.name,
      id: rule.rule_id, // Preserve rule_id if available
      value: rule.value || "",
    }));

    setSavedRules((prev) => {
      const existing = prev[selectedColumn]?.rules || [];
      // Filter out duplicate rules if they have the same type and value
      const newRules = formattedRules.filter(
        (newRule) =>
          !existing.some(
            (existingRule) =>
              existingRule.type === newRule.type && existingRule.value === newRule.value
          )
      );
      return {
        ...prev,
        [selectedColumn]: {
          type: rulesForColumn.dataType,
          rules: [...existing, ...newRules],
        },
      };
    });

    setgenrule(true); // This state seems to control a display, keep it
  };

  const handleSaveRule = () => {
    if (!selectedColumn || !selectedType) return;

    // Filter out rules that don't have a type or a value (unless it's 'not_null')
    const cleanedRules = rules.filter((r) => r.type && (r.type === "not_null" || r.value));

    if (cleanedRules.length === 0) {
      alert("Please add at least one valid rule before saving.");
      return;
    }

    setSavedRules((prev) => {
      const existingRules = prev[selectedColumn]?.rules || [];
      // Combine existing and new rules, filtering out duplicates
      const combinedRules = [...existingRules, ...cleanedRules];
      const uniqueRules = Array.from(
        new Set(combinedRules.map((rule) => JSON.stringify(rule)))
      ).map((ruleString) => JSON.parse(ruleString));

      return {
        ...prev,
        [selectedColumn]: {
          type: selectedType,
          rules: uniqueRules,
        },
      };
    });
    setRules([{ type: "", value: "" }]); // Reset current rule input
  };

  const handleSubmit = async () => {
    const formattedRules = Object.entries(savedRules).reduce((acc, [column, data]) => {
      const rules = (data.rules || [])
        .filter((r) => r.type && (r.type === "not_null" || r.value)) // Ensure rules are valid
        .map((r) => ({
          rule_id: r.id ? r.id : ruleids[r.type], // Use existing ID or map from ruleids
          name: r.type,
          value: r.value,
        }));

      acc[column] = {
        dataType: data.type,
        rules,
      };

      return acc;
    }, {});
    console.log("Formatted rules for submission:", formattedRules);

    try {
      const response = await fetch("http://localhost:8000/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formattedRules),
      });

      const result = await response.json();

      if (result.success) {
        alert("Validation completed! Check the report and highlighted data below the table.");
        console.log("Validation API response data:", result.data);
        setresult(result.data); // Update global context with validation result
        setValidationReport(result.data); // Set local state for report display
        setValidationResultData(result.data); // Store the result data for highlighting
      } else {
        alert(`Error: ${result.error || "Unknown error during validation."}`);
        setValidationReport(null);
        setValidationResultData(null);
        setFailedIndicesMap({});
      }
    } catch (error) {
      alert(`Failed to submit rules: ${error.message}`);
      console.error("Error submitting rules:", error);
      setValidationReport(null);
      setValidationResultData(null);
      setFailedIndicesMap({});
    }
  };

  useEffect(() => {
    if (validationResultData) {
      // Prepare failed indices map for highlighting
      const failedMap = {};
      Object.entries(validationResultData).forEach(([columnName, validationResults]) => {
        // Handle both array of results and single result object
        const resultsArray = Array.isArray(validationResults) ? validationResults : [validationResults];

        resultsArray.forEach(res => {
          if (!res.Success && res["Failed Indices"] && res["Failed Indices"].length > 0) {
            // Ensure column entry exists and is an array
            failedMap[columnName] = [...(failedMap[columnName] || []), ...res["Failed Indices"]];
          }
        });
      });
      // Flatten and deduplicate indices for each column
      for (const col in failedMap) {
        failedMap[col] = Array.from(new Set(failedMap[col]));
      }
      setFailedIndicesMap(failedMap);
    }
  }, [validationResultData]);

  const isFailedIndex = (rowIndex, columnName) => {
    return failedIndicesMap[columnName]?.includes(rowIndex);
  };

  const handleExportReport = () => {
    if (!validationReport) {
      alert("No validation report to export. Please run a validation first.");
      return;
    }

    try {
      const jsonString = JSON.stringify(validationReport, null, 2); // Pretty print JSON
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "validation_report.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url); // Clean up the object URL
    } catch (error) {
      alert(`Failed to export report: ${error.message}`);
      console.error("Error exporting report:", error);
    }
  };

  const handleExportWordReport = async () => {
    if (!validationReport) {
      alert("No validation report to export as Word. Please run a validation first.");
      return;
    }

    setIsExportingWord(true); // Set loading state

    try {
      const response = await fetch("http://localhost:8000/export-word", { // Assuming this is your backend endpoint
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(validationReport),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Backend error: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const blob = await response.blob(); // Get the response as a Blob
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "validation_report.docx"; // Suggest a .docx filename
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url); // Clean up the object URL

      alert("Validation report successfully exported as Word document!");

    } catch (error) {
      alert(`Failed to export report as Word: ${error.message}`);
      console.error("Error exporting Word report:", error);
    } finally {
      setIsExportingWord(false); // Reset loading state
    }
  };

  return (
    <div className="h-screen flex bg-gray-100 font-sans">
      {/* Left Panel */}
      <div className="w-1/4 bg-white shadow-lg p-4 overflow-y-auto rounded-lg m-4">
        <h3 className="text-2xl font-bold mb-6 text-gray-800">Configure Column Rules</h3>

        <label htmlFor="select-column" className="block text-sm font-medium mb-2 text-gray-700">Select Column:</label>
        <select
          id="select-column"
          className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out"
          value={selectedColumn}
          onChange={(e) => {
            setSelectedColumn(e.target.value);
            // Load saved rules for the selected column, or reset to empty if none
            setSelectedType(savedRules[e.target.value]?.type || "");
            setRules(savedRules[e.target.value]?.rules || [{ type: "", value: "" }]);
          }}
        >
          <option value="">-- Choose Column --</option>
          {columns.map((col, index) => (
            <option key={index} value={col}>
              {col}
            </option>
          ))}
        </select>

        {selectedColumn && (
          <>
            {/* Display existing validation results for the selected column */}
            {val[selectedColumn] && Array.isArray(val[selectedColumn]) &&
              val[selectedColumn].map((item, index) => (
                <div
                  key={`val-result-${index}`}
                  className={`border-l-4 rounded-lg p-4 mb-4 shadow-sm break-words ${
                    item.Success ? "border-green-500 bg-green-50" : "border-red-500 bg-red-50"
                  }`}
                >
                  <h5 className={`text-lg font-semibold ${item.Success ? "text-green-700" : "text-red-700"}`}>
                    {item.Expectation}
                  </h5>
                  <p className="text-sm font-medium mt-1 text-gray-700">
                    Success:{" "}
                    <span className={item.Success ? "text-green-600" : "text-red-600"}>
                      {item.Success ? "✅ Passed" : "❌ Failed"}
                    </span>
                  </p>

                  {!item.Success && (
                    <div className="mt-2 ml-2 text-sm text-gray-800">
                      <ul className="list-disc list-inside">
                        <li>
                          <strong>Failed %:</strong> {item["Failed %"] || item["Failed_%"] || "-"}
                        </li>
                        {item["Failed Indices"] && item["Failed Indices"].length > 0 && (
                          <li>
                            <strong>Failed Indices:</strong> {item["Failed Indices"].join(", ")}
                          </li>
                        )}
                        <li>
                          <strong>Failed Records:</strong> {item["Failed Records"] || item["Failed_Records"] || "-"}
                        </li>
                        <li>
                          <strong>Passed %:</strong> {item["Passed %"] || "-"}
                        </li>
                        <li>
                          <strong>Total Records:</strong> {item["Total Records"] || "-"}
                        </li>
                        {item["Sample Failures"] && item["Sample Failures"].length > 0 && (
                          <div className="mt-2">
                            <strong>Sample Failures:</strong>
                            <ul className="list-disc list-inside ml-4">
                              {item["Sample Failures"].map((fail, i) => (
                                <li key={i}>{String(fail)}</li> // Ensure sample failures are strings
                              ))}
                            </ul>
                          </div>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              ))}

            <label htmlFor="select-data-type" className="block text-sm font-medium mb-2 text-gray-700">Select Data Type:</label>
            <select
              id="select-data-type"
              className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out"
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value);
                setRules([{ type: "", value: "" }]); // Reset rules when data type changes
              }}
            >
              <option value="">-- Choose Type --</option>
              <option value="string">String</option>
              <option value="number">Number</option>
              <option value="date">Date</option>
              <option value="boolean">Boolean</option>
            </select>

            {selectedType && (
              <>
                <label className="block text-sm font-medium mb-3 text-gray-700">Rules:</label>
                {rules.map((rule, index) => (
                  <div key={index} className="mb-4 p-3 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="flex items-center gap-2 mb-2">
                      <select
                        className="flex-grow p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                        value={rule.type}
                        onChange={(e) => handleRuleTypeChange(index, e.target.value)}
                      >
                        <option value="">-- Select Rule --</option>
                        {ruleOptions[selectedType]?.map((r) => (
                          <option key={r} value={r}>
                            {r.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())} {/* Format rule names */}
                          </option>
                        ))}
                      </select>
                      {/* Removed the individual rule removal button here as it's typically managed in the "Saved Rules" section */}
                    </div>

                    {/* Conditional rendering for rule value input */}
                    {["range", "between"].includes(rule.type) ? (
                      <div className="flex gap-2">
                        <input
                          className="w-1/2 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                          placeholder="Min"
                          value={rule.value.split(",")[0] || ""}
                          onChange={(e) =>
                            handleRuleValueChange(index, `${e.target.value},${rule.value.split(",")[1] || ""}`)
                          }
                        />
                        <input
                          className="w-1/2 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                          placeholder="Max"
                          value={rule.value.split(",")[1] || ""}
                          onChange={(e) =>
                            handleRuleValueChange(index, `${rule.value.split(",")[0] || ""},${e.target.value}`)
                          }
                        />
                      </div>
                    ) : ["contains", "starts_with", "ends_with", "min", "max", "equal_to", "not_equal_to", "before", "after", "true_ratio", "false_ratio", "set_contain"].includes(rule.type) ? (
                      <input
                        className="w-full p-2 border border-gray-300 rounded-md mt-1 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Enter value"
                        value={rule.value}
                        onChange={(e) => handleRuleValueChange(index, e.target.value)}
                      />
                    ) : null}
                  </div>
                ))}

                <button
                  onClick={() => setRules([...rules, { type: "", value: "" }])} // Add new rule input
                  className="w-full bg-blue-100 hover:bg-blue-200 text-blue-700 py-2 px-4 rounded-lg mb-3 font-semibold transition duration-150 ease-in-out"
                >
                  + Add Rule
                </button>

                <button
                  onClick={handleSaveRule}
                  className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-bold shadow-md hover:shadow-lg transition duration-200 ease-in-out"
                >
                  ✅ Save Rule
                </button>
              </>
            )}
          </>
        )}

        {Object.keys(savedRules).length > 0 && (
          <div className="mt-8 border-t pt-6 border-gray-200">
            <h4 className="text-xl font-bold mb-4 text-gray-800">Saved Rules</h4>
            {Object.entries(savedRules).map(([column, data]) => (
              <div key={column} className="border border-blue-200 rounded-lg p-4 mb-4 bg-blue-50 shadow-sm">
                <h5 className="font-bold text-blue-700 text-lg mb-1">{column}</h5>
                <p className="text-sm text-gray-600 italic mb-2">Type: {data.type}</p>
                <ul className="list-disc list-inside mt-1 text-sm text-gray-800">
                  {data.rules.map((r, i) => (
                    <li key={i} className="flex justify-between items-center py-1">
                      <span>
                        {r.type.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())}{" "}
                        {r.value && `: ${r.value}`}
                      </span>
                      <button
                        onClick={() => handleRuleRemoval(i, column)}
                        className="text-red-500 hover:text-red-700 ml-2 text-xl font-bold transition duration-150 ease-in-out"
                        title="Remove Rule"
                      >
                        ❌
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={handleGenerateRules}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 mt-6 rounded-lg font-bold shadow-md hover:shadow-lg transition duration-200 ease-in-out"
        >
          🎯 Show Generative Rules
        </button>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg mt-4 font-bold shadow-md hover:shadow-lg transition duration-200 ease-in-out"
        >
          Submit Validation
        </button>

        {/* Export Report Buttons */}
        {validationReport && ( // Only show if there's a report
          <>
            <button
              onClick={handleExportReport}
              className="w-full bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-lg mt-4 font-bold shadow-md hover:shadow-lg transition duration-200 ease-in-out"
            >
              ⬇️ Export Report as JSON
            </button>
            <button
              onClick={handleExportWordReport}
              className={`w-full py-3 rounded-lg mt-4 font-bold shadow-md hover:shadow-lg transition duration-200 ease-in-out ${
                isExportingWord ? 'bg-orange-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
              } text-white`}
              disabled={isExportingWord}
            >
              {isExportingWord ? 'Generating Word Report...' : '📄 Export Report as Word'}
            </button>
          </>
        )}
      </div>

      {/* Right Panel */}
      <div className="w-3/4 p-4 overflow-auto flex flex-col font-sans">
        <div className="overflow-auto max-h-[60vh] bg-white shadow-lg rounded-lg mb-4">
          <table className="w-full border-collapse">
            <thead className="bg-gray-200 text-gray-700 sticky top-0 z-10 shadow-sm">
              <tr>
                {columns.map((col, index) => (
                  <th key={index} className="p-3 border border-gray-300 text-left text-sm font-semibold">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="even:bg-gray-50 hover:bg-gray-100 transition duration-100 ease-in-out">
                  {columns.map((col, colIndex) => (
                    <td
                      key={colIndex}
                      className={`p-3 border border-gray-200 text-sm ${
                        isFailedIndex(rowIndex, col) // Pass column name to check against failed indices map
                          ? 'bg-red-100 font-medium text-red-800'
                          : 'text-gray-800'
                      }`}
                    >
                      {row[col] !== undefined && row[col] !== null ? String(row[col]) : "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Validation Report */}
        {validationReport && Object.keys(validationReport).length > 0 && (
          <div className="bg-white shadow-lg rounded-lg p-6 overflow-auto mt-4">
            <h3 className="text-2xl font-bold mb-6 text-gray-800">Validation Report</h3>
            {Object.entries(validationReport).map(([key, value]) => (
              <div key={key} className="mb-6 border border-gray-200 rounded-lg p-4 bg-gray-50 shadow-sm">
                <h4 className="font-bold text-blue-700 text-xl mb-3">Column: {value.Column || key}</h4>
                {Array.isArray(value) ? (
                  value.map((item, index) => (
                    <div key={index} className="mt-3 ml-2 text-sm text-gray-800 border-t border-gray-200 pt-3">
                      <p className="mb-1"><strong>Expectation:</strong> {item.Expectation}</p>
                      <p className="mb-1">
                        <strong>Success:</strong>{" "}
                        <span className={item.Success ? "text-green-600 font-semibold" : "text-red-600 font-semibold"}>
                          {item.Success ? "✅ Passed" : "❌ Failed"}
                        </span>
                      </p>
                      {!item.Success && (
                        <ul className="list-disc list-inside ml-4 text-gray-700">
                          <li className="mb-0.5"><strong>Failed %:</strong> {item["Failed %"] || item["Failed_%"] || "-"}</li>
                          {item["Failed Indices"] && item["Failed Indices"].length > 0 && (
                            <li className="mb-0.5">
                              <strong>Failed Indices:</strong> {item["Failed Indices"].join(", ")}
                            </li>
                          )}
                          <li className="mb-0.5"><strong>Failed Records:</strong> {item["Failed Records"] || item["Failed_Records"] || "-"}</li>
                          <li className="mb-0.5"><strong>Passed %:</strong> {item["Passed %"] || "-"}</li>
                          <li className="mb-0.5"><strong>Passed Records:</strong> {item["Passed Records"] || "-"}</li>
                          {item["Sample Failures"] && item["Sample Failures"].length > 0 && (
                            <li className="mb-0.5">
                              <strong>Sample Failures:</strong> {item["Sample Failures"].map(f => String(f)).join(", ")}
                            </li>
                          )}
                        </ul>
                      )}
                      <p className="mt-1"><strong>Total Records:</strong> {item["Total Records"] || "-"}</p>
                    </div>
                  ))
                ) : (
                  <div className="mt-3 ml-2 text-sm text-gray-800">
                    <p className="mb-1"><strong>Expectation:</strong> {value.Expectation}</p>
                    <p className="mb-1">
                      <strong>Success:</strong>{" "}
                      <span className={value.Success ? "text-green-600 font-semibold" : "text-red-600 font-semibold"}>
                        {value.Success ? "✅ Passed" : "❌ Failed"}
                      </span>
                    </p>
                    {!value.Success && (
                      <ul className="list-disc list-inside ml-4 text-gray-700">
                        <li className="mb-0.5"><strong>Failed %:</strong> {value["Failed %"] || value["Failed_%"] || "-"}</li>
                        {value["Failed Indices"] && value["Failed Indices"].length > 0 && (
                          <li className="mb-0.5">
                            <strong>Failed Indices:</strong> {value["Failed Indices"].join(", ")}
                          </li>
                        )}
                        <li className="mb-0.5"><strong>Failed Records:</strong> {value["Failed Records"] || value["Failed_Records"] || "-"}</li>
                        <li className="mb-0.5"><strong>Passed %:</strong> {value["Passed %"] || "-"}</li>
                        <li className="mb-0.5"><strong>Passed Records:</strong> {value["Passed Records"] || "-"}</li>
                        {value["Sample Failures"] && value["Sample Failures"].length > 0 && (
                          <li className="mb-0.5">
                            <strong>Sample Failures:</strong> {value["Sample Failures"].map(f => String(f)).join(", ")}
                          </li>
                        )}
                      </ul>
                    )}
                    <p className="mt-1"><strong>Total Records:</strong> {value["Total Records"] || "-"}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default TableView;
