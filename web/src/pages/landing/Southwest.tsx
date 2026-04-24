import { motion } from "framer-motion";

const reasons = [
  "Vast terrain that's impossible to patrol on horseback alone",
  "Real predator threats — coyotes, mountain lions, wolves",
  "Extreme heat, dust storms, and rugged conditions",
  "Ranches measured in thousands of acres, not hundreds",
];

export default function Southwest() {
  return (
    <section className="relative py-24 sm:py-32 bg-slate-900/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left: content */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6 }}
          >
            <p className="text-sm font-semibold text-amber-500 uppercase tracking-wider mb-3">
              Built for the Southwest
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight mb-6">
              We know this land because we&apos;re from it
            </h2>
            <p className="text-slate-400 leading-relaxed mb-8">
              SkyHerd was designed from day one for the realities of ranching in
              New Mexico, Arizona, and West Texas. This isn&apos;t a tech
              company adapting a consumer drone. This is a system built for the
              kind of country where the nearest neighbor is 20 miles away.
            </p>

            <ul className="space-y-4">
              {reasons.map((reason, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.4 }}
                  className="flex items-start gap-3"
                >
                  <svg
                    className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
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
                  <span className="text-sm text-slate-300">{reason}</span>
                </motion.li>
              ))}
            </ul>
          </motion.div>

          {/* Right: testimonial */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative"
          >
            {/* Decorative background */}
            <div className="absolute inset-0 bg-gradient-to-br from-amber-600/5 to-green-600/5 rounded-2xl" />

            <div className="relative p-8 sm:p-10 rounded-2xl border border-slate-800 bg-slate-900/60">
              <svg
                className="w-10 h-10 text-amber-600/40 mb-6"
                fill="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" />
              </svg>

              <blockquote className="text-lg text-slate-200 leading-relaxed mb-6">
                &ldquo;I was spending two days a week just riding fence and
                checking cattle. Now I get alerts on my phone if something&apos;s
                wrong. That&apos;s two days back with my family.&rdquo;
              </blockquote>

              <figcaption className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-sm font-bold text-slate-300">
                  JM
                </div>
                <p className="text-sm font-semibold text-slate-200">
                  James M., cattle rancher, Southern NM
                </p>
              </figcaption>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
