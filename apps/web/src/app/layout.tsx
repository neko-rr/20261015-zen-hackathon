import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

const PREFS_BOOT = `(function(){try{var d=document.documentElement;var t=localStorage.getItem("drawref:themeId");var allowed={"default":1,"lime-right":1,"lime-dark":1,"emerald-dark":1,"sky-dark":1,"blue-dark":1,"pink-dark":1,"purple-dark":1,"orange-dark":1,"red-dark":1,"yellow-dark":1};if(t&&allowed[t]){d.setAttribute("data-theme",t);}var l=localStorage.getItem("drawref:locale");if(l==="en"||l==="ja"){d.lang=l;}}catch(e){}})();`;

export const metadata: Metadata = {
  title: "絵の資料",
  description: "写真を層と関節に分け、出典を残す",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja" data-theme="default" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{ __html: PREFS_BOOT }} />
        {children}
      </body>
    </html>
  );
}
