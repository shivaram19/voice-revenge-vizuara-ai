# Lead Generation & Qualification Framework
## Finding Decision-Makers Who Can Scale With AI

> **Scope:** Methodologies, tools, and frameworks for identifying individual decision-makers at construction and logistics companies.  
> **Limitation:** This document provides frameworks and tools — not specific personal data. Real names require ethical prospecting via LinkedIn Sales Navigator, Apollo.io, or industry directories.

---

## Part 1: The Decision-Maker Matrix

### Who Has the Power to Buy?

| Role | Company Size | Budget Authority | Speed to Close | Pain Level |
|------|-------------|------------------|----------------|------------|
| **Owner/Founder** | 1-10 employees | Absolute | 1-7 days | Extreme |
| **VP Operations** | 50-500 employees | High ($50K+) | 14-45 days | High |
| **General Manager** | 20-200 employees | Medium ($10K+) | 7-21 days | High |
| **Office Manager** | 10-50 employees | Low (influencer) | 21-60 days | Medium |
| **IT Director** | 200+ employees | Gatekeeper | 45-90 days | Low |
| **CFO** | 500+ employees | Budget owner | 60-120 days | Low |
| **Procurement Manager** | 1000+ employees | Process owner | 90-180 days | Low |

**Ideal target:** Owner/Founder at 10-50 employee companies.  
**Why:** Absolute budget authority + acute pain + fast decision cycle.

---

## Part 2: The "Ready to Scale" Signal Framework

Not every company is ready. Look for these signals:

### Signal A: Growth Trajectory (Weight: 9/10)

| Indicator | Source | How to Find |
|-----------|--------|-------------|
| Hiring spree (10+ open jobs) | LinkedIn, Indeed | LinkedIn company page → Jobs |
| New facility/warehouse | Local news, permits | City permit databases |
| Revenue growth >30% YoY | Inc 5000, press releases | Inc.com, company blog |
| New contract win (government, retail) | Press releases, SEC filings | PR Newswire, company IR |
| Recent acquisition | M&A databases | PitchBook, Crunchbase |

**Why it matters:** Growing companies have more calls than they can handle. They need scalable solutions, not headcount.

### Signal B: Technology Adoption (Weight: 8/10)

| Indicator | Source | How to Find |
|-----------|--------|-------------|
| Uses modern TMS/WMS | Website, job postings | Look for "SAP", "Oracle", "Blue Yonder" in job ads |
| Active on LinkedIn (posts 2×/week) | LinkedIn | Company page activity |
| Has website with online booking | Google | Search "book appointment [company]" |
| Uses ELD (Samsara, Motive, Geotab) | Fleet signage, job postings | Look for ELD mentions |
| Cloud-first infrastructure | Job postings | "Azure", "AWS", "Google Cloud" in job ads |

**Why it matters:** Tech-adjacent companies adopt AI faster. Non-tech companies need education first.

### Signal C: Pain Indicators (Weight: 10/10)

| Indicator | Source | How to Find |
|-----------|--------|-------------|
| Bad reviews mentioning "never called back" | Google, Yelp | Search reviews for "call", "phone", "response" |
| No after-hours phone number | Website | Check if phone goes to voicemail after 5 PM |
| High employee turnover | Glassdoor, LinkedIn | Glassdoor reviews, LinkedIn tenure |
| Job posting for "receptionist" or "dispatcher" | Indeed, LinkedIn | Search "receptionist" + company name |
| Recent complaint to BBB | BBB.org | Search company on Better Business Bureau |
| Social media complaints | Facebook, Twitter | Search "[@company] never answers" |

**Why it matters:** Pain drives purchase. A company with no pain needs no solution.

### Signal D: Financial Health (Weight: 7/10)

| Indicator | Source | How to Find |
|-----------|--------|-------------|
| Profitable (not burning cash) | Credit reports, Dun & Bradstreet | D&B Hoovers, Creditsafe |
| Paying employees on time | Glassdoor | "Pay" reviews on Glassdoor |
| No recent layoffs | News, LinkedIn | Search "[company] layoff" |
| Investing in equipment | Equipment registries | UCC filings, equipment liens |
| Good credit score | Credit bureaus | Experian Business, Equifax Business |

