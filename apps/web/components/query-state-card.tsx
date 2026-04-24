"use client";

import React from "react";
import type { ReactNode } from "react";

type QueryStateCardProps = {
  title: string;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage: string;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
  bodyClassName?: string;
};

export function QueryStateCard({
  title,
  loading,
  error,
  empty,
  emptyMessage,
  action,
  children,
  className,
  bodyClassName,
}: QueryStateCardProps) {
  let body = children;

  if (loading) {
    body = (
      <div className="space-y-3" aria-label="loading">
        <div className="h-4 w-1/3 animate-pulse bg-slate-200" />
        <div className="h-4 w-full animate-pulse bg-slate-200" />
        <div className="h-4 w-5/6 animate-pulse bg-slate-200" />
      </div>
    );
  } else if (error) {
    body = <p className="text-sm text-red-600">{error}</p>;
  } else if (empty) {
    body = <p className="text-sm text-slate-500">{emptyMessage}</p>;
  }

  return (
    <section
      className={[
        "border border-slate-200 bg-white p-6 transition hover:border-ink",
        className ?? "",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4 mb-4">
        <h2 className="text-xl font-bold text-ink">{title}</h2>
        {action}
      </div>
      <div className={bodyClassName ?? ""}>{body}</div>
    </section>
  );
}
