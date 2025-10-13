import React from "react";
import { MessageSquare, Loader2 } from "lucide-react";
import "./ComponentStyles.css";

const QuestionAnswer = ({
  documentId,
  question,
  setQuestion,
  answer,
  setAnswer,
  loading,
  setLoading,
  setError,
  API_BASE_URL,
}) => {
  const handleAsk = async () => {
    if (!question.trim()) {
      setError("Please enter a question");
      return;
    }
    setLoading((prev) => ({ ...prev, question: true }));
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/ask-question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: documentId, question }),
      });
      if (!res.ok) throw new Error("Failed to get answer");
      const data = await res.json();
      setAnswer(data.answer);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading((prev) => ({ ...prev, question: false }));
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <MessageSquare className="icon" />
        <h2>Ask a Question</h2>
      </div>
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Type your question..."
        className="input-box"
        onKeyPress={(e) => e.key === "Enter" && handleAsk()}
      />
      <button onClick={handleAsk} disabled={loading.question}>
        {loading.question ? (
          <>
            <Loader2 className="spin" size={18} /> Processing...
          </>
        ) : (
          "Get Answer"
        )}
      </button>
      {answer && (
        <div className="answer-box">
          <strong>Answer:</strong> {answer}
        </div>
      )}
    </div>
  );
};

export default QuestionAnswer;