**Why it matters:** Broke companies can't pay, no matter how much they need it.

---

## Part 3: Sourcing Methodologies

### Method 1: LinkedIn Sales Navigator (Primary)

**Search filters:**
```
Job Titles: "Owner" OR "Founder" OR "VP Operations" OR "General Manager" OR "Fleet Manager" OR "Warehouse Manager"
Company Headcount: 11-200
Industry: "Construction" OR "Transportation/Trucking/Railroad" OR "Warehousing/Storage"
Company Type: Privately Held
Geography: Memphis, TN OR Chicago, IL OR Dallas, TX OR Los Angeles, CA OR Atlanta, GA OR Houston, TX
Posted on LinkedIn in past 90 days: Yes (active users)
```

**Lead list size:** 500-2,000 names per metro area.

**Workflow:**
1. Build search → Save as lead list
2. Export to CSV (via Apollo.io or PhantomBuster)
3. Enrich with Apollo.io for emails/phones
4. Score each lead using the Signal Framework
5. Prioritize top 100

### Method 2: Apollo.io (Primary)

**Search:**
```
Industry: Construction OR Trucking OR Logistics OR Warehousing
Employee Count: 11-200
Job Title: Owner OR CEO OR VP Operations OR General Manager
Location: United States
Technologies: Exclude companies with Smith.ai, Ruby Receptionists, AnswerConnect
```

**Why Apollo:** Has direct emails and phone numbers. LinkedIn only has InMail.

### Method 3: Industry Directories (Secondary)

| Directory | URL | Best For |
|-----------|-----|----------|
| **Dun & Bradstreet** | dnb.com | Financial health, company size |
| **IBISWorld** | ibisworld.com | Industry reports, market sizing |
| **Construction Journal** | constructionjournal.com | Project leads, GC contacts |
| **Dodge Data & Analytics** | construction.com | Construction project data |
| **DAT Load Board** | dat.com | Freight broker directory |
| **Truckstop.com** | truckstop.com | Carrier/broker directory |
| **IWLA** (warehouse assoc) | iwla.com | Warehouse member directory |
| **TIA** (broker assoc) | tianet.org | Freight broker member list |
| **ABC** (builders assoc) | abc.org | Contractor member directory |
| **NAHB** (home builders) | nahb.org | Home builder directory |

### Method 4: Google Maps Scraping (Tertiary)

**Search queries:**
```
"general contractor" near Memphis, TN
"plumbing contractor" near Dallas, TX
"HVAC company" near Atlanta, GA
"freight broker" near Chicago, IL
"3PL warehouse" near Los Angeles, CA
```

**Tool:** Use Apify or Bright Data to scrape:
- Business name
- Phone number
- Website
- Review count and rating
- Recent reviews (for pain signals)

**Output:** 500-2,000 companies per metro. Manually filter for 3+ star with "hard to reach" reviews.

### Method 5: Permit Data (Hidden Gem)

**What:** Construction permits are public record. They show:
- Who is building (active = growing)
- Project value (revenue proxy)
- Contractor name (direct lead)

**Sources:**
- City of Memphis permit portal
- Chicago Building Department
- LA Department of Building and Safety
- Dallas Development Services

**Tool:** BuildZoom, ConstructConnect aggregate permit data.

### Method 6: Conference Attendee Lists (High-Intent)

| Conference | Audience | When |
|------------|----------|------|
| **TIA Capital Ideas** | Freight brokers | October |
| **IWLA Convention** | Warehouse operators | March |
| **Manifest** | Logistics tech | February |
| **ProMat** | Supply chain | March |
| **ABC Convention** | Contractors | March |
| **NAHB IBS** | Home builders | February |
| **TMC Annual Meeting** | Fleet maintenance | February |

**How to get lists:**
- Sponsor the event (get attendee list)
- Exhibit (scan badges)
- Join association (get member directory)
- Post-event: search LinkedIn for "attended [conference]"

