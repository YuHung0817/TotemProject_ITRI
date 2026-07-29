import { useEffect, useState } from "react";

export type PresencePhase = "entering" | "entered" | "exiting";

export function usePresence(open:boolean, exitDuration=300) {
  const [present,setPresent]=useState(open);
  const [phase,setPhase]=useState<PresencePhase>(open ? "entered" : "exiting");

  useEffect(() => {
    let firstFrame=0;
    let secondFrame=0;
    let exitTimer=0;
    const duration=window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : exitDuration;

    if (open) {
      setPresent(true);
      setPhase("entering");
      firstFrame=requestAnimationFrame(() => {
        secondFrame=requestAnimationFrame(() => setPhase("entered"));
      });
    } else if (present) {
      setPhase("exiting");
      exitTimer=window.setTimeout(() => setPresent(false),duration);
    }

    return () => {
      cancelAnimationFrame(firstFrame);
      cancelAnimationFrame(secondFrame);
      clearTimeout(exitTimer);
    };
  },[open,present,exitDuration]);

  return {present,phase};
}
