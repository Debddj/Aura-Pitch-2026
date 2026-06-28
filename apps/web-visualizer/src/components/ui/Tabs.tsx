import React from "react";

interface TabsProps {
  tabs: { id: string; label: string }[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export function Tabs({ tabs, activeTab, onChange, className = "" }: TabsProps) {
  return (
    <div className={`flex border-b border-cyber-border/40 mb-4 bg-cyber-bg/40 p-1 rounded-lg ${className}`}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex-1 py-1.5 text-xs font-mono font-medium rounded-md transition-all duration-200 ${
              isActive
                ? "bg-cyber-primary/10 text-cyber-primary border border-cyber-primary/20 shadow-glow/10"
                : "text-cyber-muted hover:text-cyber-text hover:bg-cyber-card/30"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
