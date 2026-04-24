import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@/app/globals.css";
import { AppShell } from "@/components/app-shell";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "StudyPilot Phase 3",
  description: "Formal StudyPilot frontend wired for the phase 3 vertical integration loop",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
