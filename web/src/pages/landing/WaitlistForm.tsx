import { useState } from "react";
import { motion } from "framer-motion";

interface WaitlistFormProps {
  variant?: "hero" | "footer";
}

export default function WaitlistForm({ variant = "hero" }: WaitlistFormProps) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      setSubmitted(true);
    }
  };

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-center gap-2 text-green-400 font-medium"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
        <span>You&apos;re on the list. We&apos;ll be in touch.</span>
      </motion.div>
    );
  }

  const isFooter = variant === "footer";

  return (
    <form
      onSubmit={handleSubmit}
      className={`flex ${isFooter ? "flex-col sm:flex-row" : "flex-col sm:flex-row"} gap-3 w-full max-w-md`}
    >
      <label htmlFor={`waitlist-email-${variant}`} className="sr-only">
        Email address
      </label>
      <input
        id={`waitlist-email-${variant}`}
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="your@email.com"
        className="flex-1 rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none transition-colors"
      />
      <button
        type="submit"
        className="rounded-lg bg-amber-600 px-6 py-3 text-sm font-semibold text-white hover:bg-amber-500 transition-colors duration-200 whitespace-nowrap cursor-pointer"
      >
        {isFooter ? "Join Waitlist" : "Request Early Access"}
      </button>
    </form>
  );
}
