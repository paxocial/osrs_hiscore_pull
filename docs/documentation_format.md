# OSINT Mandatory Documentation Format (Corta‑Compliant)

**Document Created**: {{ISO8601_TIMESTAMP}}
**Author**: OSINT Site Auditor
**Confidence Score**: {{0.00–1.00}}
**Evidence Strength**: {{direct_empirical|multi_source_corrob|single_source_inferred|llm_generated_statistical|no_direct_evidence}}
**File References**: {{List of precise references to files, lines, or URLs used}}

> **Rule**: If any field above is missing, the report must not finalize. Return an error stating which field(s) are missing and stop.

---

## 1) Domain Information / Entity Overview

* **Target Type**: domain | website | digital entity (social handle, marketplace shop, brand page)
* **Target(s)**: Primary identifier(s) (e.g., example.com; @handle)
* **Declared Owner/Org**: As claimed on site/profile
* **Jurisdiction(s)**: Country/state inferred from public records or disclosures
* **Key Identifiers**: Registrant org, contact emails, analytics IDs, app IDs, business numbers
* **Verification Level**: none | partial | strong
* **Citations**: [Add specific references]
* **Section Confidence**: {{score}}

## 2) Hosting / Infrastructure

* **DNS**: NS, A/AAAA, MX, TXT, SPF, DKIM, DMARC (summarize)
* **IP/ASN**: Current IP(s), ASN, provider, geolocation
* **CDN/WAF**: Cloudflare, Fastly, etc. (and evidence)
* **Tech Stack**: server, CMS, JS frameworks, analytics, payment processors
* **Attribution Signals**: shared infrastructure with other properties
* **Citations**: [WHOIS/RDAP, DNS lookups, BGP/ASN, tech fingerprint]
* **Section Confidence**: {{score}}

## 3) Historical Footprint

* **Registration Timeline**: creation, updates, transfers
* **Hosting History**: IP/ASN changes, name server history
* **Content History**: snapshots/archived captures; notable deltas
* **Ownership Changes**: indicators from WHOIS/RDAP diffs or public statements
* **Citations**: [Archive/CT logs/WHOIS history]
* **Section Confidence**: {{score}}

## 4) Security & Certificates

* **TLS/SSL**: issuer, validity, SANs, key size, algs
* **Certificate Transparency**: historical certs, related domains
* **Email Auth**: SPF/DKIM/DMARC status
* **Known Exposures**: open directories, misconfigurations (public-only)
* **Citations**: [CT logs, TLS scans, mail DNS]
* **Section Confidence**: {{score}}

## 5) Online Presence

* **First‑party Links**: social profiles/pages linked from target
* **Third‑party Mentions**: business registries, press, app stores, marketplaces
* **Cross‑Platform Signals**: matching bios, handles, support emails, tracking IDs
* **Posting/Update Cadence**: frequency patterns (non‑intrusive)
* **Citations**: [Profile URLs, registry entries]
* **Section Confidence**: {{score}}

## 6) Reputation & Risk Assessment

* **User/Buyer Reports**: complaints, scam reports (credible sources only)
* **Trust Indicators**: corporate disclosures, verified badges, transparency pages
* **Red Flags** (if any): domain age vs. claims, mismatched business info, copy/paste policies, suspicious payment flows, high‑risk verticals
* **Risk Rating**: low | medium | high (justify with evidence)
* **Citations**: [Reputation databases, news, review platforms]
* **Section Confidence**: {{score}}

## 7) Summary & Conclusion

* **Bottom Line**: concise assessment
* **What’s Verified**: bullet list with sources
* **What’s Unverified**: bullet list + next steps (public-only methods)
* **Overall Confidence**: {{score}}

## 8) Method Notes

* **Sources Queried**: WHOIS/RDAP, DNS, CT logs, archive snapshots, BGP/ASN, tech fingerprinting, social/profile pages, business registries, reputable news/review sources
* **What Could Not Be Verified**: list and why
* **Data Handling**: public sources only; no intrusion or non‑consensual collection

---

### Evidence Strength Levels (OSINT‑specific)

* **direct_empirical** — You directly observed results from running lookups/scans that do not require authentication (e.g., live DNS answers, TLS fingerprint, CT log entries, archive snapshots). Save artifacts (screenshots, hashes).
* **multi_source_corrob** — Two or more independent public sources corroborate the claim (e.g., RDAP + CT logs + archived WHOIS).
* **single_source_inferred** — One credible public source supports the claim; you deduced implications.
* **llm_generated_statistical** — Narrative or structure synthesized by AI; must be clearly marked and never used as sole evidence.
* **no_direct_evidence** — Avoid. If present, remove or replace with verifiable sources.

### Confidence Score Guidance (interpretation for OSINT)

* **0.95–1.00** — Multiple authoritative sources align; artifacts captured; low ambiguity.
* **0.85–0.94** — Strong corroboration; minor gaps or recent changes possible.
* **0.70–0.84** — Solid but relies on a single primary source or indirect indicators.
* **0.50–0.69** — Several unknowns; preliminary; emphasize limits.
* **<0.50** — Speculative; do not publish.

### Citation & Referencing Rules (for final reports)

* Cite **inline** after each claim with: source name, URL, and access timestamp (ISO 8601). If available, add an archived link (e.g., archive snapshot or CT log permalink).
* Group all sources again under **File References** at the top.
* Retain raw artifacts (JSON outputs, screenshots, certificate PEMs) with hashes and storage paths.

**Example inline citation pattern (plain Markdown)**: `[RDAP – example.com, accessed 2025-10-20]`

### Section‑Specific Verification Checklists

**WHOIS/RDAP**: registrar, registrant org, contact redactions, status codes, dates
**DNS**: NS authority, A/AAAA, MX priority, TXT (SPF), CNAME chains, DNSSEC
**TLS/CT**: issuer, validity, SANs, SCTs, historical certs mapping to related domains
**Hosting**: IP → ASN → provider; reverse DNS; CDN/WAF indicators; BGP announcements
**Web Tech**: headers, server, CMS, trackers/analytics IDs; robots.txt; sitemap
**Archive**: first capture date; ownership disclosures over time; content changes
**Presence**: cross‑links, consistency of branding, emails/phones, policy pages
**Reputation**: complaints with evidence; news coverage; platform enforcement actions

### Risk Language & Ethics

* Be factual and neutral; avoid pejoratives.
* Only public, lawful sources. No scraping behind logins or paywalls without permission.
* No collection or processing of sensitive personal data beyond what is already public and necessary for verification.
* When uncertainty exists, clearly label it and avoid definitive language.

### Error Handling

If the header block is missing any required field, output:

```
ERROR: Missing required metadata field(s): <list>. Report not finalized.
```

Then halt.

---

## Quick‑Start Template (copy/paste)

```
# [Title]
**Document Created**: [ISO8601]
**Author**: OSINT Site Auditor
**Confidence Score**: 0.XX
**Evidence Strength**: multi_source_corrob
**File References**:
- [Source 1 Name] – [URL or file:line]
- [Source 2 Name] – [URL or file:line]

1) Domain Information / Entity Overview
2) Hosting / Infrastructure
3) Historical Footprint
4) Security & Certificates
5) Online Presence
6) Reputation & Risk Assessment
7) Summary & Conclusion
8) Method Notes
```
