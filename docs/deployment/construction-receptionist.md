# Construction Industry AI Receptionist

**Version**: 1.0  
**Date**: 2026-04-25  
**Niche**: Construction & Building Trades

---

## Domain Specialization

This receptionist is configured for a **construction/building trades company** handling:
- Inbound calls from homeowners, property managers, and builders
- Emergency repair dispatch (plumbing, electrical, HVAC, roofing)
- Appointment scheduling for estimates and site visits
- Outbound calls to subcontractors and suppliers
- Permit and inspection coordination

## Trade Coverage

| Trade | Emergency | Estimates | Scheduled Work |
|-------|-----------|-----------|----------------|
| General Contracting | No | Yes | Renovations, additions, new builds |
| Electrical | Yes (sparking, outage) | Yes | Panel upgrades, EV chargers, lighting |
| Plumbing | Yes (burst pipe, leak) | Yes | Repiping, water heaters, fixtures |
| HVAC | Yes (no heat/AC) | Yes | Furnace, AC, mini-splits, ductwork |
| Roofing | Yes (storm damage) | Yes | Repairs, replacement, gutters |
| Framing & Carpentry | No | Yes | Walls, trim, built-ins, decks |
| Concrete & Masonry | No | Yes | Foundations, driveways, patios |
| Drywall & Painting | No | Yes | Hanging, finishing, paint |
| Flooring & Tile | No | Yes | Hardwood, tile, vinyl |
| Permits & Inspections | No | Yes | Applications, code compliance |

## Emergency Triage Logic

The receptionist uses a priority-based routing system:

**Level 1 — Immediate Dispatch (same day)**
- Burst pipe / flooding
- Electrical sparking / fire risk
- Roof leak with active water intrusion
- No heat during freezing temperatures

**Level 2 — Same/Next Day**
- Non-urgent plumbing leak
- Partial power loss
- HVAC not cooling (mild weather)
- Storm damage with temporary protection

**Level 3 — Scheduled Appointment**
- Estimates and consultations
- Routine maintenance
- Punch list items
- Warranty callbacks

## Call Flows

### Homeowner Emergency
```
Caller: "I have water pouring through my ceiling!"
Agent:  "This is an emergency. I'm dispatching a plumber now. 
         Can you shut off the main water valve? It's usually 
         in the basement near the front wall."
Agent:  [queues outbound call to on-call plumber]
Agent:  "James O'Brien is en route. ETA 25 minutes. 
         After-hours rate applies: 150 dollars per hour."
```

### Estimate Request
```
Caller: "I want a quote for a kitchen renovation."
Agent:  "I'd be happy to schedule a free estimate. 
         Mike Ross handles renovations. He has availability 
         Tuesday at 10 AM or Wednesday at 2 PM."
Caller: "Tuesday at 10 works."
Agent:  "Booked. Mike Ross will arrive Tuesday at 10 AM 
         for a kitchen renovation estimate. 
         The estimate takes 45 to 60 minutes. Is that correct?"
```

### Subcontractor Coordination
```
Agent:  [outbound call to electrician]
Agent:  "Hi Sarah, this is BuildPro dispatch. 
         We need to confirm your availability for 
         the panel upgrade at 123 Main Street tomorrow at 8 AM."
Contractor: "I'm available."
Agent:  "Confirmed. Materials will be on site by 7:30 AM. 
         Please check in with the site supervisor on arrival."
```

## FAQ Categories

- **Emergency services**: 24/7 availability, after-hours rates
- **Estimates**: Free for projects over $1,000, 48-hour scheduling
- **Licensing**: License numbers, insurance certificates
- **Timelines**: Typical durations by project type
- **Permits**: Application handling, inspection scheduling
- **Warranty**: 1-year labor, manufacturer material warranties
- **Payment**: 30/40/30 schedule, accepted methods
- **Service area**: County coverage, travel fees

## Data Model

### Contractor
- `specialty`: Trade area (e.g., "Electrical", "Plumbing")
- `daily_limit`: Max appointments per day (varies by trade)
- `timezone`: For scheduling accuracy

### Appointment
- `appointment_type`: `in_person`, `phone`, or `video`
- `notes`: Project details, materials needed, access instructions
- `duration_minutes`: 30-120 minutes depending on trade and scope

### CallTask
- `purpose`: Reason for outbound call (e.g., "Confirm material delivery")
- `scheduled_time`: Optional future scheduling

## Deployment

```bash
# Seed the database with construction data
python src/receptionist/construction_seed.py

# Run the demo
python examples/construction_demo.py

# Start the full service
docker-compose up --build
```

## References
[^56]: National Association of Home Builders. (2024). Cost of Construction Survey.
[^57]: Occupational Safety and Health Administration. (2024). Construction Industry Standards.

[^1]: National Association of Home Builders. (2024). Cost of Construction Survey.
[^2]: Occupational Safety and Health Administration. (2024). Construction Industry Standards.
