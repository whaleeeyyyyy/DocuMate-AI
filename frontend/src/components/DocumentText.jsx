import React from "react";
import { FileText } from "lucide-react";
import EntityLegend from "./EntityLegend";
import "./ComponentStyles.css";

const entityColors = {
  PERSON: "blue",
  ORG: "green",
  LOC: "purple",
  DATE: "gold",
  GPE: "pink",
  MONEY: "orange",
  DEFAULT: "gray",
};

const highlightEntities = (text, entities) => {
  if (!text || !entities || entities.length === 0) return <span>{text}</span>;

  const sorted = [...entities].sort((a, b) => a.start - b.start);
  const elements = [];
  let last = 0;

  sorted.forEach((e, i) => {
    if (e.start > last)
      elements.push(<span key={`t-${i}`}>{text.slice(last, e.start)}</span>);
    elements.push(
      <span
        key={`e-${i}`}
        className={`entity entity-${(
          entityColors[e.label] || entityColors.DEFAULT
        ).toLowerCase()}`}
        title={e.label}
      >
        {text.slice(e.start, e.end)}
      </span>
    );
    last = e.end;
  });

  if (last < text.length)
    elements.push(<span key="end">{text.slice(last)}</span>);
  return <>{elements}</>;
};

const DocumentText = ({ extractedText, entities }) => (
  <div className="card">
    <div className="card-header">
      <FileText className="icon" />
      <h2>Document Text</h2>
    </div>
    <EntityLegend />
    <div className="text-box">{highlightEntities(extractedText, entities)}</div>
  </div>
);

export default DocumentText;
