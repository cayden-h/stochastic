/** The v3 icons, drawn from the Figma file's vectors. Nav icons take currentColor so the active row can turn them white. */

const STROKE = { strokeWidth: 1.35, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, stroke: "currentColor", fill: "none" };

export type NavIconName = "dashboard" | "case" | "mapping" | "agents" | "log";

const NAV: Record<NavIconName, React.ReactNode> = {
  dashboard: <path d="M3 3H8.25V8.25H3V3ZM9.75 3H15V6H9.75V3ZM9.75 8.25H15V15H9.75V8.25ZM3 10.5H8.25V15H3V10.5Z" {...STROKE} />,
  case: (
    <>
      <path d="M3.75 3H11.25L14.25 6V15H3.75V3Z" {...STROKE} />
      <path d="M11.25 3V6H14.25" {...STROKE} />
    </>
  ),
  mapping: (
    <>
      <path d="M3 5.25H8.25M3 9H8.25M3 12.75H8.25M11.25 5.25H15M11.25 9H15M11.25 12.75H15" {...STROKE} />
      <path d="M8.25 5.25L11.25 9L8.25 12.75" {...STROKE} />
    </>
  ),
  agents: (
    <>
      <path d="M4.5 3.75H6.75C7.57843 3.75 8.25 4.42157 8.25 5.25V7.5C8.25 8.32843 7.57843 9 6.75 9H4.5C3.67157 9 3 8.32843 3 7.5V5.25C3 4.42157 3.67157 3.75 4.5 3.75Z" {...STROKE} />
      <path d="M11.25 3.75H13.5C14.3284 3.75 15 4.42157 15 5.25V7.5C15 8.32843 14.3284 9 13.5 9H11.25C10.4216 9 9.75 8.32843 9.75 7.5V5.25C9.75 4.42157 10.4216 3.75 11.25 3.75Z" {...STROKE} />
      <path d="M7.875 10.5H10.125C10.9534 10.5 11.625 11.1716 11.625 12V13.5C11.625 14.3284 10.9534 15 10.125 15H7.875C7.04657 15 6.375 14.3284 6.375 13.5V12C6.375 11.1716 7.04657 10.5 7.875 10.5Z" {...STROKE} />
    </>
  ),
  log: (
    <>
      <path d="M3.75 3.75H14.25M3.75 7.5H14.25M3.75 11.25H10.5" {...STROKE} />
      <path d="M15.375 12.75C15.375 13.7855 14.5355 14.625 13.5 14.625C12.4645 14.625 11.625 13.7855 11.625 12.75C11.625 11.7145 12.4645 10.875 13.5 10.875C14.5355 10.875 15.375 11.7145 15.375 12.75Z" {...STROKE} />
    </>
  ),
};

export function NavIcon({ name }: { name: NavIconName }) {
  return <svg width={18} height={18} viewBox="0 0 18 18" aria-hidden="true" className="shrink-0">{NAV[name]}</svg>;
}

/** The controller's mark: a silhouette in paper on the ink chip. */
export function SilhouetteIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="#F7F4EC" aria-hidden="true" className="shrink-0">
      <path d="M10 10.1C11.9882 10.1 13.6 8.48822 13.6 6.5C13.6 4.51177 11.9882 2.9 10 2.9C8.01177 2.9 6.4 4.51177 6.4 6.5C6.4 8.48822 8.01177 10.1 10 10.1Z" />
      <path d="M3 17.5C3 13.5 6.1 11 10 11C13.9 11 17 13.5 17 17.5H3Z" />
    </svg>
  );
}

/** The gateway's mark: a lock in code grey. */
export function LockIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" aria-hidden="true" className="shrink-0">
      <path d="M14 9H6C4.89543 9 4 9.89543 4 11V15.5C4 16.6046 4.89543 17.5 6 17.5H14C15.1046 17.5 16 16.6046 16 15.5V11C16 9.89543 15.1046 9 14 9Z" fill="#4A5560" />
      <path d="M6.5 9V6.5C6.5 5.57174 6.86875 4.6815 7.52513 4.02513C8.1815 3.36875 9.07174 3 10 3C10.9283 3 11.8185 3.36875 12.4749 4.02513C13.1313 4.6815 13.5 5.57174 13.5 6.5V9" stroke="#4A5560" strokeWidth={1.8} strokeLinecap="round" />
    </svg>
  );
}

export function UploadIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none" aria-hidden="true" className="shrink-0">
      <path d="M8 10.6667V3.33333M11.3333 6.66667L8 3.33333L4.66667 6.66667M2.66667 12.6667H13.3333" stroke="#1E6B52" strokeWidth={1.46667} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function FileIcon() {
  return (
    <svg width={22} height={27} viewBox="0 0 22 27" fill="none" aria-hidden="true" className="shrink-0">
      <path d="M2.35714 2.5H13.3571L19.6429 8.78571V24.5H2.35714V2.5Z" fill="white" stroke="#1E6B52" strokeWidth={1.25714} strokeLinejoin="round" />
      <path d="M13.3571 2.5V8.78571H19.6429" stroke="#1E6B52" strokeWidth={1.25714} strokeLinejoin="round" />
      <path d="M5.5 14.2857H16.5M5.5 18.2143H16.5M5.5 22.1429H12.5714" stroke="#1E6B52" strokeWidth={1.25714} strokeLinecap="round" />
    </svg>
  );
}
