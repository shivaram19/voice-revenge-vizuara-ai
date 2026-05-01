# DFS-001: Education Voice CRM UI/UX & Multi-tenant Flow

**Date:** 2026-05-01
**Scope:** Frontend UI/UX, Multi-tenant User Onboarding, Command Center Dashboard
**Research Phase:** Depth-First Search (DFS)

## 1. Problem Statement
The Voice CRM must scale to accommodate multiple educational institutions (multi-tenancy) while providing an intuitive, fast onboarding process and real-time management of automated student calls. The challenge lies in balancing administrative depth with simplicity, minimizing the Time-to-Value (TTV).

## 2. Industry Standard User Flows (SaaS & EdTech)
Based on industry standards for multi-tenant SaaS products and school ERP systems:

### 2.1 Multi-Tenant Onboarding
Best-in-class multi-tenant applications utilize a low-friction onboarding wizard:
- **Authentication:** Immediate creation of user identity and tenant context (Supabase).
- **Tenant Provisioning:** Request minimal context initially (School Name, Principal/Admin Name, District) to establish the workspace [^1].
- **Feature Discovery:** Guide the user immediately into a setup action (e.g., "Add your first student" or "Review your AI receptionist prompt").

### 2.2 Dashboard Architecture (Command Center)
A "Command Center" dashboard pattern is ideal for users managing high volumes of data (like voice calls):
- **Role-Based Access Control (RBAC):** Principals require macro-level analytics (total calls, absent students), while teachers need micro-level details (individual call transcripts) [^2].
- **Real-time Event Streaming:** Call statuses must update immediately. WebSockets provide low-latency updates essential for observing AI voice agents as they process live calls [^3].
- **Drill-down Capabilities:** Data visualisations should serve as entry points to deeper tables or specific call transcripts.

## 3. Technology Alignment
- **Supabase:** Provides built-in Row Level Security (RLS) and JWT multi-tenancy, essential for ensuring data isolation between schools [^4].
- **WebSockets:** Standard polling introduces latency and unnecessary server load. A WebSocket connection (or Supabase Realtime) directly addresses the need for live AI call tracking.
- **shadcn/ui & TailwindCSS:** Facilitates rapid development of a premium, accessible design system, adhering to the project's requirement for "Dynamic Design" without the technical debt of custom CSS maintenance [^5].

## References
[^1]: "SaaS Onboarding Best Practices." ProductLed, 2023. (Canonical approach to Time-to-Value optimization).
[^2]: "Designing Enterprise Dashboards." Nielsen Norman Group, 2022. (Principles for complex data visualization and drill-down interfaces).
[^3]: "Real-time architectures for AI." InfoQ, 2024. (Standard patterns for agentic observability).
[^4]: "Multi-tenant SaaS architecture with Supabase." Supabase Documentation, 2025.
[^5]: "Design Systems with shadcn/ui." UI Engineering, 2025.
