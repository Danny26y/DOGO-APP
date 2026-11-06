# Open decisions

No business values below are silently treated as settled. Proposed defaults require approval.

| Decision | Impact | Proposed safe default | Approver |
|---|---|---|---|
| Standard/Express/Scheduled versus Standard/Express/Same Day/Scheduled | Quote schema and SLA | Configure tiers; expose only approved ones | Product/Operations |
| Express described as 24–36 hours | Customer promise | Omit SLA until confirmed | Product/Operations |
| Base fares, distance/weight pricing, zones, ₦3,500 example | Quotes and revenue | No assumed production fares; configurable approved rules | Finance/Operations |
| Rider/DOGO split: 70/30 or 60/40 | Settlement and reporting | No payout calculation until basis and split approved | Finance/Legal |
| Paystack versus Flutterwave and responsibilities | Payment UX and reconciliation | Provider adapters; sandbox only after flow/credentials approved | Finance/Engineering |
| Crypto: USDC/USDT, EVM or Tron | Compliance and settlement | Defer processing pending provider/network/legal decision | Legal/Finance |
| Custodial wallet, escrow and payouts | Regulated activity/accounting | Record auditable events; do not custody funds or represent a balance as money | Legal/Finance |
| Three launch apps versus Section 9 Web MVP | Staffing and launch scope | Build approved Web MVP only; confirm app commitments | Product/Leadership |
| Mobile includes hailing/drones; web defers them | API and operational dependencies | Defer hailing/drones from Web MVP | Product/Operations |
| Successful delivery and proof (OTP/photo/signature) | Disputes and status transitions | Explicit POD methods; no automatic delivered status | Operations/Legal |
| GPS/rider/dispatch availability | Tracking and ETA reliability | Show only recorded events; no fabricated location/ETA | Operations |
| Delivery-agent licensing, onboarding evidence and suspension process | Agent eligibility and safety | Core rider/driver profiles, manual assignment and status events are implemented; document-review policy and evidence storage remain separate | Operations/Legal |
| Cancellation reason categories, delivery cancellation windows and post-payment refunds | Customer/rider cancellation and finance | Unpaid marketplace orders may be cancelled with a required recorded reason and no fee; delivery-job fees, reason categories, and refunds remain disabled pending approved policy | Product/Operations/Finance |
| Final customer verification terms and privacy policy versions, URLs, and retention rules | Consent evidence and identity verification | Versioned acceptance capture is implemented but disabled until approved document versions and URLs are configured; account deletion/retention policy remains for Legal/Privacy | Legal/Privacy |
| Automated dispatch and live-location provider | Agent notifications, route tracking and customer ETA | Keep manual assignment as the provider-independent core; add an adapter after vendor and retention choices | Operations/Engineering |
| “DOGO Mail” versus “DOGO Mall” | Branding | Use “DOGO Mall” provisionally; confirm | Product/Marketing |
| KYB document storage and retention | Privacy and security | Keep upload disabled pending private storage and retention policy | Legal/Security |
