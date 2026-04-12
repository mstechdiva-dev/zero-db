const POINTS = [
  {
    title: "Read-only credentials only",
    description:
      "SchemaZero only ever connects with read-only credentials. We cannot write to your database.",
  },
  {
    title: "AES-256 encryption at rest",
    description:
      "Connection strings are encrypted with AES-256-GCM before storage. Decrypted only at connection time, never logged.",
  },
  {
    title: "Schema metadata only",
    description:
      "We capture table names, column types, indexes, and constraints — never row-level data, never your application data.",
  },
  {
    title: "SOC 2 Type II audit in progress",
    description:
      "We are undergoing SOC 2 Type II certification. Report available to Enterprise customers on request.",
  },
  {
    title: "VPC peering (Enterprise)",
    description:
      "Enterprise customers can connect via VPC peering for zero-public-internet database access.",
  },
  {
    title: "SSO/SAML (Enterprise)",
    description:
      "Enterprise plans include SSO/SAML integration for centralized identity management.",
  },
];

export default function Security() {
  return (
    <div className="pt-16 pb-12">
      <h2 className="text-3xl font-bold text-white mb-4">Security</h2>
      <p className="text-gray-400 mb-12 text-lg max-w-2xl">
        SchemaZero never sees your data. It only sees your structure.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {POINTS.map((point) => (
          <div
            key={point.title}
            className="bg-[#111] border border-gray-800 rounded-xl p-6"
          >
            <div className="flex items-start gap-3">
              <span className="text-[#00e87a] mt-0.5">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 0a8 8 0 110 16A8 8 0 018 0zm3.646 5.646a.5.5 0 00-.707 0L7 9.586 5.061 7.646a.5.5 0 10-.707.707l2.293 2.293a.5.5 0 00.707 0l4.293-4.293a.5.5 0 000-.707z" />
                </svg>
              </span>
              <div>
                <h3 className="text-white font-semibold">{point.title}</h3>
                <p className="text-gray-400 text-sm mt-1 leading-relaxed">
                  {point.description}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
