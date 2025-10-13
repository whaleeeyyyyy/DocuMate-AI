import React from "react";
import { AlertCircle, CheckCircle } from "lucide-react";
import "./ComponentStyles.css";

const Notifications = ({ error, success }) => (
  <>
    {error && (
      <div className="alert alert-error">
        <AlertCircle size={20} />
        <p>{error}</p>
      </div>
    )}
    {success && (
      <div className="alert alert-success">
        <CheckCircle size={20} />
        <p>{success}</p>
      </div>
    )}
  </>
);

export default Notifications;
