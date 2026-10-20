"use client";

import type { SelectHTMLAttributes } from "react";

type AppSelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  wrapperClassName?: string;
};

export function AppSelect({
  className = "",
  wrapperClassName = "",
  children,
  disabled,
  ...props
}: AppSelectProps) {
  return (
    <div
      className={`relative inline-flex min-w-0 align-middle rounded border border-border ${
        disabled ? "opacity-50" : ""
      } ${wrapperClassName}`}
    >
      <select
        disabled={disabled}
        className={`w-full min-w-0 cursor-pointer appearance-none bg-transparent px-2 py-1 pr-7 text-xs text-inherit focus:outline-none disabled:cursor-not-allowed ${className}`}
        {...props}
      >
        {children}
      </select>
      <svg
        aria-hidden
        viewBox="0 0 24 24"
        className="pointer-events-none absolute right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 text-current opacity-70"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>
  );
}
