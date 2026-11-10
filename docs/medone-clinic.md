# MedOne Clinic: 4-Day Build Plan

> A clinic website with appointment booking, online (video) consultations and a RAG-based AI assistant.
> **Website languages:** English and Uzbek.
> **Reference site:** [campusly.uz](https://campusly.uz/), a school portfolio project. We reuse its **structure and UX patterns**, adapted to a clinic, with our own brand and design.
> **Timeline:** 4 days, 10–12 hours per day. At this pace most of the code is written with an AI coding assistant while you review and test everything.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Reference Site: Campusly → MedOne](#2-reference-site-campusly--medone)
3. [Website Structure](#3-website-structure)
4. [Build Order](#4-build-order)
5. [Tech Stack](#5-tech-stack)
6. [Design Direction](#6-design-direction)
7. [Folder Structure](#7-folder-structure)
8. [Day 1: Full Website](#8-day-1-full-website)
9. [Day 2: Booking and Payments](#9-day-2-booking-and-payments)
10. [Day 3: Online Consultations and AI Assistant](#10-day-3-online-consultations-and-ai-assistant)
11. [Day 4: Admin Panel, Live Demo and Launch](#11-day-4-admin-panel-live-demo-and-launch)
12. [Core Rules](#12-core-rules)
13. [If You Run Out of Time](#13-if-you-run-out-of-time)
14. [Notes](#14-notes)

---

## 1. Project Overview

**MedOne Clinic** is a clinic website with:

| Part | What it does |
|---|---|
| **Website** | The clinic, departments, doctors, check-ups, prices, health guides and contacts |
| **Booking** | Reserve a time slot for an in-clinic or online visit and pay |
| **Online consultation** | Talk to a doctor over video |
| **AI assistant ("Front Desk")** | Answers questions using the clinic's own data and helps find the right doctor |
| **Patient Portal** | Appointments, prescriptions and results in one place |
| **Admin panel** | Manage everything shown on the website |
| **Live demo** | Try the portal as a patient, doctor or admin, no password needed |

**Users:** patient, doctor, admin.
**Languages:** English, Uzbek.

---

## 2. Reference Site: Campusly → MedOne

### What Campusly is

Campusly is a website for a **fictional private school in Tashkent**, built as a portfolio project. It combines a public school website with a **portal** for students, parents and teachers, and offers a **live demo without a password**.

### What we take from it

| Campusly pattern | Why it works | How MedOne uses it |
|---|---|---|
| Calm, plain-language copy ("A calm, focused school where every student is known") | Builds trust, does not sound like marketing | Same tone for a clinic |
| Hero with a short claim + key numbers | Instant credibility | Doctors, departments, patients per year, founded year |
| Portal showcase with role tabs (Student / Parent) and a phone mockup | Shows the product, not just the building | Patient / Doctor tabs, Web / Mobile switch |
| **"Live demo, no password"** | Visitors (and recruiters) try it in one click | One-click demo as patient, doctor or admin |
| Program cards with schedule and "Ask about schedule" | Concrete, practical information | Department cards with opening days and hours |
| Mock tests: price, date, room, **seats left**, contact person | Creates urgency, very clear | Check-up packages and screening days with **slots left** |
| Free open courses, no sign-up | Gives value before asking for anything | Free health guides and articles |
| 6-step admission process | Removes uncertainty | "Your visit in 6 steps" |
| Enquiry form with "We will call you back within 1 working day" and a hidden spam field | Simple lead capture | "Request a call back" form |
| Facilities list (metro distance, safety, meals, medical room) | Answers practical questions | Equipment, lab, pharmacy, parking, metro, accessibility |
| Team section with a director's quote | Human face of the organisation | Chief physician's quote + doctor cards |
| Footer note: "a portfolio project; the school and its people are fictional" | Honest, avoids confusion | Same note for MedOne |

### What we do **not** take

- Campusly's name, logo, texts, photos, people or colours
- Its green colour palette and fonts (Lora, Plus Jakarta Sans). MedOne keeps its own design system (section 6), so the two sites look clearly different
- School-only features (grades, homework, honour students)

---

## 3. Website Structure

### Navigation

`Departments · Doctors · Check-ups · Prices · Health guides · FAQ` · `EN / UZ` · **Patient Portal** · **Book a visit**

### Home page sections (in order)

| # | Section | Content | Campusly equivalent |
|---|---|---|---|
| 1 | **Hero** | Eyebrow: "Tashkent · Open daily 08:00–20:00". Claim: *"Calm, careful care, and a doctor who knows your name."* Subline: specialists in 8 departments, in-clinic or online, in English and Uzbek. Buttons: **Book a visit**, **Patient Portal**. Small line: *"Live demo: patient, doctor or admin, no password"* | Hero |
| 2 | **Key numbers** | 40 doctors · 8 departments · 25,000 patients a year · founded 2018 | Stats |
| 3 | **News & events** | E.g. "Free blood pressure check day", "New MRI scanner", "Flu vaccination week" with date, place and time | News & Events |
| 4 | **Why MedOne** | 4 pillars: *In-clinic or online visits* · *AI Front Desk that answers from clinic data and never diagnoses* · *Doctors who speak English and Uzbek* · *Clear prices, no surprises* | Why choose |
| 5 | **Facilities** | 1.5T MRI, lab with same-day results, pharmacy, parking, 5 minutes from metro, step-free access, children's waiting area | Facilities |
| 6 | **Patient Portal showcase** | Tabs **Patient / Doctor**; feature cards (book in a minute, reminders, results online, prescriptions, video visits, AI Front Desk); phone mockup; **Web / Mobile** switch | Portal showcase |
| 7 | **Partners** | Insurance companies and laboratories (fictional names) | Partners |
| 8 | **Departments** | Cards: department, short description, opening days and hours, "Book" link | Programs & clubs |
| 9 | **Check-ups & screening days** | Cards: package name, what is included, price in UZS, date and time, place, **slots left**, coordinator contact, "Book" button | Mock tests |
| 10 | **Health guides** | Free articles and short videos, filter by topic (Heart, Children, Women's health, Lifestyle), no sign-up | Open courses |
| 11 | **Our doctors** | Chief physician's quote + doctor ID cards (photo, name, department, languages, years of experience) | Our team |
| 12 | **Care for every age** | Children (0–17) · Adults · 60+ with what each group gets | School stages |
| 13 | **Your visit in 6 steps** | 01 Ask the Front Desk or choose a doctor · 02 Pick a time · 03 Pay online or at the clinic · 04 Get SMS reminders · 05 Visit in clinic or online · 06 See results and prescriptions in the portal | Admission process |
| 14 | **Request a call back** | Form: name, phone (+998), department, preferred time, hidden spam field. *"We call back within 30 minutes during opening hours."* | Admissions enquiry |
| 15 | **FAQ** | Insurance, payment options, children, results timing, what is needed for an online visit, parking | FAQ |
| 16 | **Footer** | Address, nearest metro, phones, hours, socials, portal links (Patient sign in, Doctor sign in, Live demo), *"MedOne Clinic is a portfolio project; the clinic and its people are fictional."* | Footer |

### Other pages

| Page | Content |
|---|---|
| `/departments`, `/departments/[slug]` | List and detail (services, doctors, hours) |
| `/doctors`, `/doctors/[slug]` | List (filter by department and language), profile with free slots |
| `/check-ups`, `/check-ups/[slug]` | Packages and screening days |
| `/prices` | Full price list, printed-menu style, with search |
| `/guides`, `/guides/[slug]` | Health guides |
| `/news`, `/news/[slug]` | News and events |
| `/about` | Story, facilities, leadership |
| `/contact` | Map, address, phones, hours, call-back form |
| `/faq` | All questions |
| `/assistant` | AI Front Desk, full page |
| `/booking` | Booking flow |
| `/portal` | Patient Portal (appointments, prescriptions, results) |
| `/doctor` | Doctor panel |
| `/admin` | Admin panel |
| `/demo` | One-click live demo |

---

## 4. Build Order

```
Day 1               Day 2                  Day 3                       Day 4
FULL WEBSITE   →   BOOKING            →   ONLINE CONSULTATION     →   ADMIN PANEL
(all sections)     + PAYMENTS + SMS        + AI ASSISTANT (RAG)        + LIVE DEMO + LAUNCH
```

- **The website is finished first**, then each feature is added one at a time.
- Until the admin panel exists (days 1–3), data is loaded with a **seed script**.
- At the end of every day: commit, push and leave the project in a working state.

---

## 5. Tech Stack

| Part | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| UI primitives | Radix UI (unstyled, fully custom styling) |
| Internationalization | next-intl (`en`, `uz`) |
| Backend | Node.js, Express, TypeScript |
| Database | MongoDB Atlas |
| Authentication | Phone number + SMS code (Eskiz.uz) |
| Payments | Payme, Click (sandbox mode) |
| Video calls | WebRTC, Socket.io |
| AI | RAG: LLM API + MongoDB Atlas Vector Search |
| Animation | Framer Motion (used sparingly) |
| Deployment | Vercel (website), Render (backend) |

---

## 6. Design Direction

The site must **not look AI-generated or template-made**, and it must look **clearly different from Campusly** even though the structure is similar.

### Concept: "Modern Tashkent Clinic"

A calm, editorial look that mixes **clinical precision** with **subtle Uzbek craft details**. Think of a well-designed printed hospital brochure, not a SaaS landing page.

### What to avoid (the "AI look")

| ❌ Avoid | ✅ Do instead |
|---|---|
| Purple/blue gradients, glowing blobs | Flat, warm background with one strong accent colour |
| Glassmorphism and heavy drop shadows | Thin 1px rules and borders, almost no shadows |
| Everything rounded (`rounded-2xl` everywhere) | Small radius (4–6px), some sharp corners |
| Centred hero + three identical feature cards | Asymmetric editorial grid, large typography, numbered sections |
| Default shadcn/ui look | Custom-styled Radix primitives |
| Emoji and generic icon sets as decoration | A small custom line-icon set and one ornamental pattern |
| Stock photos of smiling doctors with stethoscopes | Calm, documentary-style photos: real rooms, equipment, hands, light |
| "Revolutionizing healthcare with AI ✨" copy | Short, plain, human sentences |
| Floating chat bubble with a robot avatar | AI presented as the clinic's "Front Desk" with footnote-style sources |

### Colour palette

| Token | Hex | Use |
|---|---|---|
| `paper` | `#F5F1E8` | Main background (warm off-white) |
| `ink` | `#14302B` | Text, headers, dark sections |
| `clay` | `#C2553A` | Primary accent: buttons, links, highlights |
| `tile` | `#2C6E8F` | Secondary accent, inspired by Uzbek tile blue (used rarely) |
| `line` | `#D9D2C3` | Borders and dividers |
| `muted` | `#6B6A63` | Secondary text |
| `alert` | `#B3261E` | Emergency messages only |

### Typography

| Role | Font | Notes |
|---|---|---|
| Headings | **Fraunces** (serif) | Large sizes, tight letter-spacing |
| Body and UI | **IBM Plex Sans** | Clear, good Latin support for Uzbek (`o'`, `g'`) |
| Numbers (prices, times, dates, slots left) | **IBM Plex Mono** | Makes prices and time slots feel precise |

### Signature elements

1. **Ornamental line pattern** inspired by Uzbek tilework (girih), used only in the hero corner, dividers and footer
2. **Price list like a printed menu**: name left, price right, dotted leader line, mono prices
3. **Time-slot picker like a departure board**: mono times, taken slots struck through, selected slot filled with `clay`
4. **Doctor cards like ID cards**: portrait, serif name, department, language tags, large "years of experience" number
5. **Numbered sections**: `01 Departments`, `02 Doctors` in small mono labels
6. **"Slots left" counter** on check-up cards in mono, turning `clay` when fewer than 5 remain
7. **AI "Front Desk"**: a side panel from the right with numbered footnote sources `[1] [2]`
8. **Emergency screen**: a full-width `alert` block with a large "Call 103" button

### Layout and interaction rules

- 12-column grid with generous white space; content does not always sit in the centre
- Large headings (48–72px on desktop), short paragraphs
- Animations: gentle fade/slide on scroll and clear hover states only
- Mobile first: tap targets at least 44px, sticky bottom bar with "Book" and "Call"
- Accessibility: WCAG AA contrast, visible focus states, body text at least 17px

---

## 7. Folder Structure

```
medone-clinic/
├── web/                         # Next.js website
│   ├── app/[locale]/
│   │   ├── (site)/              # home, departments, doctors, check-ups, prices, guides, news, about, contact, FAQ
│   │   ├── login/
│   │   ├── demo/                # one-click live demo
│   │   ├── booking/
│   │   ├── portal/              # patient portal
│   │   ├── call/[id]/           # video consultation
│   │   ├── assistant/           # AI Front Desk (full page)
│   │   ├── doctor/              # doctor panel
│   │   └── admin/               # admin panel
│   ├── components/
│   │   ├── ui/                  # base components (Button, Tag, Card...)
│   │   └── site/                # home page sections
│   ├── styles/                  # design tokens, fonts, pattern SVGs
│   ├── messages/                # en.json, uz.json
│   └── lib/
│
├── api/                         # Express backend
│   ├── src/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/            # booking, payment, sms, ai, demo
│   │   ├── middlewares/
│   │   ├── socket.ts
│   │   └── server.ts
│   └── scripts/seed.ts
│
└── README.md
```

---

## 8. Day 1: Full Website

**Goal:** by the end of the day the full public website works in English and Uzbek, with all home page sections and its own design.

### Block 1: Project setup (1 h)
- [ ] Create `web` (Next.js) and `api` (Express)
- [ ] Connect to MongoDB Atlas, `.env` and `.env.example`
- [ ] Tailwind CSS, Radix UI, next-intl (`en`, `uz`)

### Block 2: Design system (1.5 h)
- [ ] Tokens in Tailwind: colours, fonts, radius, spacing
- [ ] Fonts: Fraunces, IBM Plex Sans, IBM Plex Mono
- [ ] Ornamental pattern SVG
- [ ] Base components: Button, Link, Tag, Card, Section heading (with number), Divider, Stat

### Block 3: Data and API (1.5 h)
- [ ] Models: **Department**, **Doctor**, **Service**, **CheckupEvent** (price, date, place, total and taken slots, coordinator), **Guide**, **News**, **Partner**, **FAQ**, **CallbackRequest**, **Settings**
- [ ] Public APIs for all of them, plus `POST /callback-requests` (rate-limited, honeypot check)
- [ ] Seed script with bilingual content: 8 departments, 16 doctors, 40 services, 4 check-ups, 6 guides, 3 news items, 4 partners, 15 FAQs

### Block 4: Layout (1 h)
- [ ] Header with navigation, `EN / UZ`, phone, **Patient Portal**, **Book a visit**
- [ ] Footer with address, metro, hours, socials, portal links, portfolio disclaimer
- [ ] Mobile menu and sticky bottom bar

### Block 5: Home page (3.5 h)
- [ ] Hero, key numbers, news & events
- [ ] Why MedOne, facilities
- [ ] Patient Portal showcase (role tabs, phone mockup, Web / Mobile switch)
- [ ] Partners, departments, check-ups with slots left
- [ ] Health guides (topic filter), our doctors with quote
- [ ] Care for every age, your visit in 6 steps
- [ ] Request a call back form, FAQ

### Block 6: Inner pages (2.5 h)
- [ ] Departments (list + detail), Doctors (list + profile)
- [ ] Check-ups (list + detail), Prices (printed-menu style with search)
- [ ] Guides, News, About, Contact (map), FAQ

### Block 7: Review (0.5 h)
- [ ] Every page on a phone and in both languages
- [ ] Compare against the "What to avoid" table and against Campusly (must look different)

### ✅ Day 1 result
- [ ] All 16 home sections and inner pages work in English and Uzbek
- [ ] Call-back requests are saved
- [ ] The site has its own recognisable style and looks good on mobile

---

## 9. Day 2: Booking and Payments

**Goal:** a patient signs in, books an appointment or a check-up and pays.

### Block 1: Sign-in (2 h)
- [ ] **User** model: phone, name, role (patient, doctor, admin)
- [ ] Send and verify SMS code (Eskiz.uz; in development the code is printed to the console)
- [ ] Sign-in page: phone number → SMS code
- [ ] Role-based access checks

### Block 2: Time slots and booking (3.5 h)
- [ ] **Slot** and **Appointment** models (type: in-clinic or online)
- [ ] Seed: two weeks of free slots for every doctor
- [ ] Free slots on the doctor's page (departure-board style)
- [ ] Booking API: **only one patient per slot**
- [ ] Test: out of 50 simultaneous requests only 1 succeeds

### Block 3: Check-up booking (1 h)
- [ ] Book a seat on a check-up or screening day
- [ ] "Slots left" decreases safely, never below zero (same protection as doctor slots)

### Block 4: Booking page (1.5 h)
- [ ] Step by step: visit type → department → doctor → date and time → confirm
- [ ] Sign in with SMS right there if needed

### Block 5: Payments (2 h)
- [ ] **Payment** model; Payme and Click sandbox; "Pay at the clinic"
- [ ] Protection against **charging twice**
- [ ] Unpaid online bookings release the slot after 10 minutes

### Block 6: SMS and Patient Portal (1.5 h)
- [ ] Confirmation SMS and reminders (1 day and 2 hours before)
- [ ] Patient Portal: "My appointments" (upcoming, past, cancel) and "My check-ups"

### ✅ Day 2 result
- [ ] A patient signs in with SMS, books a doctor or a check-up and pays (sandbox)
- [ ] Two people cannot take the same slot or the last check-up seat (proven by tests)
- [ ] Bookings appear in the Patient Portal

---

## 10. Day 3: Online Consultations and AI Assistant

**Goal:** video consultations work and the AI Front Desk answers using the clinic's data.

### Block 1: Doctor panel (1.5 h)
- [ ] "Today's appointments", set own free slots, "Join call" for online visits

### Block 2: Video consultation (3 h)
- [ ] Socket.io: only this appointment's patient and doctor can join
- [ ] WebRTC video and audio; microphone, camera, end call; "Audio only" mode
- [ ] Test on two devices

### Block 3: Notes, prescriptions and results (1 h)
- [ ] The doctor writes a summary and prescription; the patient sees them in the portal
- [ ] Results (PDF) visible only to their owner

### Block 4: AI data preparation (2 h)
- [ ] Split departments, doctors, services, check-ups, guides, FAQ and "About" into chunks
- [ ] Embed and store them (Atlas Vector Search)
- [ ] Retrieval of the most relevant chunks for a question

### Block 5: AI answering (2.5 h)
- [ ] **Emergency filter** first: "chest pain", "can't breathe" → "Call 103!"
- [ ] Live database tools: free slots, prices, doctors, **check-up slots left**
- [ ] Answers only from retrieved data, with sources
- [ ] Replies in English or Uzbek, matching the patient

### Block 6: Front Desk interface (1 h)
- [ ] Right-side panel on every page + full `/assistant` page
- [ ] Streaming answers, numbered footnote sources, "Book this doctor" button
- [ ] "This is not a diagnosis" notice

### ✅ Day 3 result
- [ ] Patient and doctor talk over video; prescriptions appear in the portal
- [ ] The AI correctly answers about prices, doctors, free slots, check-ups and opening hours
- [ ] In emergencies the AI does not recommend a doctor

---

## 11. Day 4: Admin Panel, Live Demo and Launch

**Goal:** the admin fully manages the site, visitors can try a live demo, and the project is online.

### Block 1: Admin foundation (1 h)
- [ ] Admin sign-in, side navigation, data table, bilingual inputs (EN / UZ tabs), image upload

### Block 2: Content management (3 h)
- [ ] Departments, Doctors (with login account), Services and prices
- [ ] Check-up events (price, date, total slots), Guides, News, Partners, FAQ
- [ ] Settings: address, phones, hours, key numbers, "About" text

### Block 3: Operations (1.5 h)
- [ ] Doctor schedules; all appointments and payments with filters
- [ ] **Call-back requests** inbox (new → called → closed)
- [ ] Simple report: appointments today and this month, revenue, busiest doctors, check-up occupancy

### Block 4: AI sync (0.5 h)
- [ ] Any admin change **updates the AI data automatically**; test by adding a doctor and asking about them

### Block 5: Live demo, no password (1.5 h)
- [ ] `/demo` page with three buttons: **Patient**, **Doctor**, **Admin**
- [ ] Each button signs in to a seeded demo account with sample data
- [ ] Demo accounts cannot send real SMS; payments stay in sandbox
- [ ] Demo data resets every night
- [ ] Hero and footer link to the demo

### Block 6: Testing and security (1 h)
- [ ] A patient cannot see another patient's data or calls
- [ ] Rate limits on SMS codes, AI chat, sign-in and call-back form
- [ ] Test the AI with 40 questions in English and Uzbek

### Block 7: Deployment and README (2.5 h)
- [ ] Backend → Render, website → Vercel, Payme and Click sandbox webhooks
- [ ] Test the live site end to end: website → Front Desk → booking → payment → video → prescription → admin
- [ ] README: what it does, screenshots, live demo link, how to run locally

### ✅ Day 4 result
- [ ] The admin can change everything and changes appear immediately (including in the AI)
- [ ] Anyone can try the portal in one click as patient, doctor or admin
- [ ] The site is live and the README is ready

---

## 12. Core Rules

### Booking and payments
- **Only one patient** per time slot; check-up seats never go below zero
- A patient is **never charged twice**
- Unpaid online bookings release the slot after **10 minutes**

### Security
- A patient sees **only their own** appointments, prescriptions, results and calls
- **Only that patient and that doctor** can join a video call
- **Only admins** can access the admin panel
- Demo accounts are isolated: no real SMS, sandbox payments, nightly reset

### AI assistant
- Answers **only from clinic data**; otherwise "I don't have that information, please call us"
- Every answer shows its **sources**
- **Never gives a diagnosis**
- In emergencies: **"Call 103!"**
- Recommends **only** what the clinic actually has

---

## 13. If You Run Out of Time

Postpone in this order (top first):

1. Partners section and health guides
2. News & events
3. Admin reports
4. SMS reminders (keep the confirmation SMS)
5. Click (keep only Payme)
6. Ornamental pattern and scroll animations (keep colours and fonts)
7. "Audio only" mode

**Never cut:** one patient per slot, double-charge protection, access checks, the AI emergency filter, video consultations, the core of the admin panel, the live demo, deployment.

---

## 14. Notes

- Campusly is used **only as a reference for structure and UX patterns**. MedOne uses its own name, texts, images, colours and fonts.
- Payments run in **Payme and Click sandbox mode**. Real payments require a registered legal entity with a merchant agreement.
- Before launching for a real clinic, check the legal requirements for **personal data and online medical services** with a lawyer.
- The demo uses **fictional data only**. The footer states that MedOne Clinic is a portfolio project and that the clinic and its people are fictional.
