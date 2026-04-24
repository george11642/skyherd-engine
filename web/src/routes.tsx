/**
 * Client-side routing — reads window.location.pathname.
 *
 * Routes:
 *   /              → LandingPage (marketing)
 *   /demo          → Dashboard (App)
 *   /rancher       → RancherPhone PWA
 *   /cross-ranch   → CrossRanchView
 *   /attest/:hash  → AttestChainViewer (Phase 4 ATT-01)
 *   *              → LandingPage (fallback — safer than dumping into ops console)
 */

import { useState, useEffect } from "react";
import App from "@/App";
import { RancherPhone } from "@/components/RancherPhone";
import CrossRanchView from "@/components/CrossRanchView";
import { AttestChainViewer } from "@/components/AttestChainViewer";
import LandingPage from "@/pages/landing/LandingPage";

const ATTEST_PREFIX = "/attest/";

export type Route =
  | { kind: "landing" }
  | { kind: "app" }
  | { kind: "rancher" }
  | { kind: "cross-ranch" }
  | { kind: "attest"; hash: string };

/**
 * Pure pathname → route descriptor. Exported for unit tests so the
 * router does not require a jsdom window for its truth table.
 */
export function resolveRoute(pathname: string): Route {
  if (pathname === "/demo" || pathname.startsWith("/demo/")) {
    return { kind: "app" };
  }
  if (pathname === "/rancher" || pathname.startsWith("/rancher/")) {
    return { kind: "rancher" };
  }
  if (pathname === "/cross-ranch" || pathname.startsWith("/cross-ranch/")) {
    return { kind: "cross-ranch" };
  }
  if (pathname.startsWith(ATTEST_PREFIX)) {
    const hash = decodeURIComponent(pathname.slice(ATTEST_PREFIX.length));
    return { kind: "attest", hash };
  }
  if (pathname === "/") {
    return { kind: "landing" };
  }
  // Unknown routes → landing fallback (never dump visitors into /demo).
  return { kind: "landing" };
}

export function Router() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const route = resolveRoute(path);
  switch (route.kind) {
    case "app":
      return <App />;
    case "rancher":
      return <RancherPhone />;
    case "cross-ranch":
      return <CrossRanchView />;
    case "attest":
      return <AttestChainViewer hash={route.hash} />;
    case "landing":
      return <LandingPage />;
  }
}
