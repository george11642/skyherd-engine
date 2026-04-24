export default function Footer() {
  return (
    <footer className="relative pt-12 pb-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="border-t border-slate-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <svg
              className="w-6 h-6 text-amber-500"
              viewBox="0 0 32 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M16 4L28 12V20L16 28L4 20V12L16 4Z"
                stroke="currentColor"
                strokeWidth="2"
                fill="currentColor"
                fillOpacity="0.15"
              />
              <path
                d="M10 16H22M16 10V22"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
            <span className="text-sm font-semibold text-slate-300">
              SkyHerd
            </span>
          </div>

          <p className="text-xs text-slate-500">
            © SkyHerd 2026 · Albuquerque, NM
          </p>
        </div>
      </div>
    </footer>
  );
}
