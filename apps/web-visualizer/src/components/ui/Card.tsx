import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function Card({ children, className = "", ...props }: CardProps) {
  return (
    <div
      className={`glass rounded-xl border border-cyber-border/40 p-4 transition-all duration-300 hover:shadow-glow/5 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
