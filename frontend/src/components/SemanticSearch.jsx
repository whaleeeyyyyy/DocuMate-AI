import React from "react";
import { Search, Loader2 } from "lucide-react";
import "./ComponentStyles.css";

const SemanticSearch = ({
  documentId,
  searchQuery,
  setSearchQuery,
  searchResults,
  setSearchResults,
  loading,
  setLoading,
  setError,
  API_BASE_URL,
}) => {
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError("Please enter a search query");
      return;
    }

    setLoading((prev) => ({ ...prev, search: true }));
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/semantic-search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: documentId, query: searchQuery }),
      });
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setSearchResults(data.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading((prev) => ({ ...prev, search: false }));
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <Search className="icon" />
        <h2>Semantic Search</h2>
      </div>
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder="Search content..."
        className="input-box"
        onKeyPress={(e) => e.key === "Enter" && handleSearch()}
      />
      <button onClick={handleSearch} disabled={loading.search}>
        {loading.search ? (
          <>
            <Loader2 className="spin" size={18} /> Searching...
          </>
        ) : (
          "Search"
        )}
      </button>

      {searchResults.length > 0 && (
        <div className="results-box">
          <p>
            <strong>Results ({searchResults.length})</strong>
          </p>
          {searchResults.map((r, i) => (
            <div key={i} className="result-item">
              <p className="result-text">{r}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SemanticSearch;
