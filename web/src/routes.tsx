/**
 * Client-side routing — / → Dashboard, /rancher → RancherPhone PWA.
 *
 * Minimal router (no react-router dep) — reads window.location.pathname.
 */

import { useState, useEffect } from "react";
import App from "@/App";
import { RancherPhone } from "@/components/RancherPhone";

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

  return <App />;
}
