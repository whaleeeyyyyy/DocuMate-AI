import React from "react";
import { FileText } from "lucide-react";
import "./ComponentStyles.css";

const Summary = ({ summary }) => (
  <div className="card">
    <div className="card-header">
      <FileText className="icon" />
      <h2>Summary</h2>
    </div>
    <div className="summary-box">{summary}</div>
  </div>
);

export default Summary;