---

## Part 4: Lead Scoring Model

Score each lead 0-100. Only pursue 70+.

### Scorecard

| Factor | Points | How to Determine |
|--------|--------|------------------|
| **Company size 11-50** | +20 | LinkedIn, Apollo |
| **Growth signal (hiring/facility/contract)** | +20 | Job postings, permits, news |
| **Tech-adjacent (modern TMS/WMS/ELD)** | +15 | Job postings, website |
| **Pain signal (bad reviews/high turnover)** | +20 | Google, Glassdoor |
| **Financially healthy** | +15 | D&B, Glassdoor pay reviews |
| **Decision-maker is Owner/Founder** | +10 | LinkedIn |
| **Located in Tier 1 logistics hub** | +5 | Geography |
| **Already uses answering service** | -10 | Website, reviews |
| **Company size >500** | -20 | Long sales cycle |
| **Recent layoffs/revenue decline** | -20 | News, Glassdoor |
| **No website/no LinkedIn presence** | -15 | Not tech-ready |

**Scoring tiers:**
- **90-100:** Hot lead. Call today.
- **70-89:** Warm lead. Email this week.
- **50-69:** Cold lead. Nurture with content.
- **<50:** Disqualify. Don't waste time.

---

## Part 5: The Outreach Sequences

### Sequence A: LinkedIn Connection + Message (Owner/Founder)

**Day 1: Connection Request**
> "Hi [Name], I help [industry] companies stop losing revenue to missed calls. Saw [Company]'s work on [project/review]. Impressive growth. Would love to connect."

**Day 3: First Message (if accepted)**
> "[Name], quick question: how many calls does [Company] miss per week while your team is on job sites? We built an AI receptionist that answers 24/7, books appointments, and handles emergencies. One Memphis contractor reduced missed calls 94% in 30 days. Worth a 10-min call?"

**Day 7: Follow-up (if no response)**
> "[Name], no pressure if timing is off. Here's a 90-sec demo of how it sounds: [link]. If missed calls aren't a pain point, I won't follow up again."

**Day 14: Breakup (if no response)**
> "[Name], last note from me. If you ever want to see how AI could handle [Company]'s after-hours calls, I'm here. Otherwise, best of luck with the growth."

### Sequence B: Cold Email (VP Operations / GM)

**Subject:** [Company] + after-hours calls

**Body:**
> Hi [Name],
>
> [Company] has grown to [X] employees — impressive. At this scale, after-hours and weekend calls are probably falling through the cracks.
>
> We deploy AI receptionists for [industry] firms in the [$X-$Y revenue] range. The AI handles nights, weekends, and overflow — with full calendar integration and emergency escalation.
>
> One [similar company] in [city] reduced their answering service cost by 60% while improving customer satisfaction.
>
> 15-minute call next week?
>
> [Your name]

**Follow-up 1 (Day 3):**
> Subject: Re: [Company] + after-hours calls
>
> [Name], bumping this up. I know you're busy. If not interested, just reply "no thanks" and I'll close the loop.

**Follow-up 2 (Day 7):**
> Subject: Last try: [Company] + 24/7 calls
>
> [Name], last note. Here's a 2-min video of the AI handling an emergency dispatch: [link]. If this isn't a priority right now, I get it. No hard feelings.

### Sequence C: Cold Call (Owner/Founder)

**Opening (15 seconds):**
> "[Name], this is [Your name] with [Company]. I'm not selling anything today. I have a 30-second question about missed calls. Do you have 30 seconds?"

**If yes:**
> "Quick question: when you're on a roof or in a crawl space and the phone rings, who answers it?"

**If they say "no one" or "my spouse" or "it goes to voicemail":**
> "That's exactly why I'm calling. We built an AI that answers those calls, books the appointment, and sends you a text summary. You focus on the work. The AI handles the phone. Worth 10 minutes to see how it sounds?"

**If they say "not interested":**
> "Fair enough. Can I ask what you do for after-hours calls? Just curious — we're always learning."

