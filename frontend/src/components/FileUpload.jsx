import React from "react";
import { Upload, Loader2 } from "lucide-react";
import "./ComponentStyles.css";

const FileUpload = ({
  file,
  setFile,
  loading,
  setLoading,
  setError,
  setSuccess,
  setDocumentId,
  setExtractedText,
  setSummary,
  setEntities,
  API_BASE_URL,
}) => {
  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
      setError(null);
    } else {
      setError("Please select a valid PDF file");
      setFile(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a PDF file first");
      return;
    }

    setLoading((prev) => ({ ...prev, upload: true }));
    setError(null);
    setSuccess(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok)
        throw new Error(`Upload failed: ${response.statusText}`);

      const data = await response.json();
      setDocumentId(data.document_id);
      setExtractedText(data.extracted_text);
      setSummary(data.summary);
      setEntities(data.entities);
      setSuccess("PDF processed successfully!");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading((prev) => ({ ...prev, upload: false }));
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <Upload className="icon" />
        <h2>Upload PDF</h2>
      </div>

      <div className="upload-actions">
        <input type="file" accept=".pdf" onChange={handleFileChange} />
        <button onClick={handleUpload} disabled={!file || loading.upload}>
          {loading.upload ? (
            <>
              <Loader2 className="spin" size={18} /> Processing...
            </>
          ) : (
            "Upload"
          )}
        </button>
      </div>

      {file && <p className="file-name">Selected: {file.name}</p>}
    </div>
  );
};

export default FileUpload;
