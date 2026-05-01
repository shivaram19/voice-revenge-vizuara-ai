# ADR-001: Frontend Architecture for Multi-Tenant Education Voice CRM

**Date:** 2026-05-01
**Scope:** Frontend Architecture, Authentication, Real-time Communication
**Research Phase:** ADR Completion

## Context
The project requires a pivot to a multi-tenant Voice CRM tailored for educational institutions. Schools will use this system to manage AI voice agents that call students/parents. The user interface must be scalable, support multi-tenancy securely, provide a premium "Dynamic Design" aesthetic, and offer real-time observability of active calls.

## Decision
We will adopt the following architectural stack for the Next.js frontend:
1. **Authentication & Multi-tenancy:** Supabase.
2. **Styling & Component Library:** TailwindCSS combined with `shadcn/ui`.
3. **Real-time Updates:** WebSockets (specifically leveraging Supabase Realtime where applicable or custom Next.js WS integration).

## Consequences
**Positive:**
- Supabase provides robust out-of-the-box Row Level Security (RLS), guaranteeing data isolation across school tenants without complex custom backend logic.
- `shadcn/ui` drastically accelerates the development of a highly accessible, premium user interface, meeting the requirement for visual excellence.
- WebSockets eliminate the need for HTTP polling, reducing latency and allowing for instant updates when the AI agent completes a call or encounters an error.

**Negative:**
- `shadcn/ui` and TailwindCSS represent a shift from purely Vanilla CSS, introducing a build step and utility-first paradigm.
- Integrating WebSockets in Next.js serverless environments requires careful architecture (likely relying on a decoupled long-running server or Supabase Realtime limits).

## Alternatives Considered
- **NextAuth.js / Clerk for Auth:** Clerk offers great UI but is expensive at scale. NextAuth.js requires managing our own database adapters and does not enforce RLS natively at the database level like Supabase does.
- **Vanilla CSS:** Maintained maximum flexibility but would require significantly more time to achieve the "wow" factor and premium dynamic interactions compared to leveraging Radix primitives via `shadcn/ui`.
- **HTTP Polling:** Simpler to implement but scales poorly for 1,000,000 concurrent users (a project requirement) and degrades the UX for live call monitoring.

## References
- `DFS-001-education-voice-crm-uiux.md`
- Supabase Architecture Guide: https://supabase.com/docs/guides/architecture
- shadcn/ui Documentation: https://ui.shadcn.com/
