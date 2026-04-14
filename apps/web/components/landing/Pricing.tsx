const PLANS = [
  {
    name: "Solo",
    price: "$19",
    period: "/mo",
    description: "One seat. Two databases. Everything included.",
    features: [
      "1 seat",
      "2 database connections",
      "All supported engines",
      "Real-time schema monitoring",
      "Full impact analysis",
      "Custom webhook + Slack + PagerDuty alerts",
      "Email notifications",
      "14-day free trial — no credit card required",
    ],
    cta: "Start free trial",
    href: "/auth/signup",
    featured: true,
  },
  {
    name: "Teams",
    price: "$79",
    period: "/mo",
    description: "Multiple seats. Multiple databases. Built for your team.",
    features: [
      "Up to 10 seats",
      "Up to 10 database connections",
      "All supported engines",
      "Team alert routing",
      "Role-based access",
      "Priority support",
    ],
    cta: "Get started",
    href: "/auth/signup",
    featured: false,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For regulated industries and large organizations.",
    features: [
      "Everything in Teams",
      "Unlimited databases",
      "VPC peering",
      "SSO / SAML",
      "SOC 2 report access",
      "Custom data retention",
      "Dedicated SLA",
    ],
    cta: "Talk to us",
    href: "/auth/signup",
    featured: false,
  },
];

export default function Pricing() {
  return (
    <div className="py-20">
      <p className="font-mono text-[10px] uppercase tracking-[1.5px] text-[#00e87a] mb-3.5">
        Pricing
      </p>
      <h2 className="text-[36px] font-semibold text-white leading-[1.15] tracking-[-1.2px] mb-3.5">
        Simple pricing.<br />No surprises.
      </h2>
      <p className="text-base text-white/45 max-w-[560px] leading-[1.65] mb-10">
        Start free on Solo. No credit card required. Upgrade when your team grows.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`relative flex flex-col rounded-[14px] p-7 border ${
              plan.featured
                ? "border-[rgba(0,232,122,0.2)] bg-gradient-to-b from-[rgba(0,232,122,0.04)] to-[#111]"
                : "border-white/[0.06] bg-[#111]"
            }`}
          >
            {plan.featured && (
              <div className="absolute top-[-1px] left-1/2 -translate-x-1/2 bg-[#00e87a] text-black text-[10px] font-bold font-mono px-3.5 py-1 rounded-b-lg tracking-[0.3px]">
                SOLO
              </div>
            )}
            {plan.featured && <div className="h-4" />}

            <div className="font-mono text-[14px] font-semibold text-white/45 uppercase tracking-[0.5px] mb-2.5">
              {plan.name}
            </div>

            <div className="text-[38px] font-semibold text-white tracking-[-1.5px] leading-none mb-1">
              {plan.price}
              {plan.period && (
                <sub className="text-sm font-normal text-white/45 tracking-normal ml-1">
                  {plan.period}
                </sub>
              )}
            </div>

            <p className="text-[13px] text-white/22 mb-6 leading-[1.5]">{plan.description}</p>

            <ul className="flex flex-col gap-2 mb-7 flex-1">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-[13px] text-white/45">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00e87a] opacity-60 shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>

            <a
              href={plan.href}
              className={`block text-center text-[13px] font-semibold py-3 rounded-lg transition-opacity tracking-[-0.1px] ${
                plan.featured
                  ? "bg-[#00e87a] text-black hover:opacity-85"
                  : "border border-white/[0.12] text-white/60 hover:border-white/25 hover:text-white"
              }`}
            >
              {plan.cta}
            </a>
          </div>
        ))}
      </div>

      <p className="mt-8 text-center text-[13px] text-white/22">
        All plans include real-time monitoring, full impact analysis, and multi-channel alerts.
        Solo includes a 14-day free trial — no credit card required.
      </p>
    </div>
  );
}
