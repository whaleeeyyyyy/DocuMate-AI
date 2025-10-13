import React from "react";
import "./ComponentStyles.css";

const labels = ["PERSON", "ORG", "LOC", "DATE", "GPE", "MONEY"];

const EntityLegend = () => (
  <div className="entity-legend">
    {labels.map((label) => (
      <span key={label} className={`entity entity-${label.toLowerCase()}`}>
        {label}
      </span>
    ))}
  </div>
);

export default EntityLegend;
