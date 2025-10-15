import React, { useState, useEffect, useCallback } from "react";
import {
  Upload,
  FileText,
  MessageSquare,
  Search,
  Loader2,
  AlertCircle,
  CheckCircle,
  List,
} from "lucide-react";
import "./DocuMateApp.css";

import { API_BASE_URL } from "../config";

const DocuMateApp = () => {
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  // const [extractedText, setExtractedText] = useState("");
  const [summary, setSummary] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [userDocuments, setUserDocuments] = useState([]);

  const [loading, setLoading] = useState({
    upload: false,
    question: false,
    search: false,
    documents: false,
  });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleDocumentSelection = useCallback(async (selectedDocId) => {
    setDocumentId(selectedDocId);
    setError(null);
    setSuccess(null);

    // setExtractedText("");
    setSummary("");
    setQuestion("");
    setAnswer("");
    setSearchQuery("");
    setSearchResults([]);

    try {
      setLoading((prev) => ({ ...prev, documents: true }));
      const res = await fetch(`${API_BASE_URL}/documents/${selectedDocId}`);
      if (!res.ok) {
        throw new Error(
          `Failed to load document details: ${res.status} ${res.statusText}`
        );
      }
      const doc = await res.json();
      // setExtractedText(doc.extracted_text || doc.content || doc.text || "");
      setSummary(doc.summary || "");
    } catch (err) {
      console.error("Error fetching document details:", err);
      setError(`Failed to load document: ${err.message}`);
    } finally {
      setLoading((prev) => ({ ...prev, documents: false }));
    }
  }, []);

  const fetchUserDocuments = useCallback(async () => {
    setLoading((prev) => ({ ...prev, documents: true }));
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) {
        throw new Error(`Failed to fetch documents: ${response.statusText}`);
      }
      const data = await response.json();
      setUserDocuments(data);

      if (!documentId && data.length > 0) {
        handleDocumentSelection(data[0].id);
      }
    } catch (err) {
      setError(`Failed to load documents: ${err.message}`);
    } finally {
      setLoading((prev) => ({ ...prev, documents: false }));
    }
  }, [documentId, handleDocumentSelection]);

  useEffect(() => {
    fetchUserDocuments();
  }, [fetchUserDocuments]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError(null);
      setSuccess(null);
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

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setDocumentId(data.document_id);
      // setExtractedText(data.extracted_text);
      setSummary(data.summary);
      setSuccess("PDF processed successfully!");
      fetchUserDocuments();
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setLoading((prev) => ({ ...prev, upload: false }));
    }
  };

  const handleAskQuestion = async () => {
    if (!documentId) {
      setError("Please select or upload a PDF first");
      return;
    }
    if (!question.trim()) {
      setError("Please enter a question");
      return;
    }

    setLoading((prev) => ({ ...prev, question: true }));
    setError(null);
    setAnswer("");

    try {
      const response = await fetch(`${API_BASE_URL}/ask-question`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_id: documentId,
          question: question,
        }),
      });

      if (!response.ok) {
        throw new Error(`Question failed: ${response.statusText}`);
      }

      const data = await response.json();
      setAnswer(data.answer);
    } catch (err) {
      setError(`Question failed: ${err.message}`);
    } finally {
      setLoading((prev) => ({ ...prev, question: false }));
    }
  };

  const handleSemanticSearch = async () => {
    if (!documentId) {
      setError("Please select or upload a PDF first");
      return;
    }
    if (!searchQuery.trim()) {
      setError("Please enter a search query");
      return;
    }

    setLoading((prev) => ({ ...prev, search: true }));
    setError(null);
    setSearchResults([]);

    try {
      const response = await fetch(`${API_BASE_URL}/semantic-search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_id: documentId,
          query: searchQuery,
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setSearchResults(data.results);
    } catch (err) {
      setError(`Search failed: ${err.message}`);
    } finally {
      setLoading((prev) => ({ ...prev, search: false }));
    }
  };

  return (
    <div className="app-container">
      <div className="content-wrapper">
        {/* Header */}
        <div className="header">
          <h1>DocuMate AI</h1>
          <p>Intelligent Document Assistant</p>
        </div>

        {/* Notifications */}
        {error && (
          <div className="notification notification-error">
            <AlertCircle className="notification-icon" size={20} />
            <p>{error}</p>
          </div>
        )}

        {success && (
          <div className="notification notification-success">
            <CheckCircle className="notification-icon" size={20} />
            <p>{success}</p>
          </div>
        )}

        {/* Upload Section */}
        <div className="card">
          <div className="card-header">
            <Upload className="card-header-icon" size={24} />
            <h2>Upload PDF</h2>
          </div>

          <div className="upload-controls">
            <div className="file-input-wrapper">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="file-input"
              />
            </div>
            <button
              onClick={handleUpload}
              disabled={!file || loading.upload}
              className="btn btn-primary"
            >
              {loading.upload ? (
                <>
                  <Loader2 className="spinner" size={20} />
                  Processing...
                </>
              ) : (
                <>
                  <Upload size={20} />
                  Upload
                </>
              )}
            </button>
          </div>

          {file && (
            <p className="selected-file">
              Selected file for upload: <span>{file.name}</span>
            </p>
          )}
        </div>

        {/* Document List */}
        <div className="card">
          <div className="card-header">
            <List className="card-header-icon" size={24} />
            <h2>Your Documents</h2>
          </div>
          {loading.documents ? (
            <p className="loading-text">
              <Loader2 className="spinner" size={20} /> Loading documents...
            </p>
          ) : userDocuments.length > 0 ? (
            <div className="document-selector">
              <label htmlFor="doc-select">Select a document:</label>
              <select
                id="doc-select"
                value={documentId || ""}
                onChange={(e) => handleDocumentSelection(e.target.value)}
                className="select-input"
              >
                <option value="" disabled>
                  -- Choose a document --
                </option>
                {userDocuments.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename} (ID: {doc.id.substring(0, 8)}...)
                  </option>
                ))}
              </select>
              {documentId && (
                <p className="selected-file">
                  Currently active:{" "}
                  <span>
                    {userDocuments.find((d) => d.id === documentId)?.filename ||
                      "Unknown Document"}
                  </span>
                </p>
              )}
            </div>
          ) : (
            <p>No documents uploaded yet. Upload a PDF above!</p>
          )}
        </div>

        {/* Summary and Features */}
        {documentId && (
          <>
            <div className="card">
              {/* Summary */}
              <div className="card">
                <div className="card-header">
                  <FileText className="card-header-icon" size={24} />
                  <h2>Summary</h2>
                </div>
                <div className="summary-box">
                  {summary ? (
                    <p>{summary}</p>
                  ) : (
                    <p className="placeholder-text">
                      Upload a PDF or select a document to see its summary.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Q&A + Search */}
            <div className="card">
              {/* Question Answering */}
              <div className="card">
                <div className="card-header">
                  <MessageSquare className="card-header-icon" size={24} />
                  <h2>Ask a Question (Direct RAG)</h2>
                </div>

                <div className="input-group">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleAskQuestion()}
                    placeholder="What would you like to know about this document?"
                    className="text-input"
                  />

                  <button
                    onClick={handleAskQuestion}
                    disabled={loading.question || !documentId}
                    className="btn btn-primary btn-full"
                  >
                    {loading.question ? (
                      <>
                        <Loader2 className="spinner" size={20} />
                        Processing...
                      </>
                    ) : (
                      "Get Answer"
                    )}
                  </button>

                  {answer && (
                    <div className="answer-box">
                      <p className="answer-label">Answer:</p>
                      <p className="answer-text">{answer}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Semantic Search */}
              <div className="card">
                <div className="card-header">
                  <Search className="card-header-icon" size={24} />
                  <h2>Semantic Search</h2>
                </div>

                <div className="input-group">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) =>
                      e.key === "Enter" && handleSemanticSearch()
                    }
                    placeholder="Search for relevant content..."
                    className="text-input"
                  />

                  <button
                    onClick={handleSemanticSearch}
                    disabled={loading.search || !documentId}
                    className="btn btn-primary btn-full"
                  >
                    {loading.search ? (
                      <>
                        <Loader2 className="spinner" size={20} />
                        Searching...
                      </>
                    ) : (
                      "Search"
                    )}
                  </button>

                  {searchResults.length > 0 && (
                    <div className="results-container">
                      <p className="results-header">
                        Results ({searchResults.length}):
                      </p>
                      {searchResults.map((result, idx) => (
                        <div key={idx} className="result-item">
                          <p className="result-number">Result {idx + 1}</p>
                          <p className="result-text">{result}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DocuMateApp;
