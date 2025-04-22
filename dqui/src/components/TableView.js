import React, { useState, useEffect, use, useContext } from "react";
import { useLocation } from "react-router-dom";
import * as XLSX from "xlsx";
import Papa from "papaparse";
import FileContext from "../context/File/FileContext";
import QualityContext from "../context/Qualitychecks/QualityContext";

function TableView() {
  const location = useLocation();
  const file = location.state?.file;
  const filecontext=useContext(FileContext);
  const {data,val}=filecontext;
  const qualityContext = useContext(QualityContext);
  const { ruleids } = qualityContext;

  const [columns, setColumns] = useState([]);
  const [genrule,setgenrule]=useState(false);
  const [generatedRules, setGeneratedRules] = useState([]);
  const [rows, setRows] = useState([]);
  const [selectedColumn, setSelectedColumn] = useState("");
  const [selectedType, setSelectedType] = useState("");
  const [rules, setRules] = useState([{ type: "", value: "" }]);
  const [savedRules, setSavedRules] = useState({}); // { column: { type, rules } }

  const ruleOptions = {
    string: ["not_null", "contains", "starts_with", "ends_with"],
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
          setColumns(Object.keys(result.data[0]));
          setRows(result.data);
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

  // const handleAddRule = () => {
  //   setRules([...rules, { type: "", value: "" }]);
  // };

  const handleRuleRemoval = (index,column) => {
    const updatedRules = savedRules[column].rules.filter((_, i) => i !== index);
    setSavedRules((prev) => ({
      ...prev,
      [column]: {
        ...prev[column],
        rules: updatedRules.length > 0 ? updatedRules : [{ type: "", value: "" }],
      },
    }));
    //if saved rules are empty, remove it from savedRules
    if (updatedRules.length === 0) {
      const { [column]: _, ...rest } = savedRules;
      setSavedRules(rest);
    }
  }

  // const handleRemoveRule = (indexToRemove) => {
  //   const updatedRules = rules.filter((_, i) => i !== indexToRemove);
  //   setRules(updatedRules.length > 0 ? updatedRules : [{ type: "", value: "" }]);
  // };

  const handleRuleTypeChange = (index, value) => {
    const updated = [...rules];
    updated[index].type = value;
    updated[index].value = "";
    setRules(updated);
  };

  const handleRuleValueChange = (index, value) => {
    const updated = [...rules];
    updated[index].value = value;
    setRules(updated);
  };

  const handleGenerateRules = () => {
    if (!selectedColumn) return;
  
    const gen_rules = data.file_info.gen_rule || {};
  
    const rulesForColumn = gen_rules[selectedColumn];
  
    if (!rulesForColumn || !rulesForColumn.rules || rulesForColumn.rules.length === 0) {
      alert("No generative rules found for this column.");
      return;
    }
  
    const formattedRules = rulesForColumn.rules.map(rule => ({
      type: rule.type, // it's called 'type' in your JSON
      value: rule.value || "",
    }));
  
    setSavedRules(prev => {
      const existing = prev[selectedColumn]?.rules || [];
      return {
        ...prev,
        [selectedColumn]: {
          type: rulesForColumn.type,
          rules: [...existing, ...formattedRules],
        }
      };
    });
  
    setgenrule(true);
  };
    


  const handleSaveRule = () => {
    if (!selectedColumn || !selectedType) return;
  
    const cleanedRules = rules.filter(
      (r) => r.type && (r.type === "not_null" || r.value)
    );
  
    setSavedRules((prev) => {
      const existingRules = prev[selectedColumn]?.rules || [];
      return {
        ...prev,
        [selectedColumn]: {
          type: selectedType,
          rules: [...existingRules, ...cleanedRules],  
        },
      };
    });
    setRules([{ type: "", value: "" }]);
  };

  // Submit and fetch rules
  const handleSubmit = async () => {
    const columnRules = savedRules[selectedColumn].rules || [];
    console.log(savedRules)
  
    alert(
      `Column: ${selectedColumn}\nType: ${selectedType}\nRules:\n${columnRules
        .map((r) => `- ${r.type} ${r.value ? `: ${r.value}` : ""}`)
        .join("\n")}`
    );
    console.log("Submitting rules:", columnRules);
  
    const formattedRules = Object.entries(savedRules).map(([column, data]) => ({
      column,
      dataType: data.type,
      rules: (data.rules || [])
        .filter(r => r.type && (r.type === "not_null" || r.value))
        .map(r => ({
          rule_id: ruleids[r.type],
          value: r.value
        }))
    }));
    console.log("Formatted rules:", formattedRules);
    console.log("savedRules:", savedRules);
  
    try {
      const response = await fetch('http://localhost:8000/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formattedRules),
      });
  
      const result = await response.json();
  
      if (result.success) {
        alert("Validation completed! Check the console for results.");
        console.log(result.data);
      } else {
        alert(`Error: ${result.error || "Unknown error"}`);
      }
    } catch (error) {
      alert(`Failed to submit rules: ${error.message}`);
      console.error("Error submitting rules:", error);
    }
  };
  


  return (
    <div className="h-screen flex bg-gray-100">
      {/* Left Panel */}
      <div className="w-1/4 bg-white shadow-md p-4 overflow-auto">
        <h3 className="text-lg font-semibold mb-4">Configure Column</h3>

        <label className="block text-sm font-medium mb-1">Select Column:</label>
        <select
          className="w-full p-2 border rounded mb-4"
          value={selectedColumn}
          onChange={(e) => {
            setSelectedColumn(e.target.value);
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
            {val[selectedColumn] && val[selectedColumn].map((item, index) => (
              <div
                key={index}
                className={`border-l-4 rounded-lg p-4 mb-4 shadow-sm break-words ${
                  item.Success ? "border-green-500 bg-green-50" : "border-red-500 bg-red-50"
                }`}
              >
                <h5 className={`text-lg font-semibold ${item.Success ? "text-green-700" : "text-red-700"}`}>
                  {item.Expectation}
                </h5>
                <p className="text-sm font-medium mt-1">
                  Success:{" "}
                  <span className={item.Success ? "text-green-600" : "text-red-600"}>
                    {item.Success ? "✅ Passed" : "❌ Failed"}
                  </span>
                </p>

                {!item.Success && (
                  <div className="mt-2 ml-2 text-sm text-gray-800">
                    <ul className="list-disc list-inside">
                      <li><strong>Failed %:</strong> {item["Failed %"] || item["Failed_%"] || "-"}</li>
                      <li><strong>Failed Records:</strong> {item["Failed Records"] || item["Failed_Records"] || "-"}</li>
                      <li><strong>Passed %:</strong> {item["Passed %"] || "-"}</li>
                      <li><strong>Total Records:</strong> {item["Total Records"] || "-"}</li>
                    </ul>

                    {item["Sample Failures"] && item["Sample Failures"].length > 0 && (
                      <div className="mt-2">
                        <strong>Sample Failures:</strong>
                        <ul className="list-disc list-inside ml-4">
                          {item["Sample Failures"].map((fail, i) => (
                            <li key={i}>{fail}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            <label className="block text-sm font-medium mb-1">Select Data Type:</label>
            <select
              className="w-full p-2 border rounded mb-4"
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value);
                setRules([{ type: "", value: "" }]);
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
                <label className="block text-sm font-medium mb-2">Rules:</label>
                {rules.map((rule, index) => (
                  <div key={index} className="mb-3">
                    <div className="flex items-center gap-2 mb-1">
                      <select
                        className="w-full p-2 border rounded"
                        value={rule.type}
                        onChange={(e) => handleRuleTypeChange(index, e.target.value)}
                      >
                        <option value="">-- Select Rule --</option>
                        {ruleOptions[selectedType]?.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                      {/* <button
                        className="text-red-500 hover:text-red-700 text-lg font-bold"
                        onClick={() => handleRemoveRule(index)}
                      >
                        ❌
                      </button> */}
                    </div>

                    {["range", "between"].includes(rule.type) ? (
                      <div className="flex gap-2">
                        <input
                          className="w-1/2 p-2 border rounded"
                          placeholder="Min"
                          value={rule.value.split(",")[0] || ""}
                          onChange={(e) =>
                            handleRuleValueChange(index, `${e.target.value},${rule.value.split(",")[1] || ""}`)
                          }
                        />
                        <input
                          className="w-1/2 p-2 border rounded"
                          placeholder="Max"
                          value={rule.value.split(",")[1] || ""}
                          onChange={(e) =>
                            handleRuleValueChange(index, `${rule.value.split(",")[0] || ""},${e.target.value}`)
                          }
                        />
                      </div>
                    ) : ["contains", "starts_with", "ends_with", "min", "max", "equal_to", "not_equal_to", "before", "after", "true_ratio", "false_ratio"].includes(rule.type) ? (
                      <input
                        className="w-full p-2 border rounded mt-1"
                        placeholder="Enter value"
                        value={rule.value}
                        onChange={(e) => handleRuleValueChange(index, e.target.value)}
                      />
                    ) : null}
                  </div>
                ))}

                {/* <button
                  onClick={handleAddRule}
                  className="w-full bg-blue-100 hover:bg-blue-200 text-blue-700 py-1 px-2 rounded mb-2"
                >
                  + Add Rule
                </button> */}

                <button
                  onClick={handleSaveRule}
                  className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded"
                >
                  ✅ Save Rule
                </button>
              </>
            )}
          </>
        )}

        {Object.keys(savedRules).length > 0 && (
          <div className="mt-6 border-t pt-4">
            <h4 className="text-md font-semibold mb-2">Saved Rules</h4>
            {Object.entries(savedRules).map(([column, data]) => (
              <div key={column} className="border rounded-lg p-3 mb-3 bg-gray-50">
                <h5 className="font-bold text-blue-700">{column}</h5>
                <p className="text-sm text-gray-600 italic">Type: {data.type}</p>
                <ul className="list-disc list-inside mt-1 text-sm text-gray-800">
                  {data.rules.map((r, i) => (
                    <li key={i}>
                      {r.type} {r.value && `: ${r.value}`}
                      <button onClick={()=>handleRuleRemoval(i,column)}>❌</button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

      <button
        onClick={handleGenerateRules}
        className="w-full bg-purple-600 hover:bg-purple-700 text-white py-2 mt-2 rounded"
      >
        🎯 Show Generative Rules
      </button>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded mt-4"
        >
          Submit Validation
        </button>
      </div>

      {/* Right Panel */}
      <div className="w-3/4 p-4 overflow-auto">
        <div className="overflow-auto max-h-[80vh] bg-white shadow-md rounded-lg">
          <table className="w-full border-collapse">
            <thead className="bg-gray-300 text-gray-700">
              <tr>
                {columns.map((col, index) => (
                  <th key={index} className="p-2 border text-left">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="even:bg-gray-100">
                  {columns.map((col, colIndex) => (
                    <td key={colIndex} className="p-2 border">
                      {row[col] !== undefined && row[col] !== null
                        ? String(row[col])
                        : "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
  
}

export default TableView;
