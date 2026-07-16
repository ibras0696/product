import { AuthControls } from "@/modules/auth";
import { LandingShowcase } from "@/modules/landing-showcase";

export function App() {
  return <LandingShowcase accountSlot={<AuthControls />} />;
}
