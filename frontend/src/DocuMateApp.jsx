import React, { useState } from "react";
import FileUpload from "./components/FileUpload";
import DocumentText from "./components/DocumentText";
import Summary from "./components/Summary";
import QuestionAnswer from "./components/QuestionAnswer";
import SemanticSearch from "./components/SemanticSearch";
import Notifications from "./components/Notifications";
import "./DocuMateApp.css";

const DocuMateApp = () => {
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [extractedText, setExtractedText] = useState("");
  const [summary, setSummary] = useState("");
  const [entities, setEntities] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState({
    upload: false,
    question: false,
    search: false,
  });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const API_BASE_URL = "http://localhost:8000";

  return (
    <div className="documate-container">
      <header className="documate-header">
        <h1>DocuMate AI</h1>
        <p>Intelligent Document Assistant</p>
      </header>

      <Notifications error={error} success={success} />

      <FileUpload
        file={file}
        setFile={setFile}
        loading={loading}
        setLoading={setLoading}
        setError={setError}
        setSuccess={setSuccess}
        setDocumentId={setDocumentId}
        setExtractedText={setExtractedText}
        setSummary={setSummary}
        setEntities={setEntities}
        API_BASE_URL={API_BASE_URL}
      />

      {documentId && (
        <>
          <div className="documate-grid">
            <DocumentText extractedText={extractedText} entities={entities} />
            <Summary summary={summary} />
          </div>

          <div className="documate-grid">
            <QuestionAnswer
              documentId={documentId}
              question={question}
              setQuestion={setQuestion}
              answer={answer}
              setAnswer={setAnswer}
              loading={loading}
              setLoading={setLoading}
              setError={setError}
              API_BASE_URL={API_BASE_URL}
            />
            <SemanticSearch
              documentId={documentId}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              searchResults={searchResults}
              setSearchResults={setSearchResults}
              loading={loading}
              setLoading={setLoading}
              setError={setError}
              API_BASE_URL={API_BASE_URL}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default DocuMateApp;
