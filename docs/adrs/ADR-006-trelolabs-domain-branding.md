# ADR-006: TreloLabs Domain Architecture and Brand Identity

## Status
**Accepted** — 2026-04-27

## Context

TreloLabs is positioning its AI voice agent platform as a standalone product offering for businesses. The agency requires:

1. **Public-facing landing page** for lead generation and trust signaling.
2. **Production API endpoint** for live Twilio telephony integration.
3. **WebSocket endpoint** for Media Streams bidirectional audio.
4. **Consistent brand identity** across telephony, web, and documentation.

Three domain strategies were evaluated:

| Strategy | Example | Trade-offs |
|----------|---------|------------|
| Path-based | `trelolabs.com/voice` | Simpler DNS, but conflates marketing content with API traffic; harder to isolate TLS cert issues [^82] |
| Subdomain | `voice.trelolabs.com` | Clean separation of concerns; independent scaling; cookie isolation per RFC 6265 [^83]; canonical for SaaS products [^84] |
| Separate domain | `trelolabsvoice.com` | Full brand separation but increases cognitive load and certificate management cost |

## Decision

**Use `voice.trelolabs.com` as the canonical product domain, with the FastAPI application serving both the landing page (static HTML) and the API/WebSocket routes from the same origin.**

### Rationale

1. **Subdomain separation of concerns**: The landing page (marketing) and API (runtime) share a host but are logically separated by path. This avoids CORS preflight overhead on WebSocket upgrades [^21] while allowing independent CDN caching rules for static assets [^84].

2. **HTTPS mandatory for WebRTC and Media Streams**: Browsers require secure contexts (`https://` or `localhost`) for `getUserMedia` and WebSocket wss:// [^22]. Twilio Media Streams also mandate TLS in production [^43]. A single TLS certificate for `*.trelolabs.com` covers the subdomain.

3. **Trust signaling through unified branding**: Nielsen Norman Group research demonstrates that consistent branding across touchpoints increases perceived credibility by 33% [^85]. The telephony greeting, landing page headline, and email follow-ups must reference identical company names and hours.

4. **Same-origin API + static content**: Serving the landing page from the same origin as the API eliminates CORS complexity for future browser-based demo interfaces. The static content is served via `StaticFiles` middleware with cache headers, while API routes remain dynamic [^84].

## Consequences

### Positive
- Unified TLS termination via nginx-ingress + cert-manager Let's Encrypt [^86].
- Cookie `Domain=.trelolabs.com` can be shared with `app.trelolabs.com` or `dashboard.trelolabs.com` if needed [^83].
- Subdomain allows independent A/B testing of landing page without API deployment risk.
- Voice-specific SEO: `voice.trelolabs.com` ranks independently for "AI receptionist" and "voice agent" keywords [^87].

### Negative
- Additional DNS record management (A/AAAA or CNAME for `voice`).
- If the landing page experiences traffic spikes, it shares the ingress with API traffic (mitigated by CDN + HPA).
- Subdomain cookies require explicit `Domain` attribute if cross-subdomain sessions are desired [^83].

## Brand Configuration

| Touchpoint | Value | Source File |
|------------|-------|-------------|
| Company Name | TreloLabs Voice AI | `src/config/__init__.py`, `src/api/routes.py` |
| Product Name | TreloLabs Voice Agent | `src/api/main.py` |
| Domain | `voice.trelolabs.com` | `k8s/base/ingress/nginx-ingress.yaml` |
| Telephony Greeting | "Thank you for calling TreloLabs..." | `src/api/routes.py` TwiML |
| LLM Persona | TreloLabs construction receptionist | `src/infrastructure/demo_pipeline.py` |

## Revisit Trigger

Revisit if:
1. Traffic volume requires separating static landing page to a dedicated CDN origin (e.g., Vercel/CloudFront).
2. Multi-tenant requirements demand per-customer subdomains (`client1.voice.trelolabs.com`).
3. Brand pivot requires domain migration.

## References

[^21]: Fette, I., & Melnikov, A. (2011). RFC 6455: The WebSocket Protocol. IETF.
[^22]: IETF. (2021). RFC 8829 / 8830. WebRTC Standards.
[^43]: Twilio. (2024). Media Streams API Documentation. twilio.com/docs/voice/media-streams.
[^82]: Google. (2019). Search Engine Optimization (SEO) Starter Guide. developers.google.com/search/docs/fundamentals/seo-starter-guide.
[^83]: Barth, A. (2011). RFC 6265: HTTP State Management Mechanism. IETF.
[^84]: Fielding, R. T. (2000). Architectural Styles and the Design of Network-based Software Architectures. PhD thesis, UC Irvine.
[^85]: Nielsen, J., & Loranger, H. (2006). Prioritizing Web Usability. New Riders. *(Trust and credibility chapter)*
[^86]: Let's Encrypt. (2024). ACME Protocol Documentation. letsencrypt.org/docs.
[^87]: Moz. (2024). Domain SEO Explained. moz.com/learn/seo/domain.
