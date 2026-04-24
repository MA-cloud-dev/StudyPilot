"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PropsWithChildren } from "react";

import { useCurrentWorkflow } from "@/lib/hooks/use-current-workflow";

const navigation = [
  { href: "/", label: "首页" },
  { href: "/plans", label: "计划中心" },
  { href: "/workbench", label: "学习工作台" },
  { href: "/knowledge", label: "知识仓库" },
  { href: "/assessments", label: "阶段测试" },
];

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const workflow = useCurrentWorkflow();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-canvas text-ink font-sans antialiased">
      {/* 侧边栏 */}
      <aside className="w-[220px] bg-warm border-r border-slate-200 flex flex-col shrink-0">
        <div className="h-20 px-8 flex items-center">
          <h2 className="text-xl font-bold tracking-wide text-ink">StudyPilot</h2>
        </div>
        
        <nav aria-label="Main navigation" className="flex flex-col pt-2 flex-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  "px-8 py-3.5 text-[0.95rem] transition relative border-l-4",
                  isActive
                    ? "bg-canvas text-accent border-accent font-medium"
                    : "border-transparent text-slate-600 hover:text-ink cursor-pointer",
                ].join(" ")}
              >
                {item.label}
              </Link>
            );
          })}
          <div className="flex-1" />
          <Link
            href="/profile"
            className={[
              "px-8 py-3.5 text-sm transition relative border-l-4",
              pathname === "/profile"
                ? "bg-canvas text-accent border-accent font-medium"
                : "border-transparent text-slate-400 hover:text-slate-600",
            ].join(" ")}
          >
            个人主页
          </Link>
        </nav>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 relative overflow-hidden bg-canvas">
        <div className="h-full overflow-y-auto px-12 py-12">{children}</div>
      </main>
    </div>
  );
}
