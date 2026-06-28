import React from "react";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "success" | "warning" | "danger" | "muted";
  children: React.ReactNode;
}

export function Badge({ children, variant = "primary", className = "", ...props }: BadgeProps) {
  const styles = {
    primary: "bg-cyber-primary/10 text-cyber-primary border border-cyber-primary/20",
    success: "bg-cyber-success/10 text-cyber-success border border-cyber-success/20",
    warning: "bg-cyber-warning/10 text-cyber-warning border border-cyber-warning/20",
    danger: "bg-cyber-danger/10 text-cyber-danger border border-cyber-danger/20",
    muted: "bg-cyber-muted/10 text-cyber-muted border border-cyber-border/40",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium leading-none ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
