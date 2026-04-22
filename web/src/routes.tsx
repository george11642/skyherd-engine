/**
 * Client-side routing — reads window.location.pathname.
 * / → Dashboard, /rancher → RancherPhone PWA, /cross-ranch → CrossRanchView.
 */

import { useState, useEffect } from "react";
import App from "@/App";
import { RancherPhone } from "@/components/RancherPhone";
import CrossRanchView from "@/components/CrossRanchView";

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
  return <App />;
}