**If they give an objection:**
> "Totally understand. Most contractors say the same thing until they see the numbers. One of our customers was missing 12 calls a week. At $2,500 per job, that's $30K in lost revenue. The AI costs $299/month. Can I send you a 2-minute video? No commitment."

---

## Part 6: The "Dream 100" List Building Exercise

### Step 1: Pick Your First City

Start with ONE city. Master it before expanding.

**Recommended starter cities (highest density + lowest competition):**
1. **Memphis, TN** — logistics gravity, lower cost, less tech competition
2. **Indianapolis, IN** — distribution hub, e-commerce growth
3. **Columbus, OH** — retail DCs, central location
4. **Nashville, TN** — healthcare logistics, rapid growth

### Step 2: Build the List

**Target:** 100 companies in your city that fit the profile.

**Sources:**
- Apollo.io: 40 leads
- LinkedIn Sales Navigator: 30 leads
- Google Maps scraping: 20 leads
- Industry association directories: 10 leads

### Step 3: Enrich Each Lead

For each of the 100, gather:
- [ ] Company name
- [ ] Website
- [ ] Decision-maker name
- [ ] Decision-maker title
- [ ] Decision-maker LinkedIn URL
- [ ] Decision-maker email (Apollo.io)
- [ ] Decision-maker phone (Apollo.io or company line)
- [ ] Employee count
- [ ] Annual revenue (estimate)
- [ ] Growth signals (hiring, permits, news)
- [ ] Pain signals (reviews, turnover)
- [ ] Tech stack (TMS, WMS, ELD)
- [ ] Current phone setup (voicemail, answering service, spouse)
- [ ] Score (0-100)

### Step 4: Prioritize and Attack

**Week 1:** Top 20 scores → Phone calls + LinkedIn connections  
**Week 2:** Scores 21-40 → Emails + LinkedIn messages  
**Week 3:** Scores 41-60 → Content nurture (send blog posts, case studies)  
**Week 4:** Scores 61-100 → Add to retargeting audience, revisit in 30 days

### Step 5: Track and Iterate

**CRM fields to track:**
- Date of first contact
- Channel (phone, email, LinkedIn)
- Response (yes, no, maybe, no response)
- Objection (if any)
- Demo scheduled (yes/no, date)
- Trial started (yes/no, date)
- Closed (yes/no, date, value)

**Weekly metrics:**
- Leads contacted
- Responses received
- Demos scheduled
- Trials started
- Deals closed
- Revenue

---

## Part 7: Tools Stack

| Purpose | Tool | Cost | Why |
|---------|------|------|-----|
| **Lead finding** | Apollo.io | $59/mo | Best email/phone data for SMB |
| **LinkedIn prospecting** | LinkedIn Sales Navigator | $99/mo | Advanced search, InMail |
| **CRM** | HubSpot Free | $0 | Track pipeline, emails, calls |
| **Email sequences** | Apollo.io or HubSpot | Included | Automated follow-ups |
| **Phone dialing** | Aircall or JustCall | $30/mo | Track calls, record demos |
| **Data enrichment** | Clearbit or ZoomInfo | $$$ | Firmographic data |
| **Review monitoring** | Google Alerts | $0 | Track company mentions |
| **Permit data** | BuildZoom | Freemium | Construction project leads |
| **Scraping** | Apify | $49/mo | Google Maps, directories |
| **Email verification** | Hunter.io | $49/mo | Verify emails before sending |

**Total starter stack:** ~$300/month

---

## Part 8: The Ethics Boundary

### What We Do
- Use publicly available business directories
- Respect opt-outs and unsubscribe requests
- Provide genuine value in every interaction
- Be transparent about AI capabilities and limitations

### What We Don't Do
- Scrape private social media profiles
- Buy lists of personal phone numbers
- Spam or harass prospects
- Misrepresent the product
- Target companies that explicitly opt out

---

## References

- [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch.
- [^41]: Twilio. (2024). REST API: Making Calls.
- [^44]: Microsoft. (2024). Azure Well-Architected Framework.
