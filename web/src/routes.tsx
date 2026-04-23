/**
 * Client-side routing — reads window.location.pathname.
 *
 * Routes:
 *   /              → Dashboard (App)
 *   /rancher       → RancherPhone PWA
 *   /cross-ranch   → CrossRanchView
 *   /attest/:hash  → AttestChainViewer (Phase 4 ATT-01)
 */

import { useState, useEffect } from "react";
import App from "@/App";
import { RancherPhone } from "@/components/RancherPhone";
import CrossRanchView from "@/components/CrossRanchView";
import { AttestChainViewer } from "@/components/AttestChainViewer";

const ATTEST_PREFIX = "/attest/";

export function Router() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  if (path.startsWith("/rancher")) {
    return <RancherPhone />;
  }
  if (path.startsWith("/cross-ranch")) {
    return <CrossRanchView />;
  }
  if (path.startsWith(ATTEST_PREFIX)) {
    const hash = decodeURIComponent(path.slice(ATTEST_PREFIX.length));
    return <AttestChainViewer hash={hash} />;
  }
  return <App />;
}
