# MedOne Clinic: 4-Day Build Plan

> A clinic website with appointment booking, online (video) consultations and a RAG-based AI assistant.
> **Website languages:** English and Uzbek.
> **Timeline:** 4 days, 10–12 hours per day. At this pace most of the code is written with an AI coding assistant while you review and test everything.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Build Order](#2-build-order)
3. [Tech Stack](#3-tech-stack)
4. [Design Direction](#4-design-direction)
5. [Folder Structure](#5-folder-structure)
6. [Day 1: Full Website](#6-day-1-full-website)
7. [Day 2: Booking and Payments](#7-day-2-booking-and-payments)
8. [Day 3: Online Consultations and AI Assistant](#8-day-3-online-consultations-and-ai-assistant)
9. [Day 4: Admin Panel and Launch](#9-day-4-admin-panel-and-launch)
10. [Core Rules](#10-core-rules)
11. [If You Run Out of Time](#11-if-you-run-out-of-time)
12. [Notes](#12-notes)

---

## 1. Project Overview

**MedOne Clinic** is a clinic website with:

| Part | What it does |
|---|---|
| **Website** | Information about the clinic, departments, doctors, prices and contacts |
| **Booking** | Reserve a time slot for an in-clinic or online visit and pay |
| **Online consultation** | Talk to a doctor over video |
| **AI assistant** | Answers questions using the clinic's own data and helps find the right doctor |
| **Admin panel** | Manage everything shown on the website |

**Users:** patient, doctor, admin.
**Languages:** English, Uzbek.

---

## 2. Build Order

```
Day 1               Day 2                  Day 3                       Day 4
FULL WEBSITE   →   BOOKING            →   ONLINE CONSULTATION     →   ADMIN PANEL
(all pages)        + PAYMENTS + SMS        + AI ASSISTANT (RAG)        + DEPLOY + TESTING
```

- **The website is finished first**, then each feature is added one at a time.
- Until the admin panel exists (days 1–3), data is loaded with a **seed script**.
- At the end of every day: commit, push and leave the project in a working state.

---

## 3. Tech Stack

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

## 4. Design Direction

The goal: the site must **not look AI-generated or template-made**. It should feel like it was designed by a studio for one specific clinic in Tashkent.

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
| `ink` | `#14302B` | Text, headers, dark sections (deep green-black) |
| `clay` | `#C2553A` | Primary accent: buttons, links, highlights |
| `tile` | `#2C6E8F` | Secondary accent, inspired by Uzbek tile blue (used rarely) |
| `line` | `#D9D2C3` | Borders and dividers |
| `muted` | `#6B6A63` | Secondary text |
| `alert` | `#B3261E` | Emergency messages only |

### Typography

| Role | Font | Notes |
|---|---|---|
| Headings | **Fraunces** (serif) | Large sizes, tight letter-spacing, gives an editorial feel |
| Body and UI | **IBM Plex Sans** | Clear, slightly technical, good Latin support for Uzbek (`o'`, `g'`) |
| Numbers (prices, times, dates) | **IBM Plex Mono** | Makes prices and time slots feel precise |

### Signature elements

These details make the site recognisable:

1. **Ornamental line pattern.** A thin geometric pattern inspired by Uzbek tilework (girih), used only in a few places: hero corner, section dividers, footer.
2. **Price list like a printed menu.** Service name on the left, price on the right, joined by a dotted leader line, prices in mono font.
3. **Time-slot picker like a departure board.** A clean grid of times in mono font. Taken slots are struck through, the selected slot is filled with `clay`.
4. **Doctor cards like ID cards.** Portrait photo, name in serif, department, languages spoken as small tags, years of experience as a large number.
5. **Numbered sections.** `01 Departments`, `02 Doctors`, `03 Prices` in small mono labels above each section heading.
6. **AI "Front Desk".** A side panel that opens from the right. Answers show sources as numbered footnotes `[1] [2]`, like a document.
7. **Emergency screen.** A full-width `alert` block with a large "Call 103" button. Nothing decorative.

### Layout and interaction rules

- 12-column grid with generous white space; content does not always sit in the centre
- Large headings (48–72px on desktop), short paragraphs
- Animations: only gentle fade/slide on scroll and clear hover states; no bouncing, no parallax
- Mobile first: tap targets at least 44px, a sticky bottom bar with "Book" and "Call"
- Accessibility: WCAG AA contrast, visible focus states, readable text for older patients (body text at least 17px)

### Design steps

1. Collect a small moodboard (editorial websites, museum sites, printed brochures, Uzbek tile patterns)
2. Define the tokens above in `tailwind.config` (colours, fonts, radius, spacing)
3. Build the base components first: Button, Link, Tag, Card, Section heading, Divider with pattern
4. Only then build the pages

---

## 5. Folder Structure

```
medone-clinic/
├── web/                         # Next.js website
│   ├── app/[locale]/
│   │   ├── (site)/              # home, departments, doctors, prices, about, contact, FAQ
│   │   ├── login/
│   │   ├── booking/             # appointment booking
│   │   ├── cabinet/             # patient account
│   │   ├── call/[id]/           # video consultation
│   │   ├── assistant/           # AI assistant (full page)
│   │   ├── doctor/              # doctor panel
│   │   └── admin/               # admin panel
│   ├── components/
│   │   ├── ui/                  # base components (Button, Tag, Card...)
│   │   └── site/                # page sections
│   ├── styles/                  # design tokens, fonts, pattern SVGs
│   ├── messages/                # en.json, uz.json
│   └── lib/
│
├── api/                         # Express backend
│   ├── src/
│   │   ├── models/              # data models
│   │   ├── routes/              # API routes
│   │   ├── services/            # business logic (booking, payment, sms, ai)
│   │   ├── middlewares/         # auth, roles, validation, errors
│   │   ├── socket.ts            # video call signalling
│   │   └── server.ts
│   └── scripts/seed.ts          # initial data
│
└── README.md
```

---

## 6. Day 1: Full Website

**Goal:** by the end of the day the clinic website works fully in English and Uzbek, with its own distinctive design.

### Block 1: Project setup (1.5 h)
- [ ] Create `web` (Next.js) and `api` (Express) folders
- [ ] Connect to MongoDB Atlas
- [ ] `.env` and `.env.example`
- [ ] Tailwind CSS and Radix UI
- [ ] Set up English and Uzbek (next-intl)

### Block 2: Design system (2 h)
- [ ] Design tokens in Tailwind: colours, fonts, radius, spacing
- [ ] Load fonts: Fraunces, IBM Plex Sans, IBM Plex Mono
- [ ] Draw the ornamental line pattern as an SVG
- [ ] Base components: Button, Link, Tag, Card, Section heading (with number label), Divider

### Block 3: Data and API (1.5 h)
- [ ] Models: **Department**, **Doctor**, **Service**, **Settings** (address, phone, opening hours), **FAQ**
- [ ] Public APIs: departments, doctors, services, settings, FAQ
- [ ] Seed script: 8 departments, 16 doctors, 40 services, 15 FAQs (in English and Uzbek)

### Block 4: Layout (1 h)
- [ ] **Header:** logo, menu, language switch (EN / UZ), phone, "Book a visit" button
- [ ] **Footer:** address, phone, opening hours, social links, pattern strip
- [ ] Mobile menu and sticky bottom bar ("Book" and "Call")

### Block 5: Pages (4.5 h)
- [ ] **Home:** editorial hero, "Book a visit" and "Ask the Front Desk" buttons, departments, doctors, key numbers, patient reviews
- [ ] **Departments:** list and a page for each department
- [ ] **Doctors:** list (filter by department and language) and a profile page for each doctor (ID-card style)
- [ ] **Services and prices:** printed-menu style list grouped by department, with search
- [ ] **About**
- [ ] **Contact:** map, address, phone, opening hours
- [ ] **FAQ**

### Block 6: Review (0.5 h)
- [ ] Check every page on a phone
- [ ] Check every page in both languages
- [ ] Compare against the "What to avoid" table

### ✅ Day 1 result
- [ ] All pages work in English and Uzbek
- [ ] Data comes from the database
- [ ] The site has its own recognisable style and looks good on mobile

---

## 7. Day 2: Booking and Payments

**Goal:** a patient signs in, books an appointment and pays.

### Block 1: Sign-in (2 h)
- [ ] **User** model: phone, name, role (patient, doctor, admin)
- [ ] Send and verify SMS code (Eskiz.uz; in development the code is printed to the console)
- [ ] Sign-in page: phone number → SMS code
- [ ] Role-based access checks

### Block 2: Time slots and booking (3.5 h)
- [ ] **Slot** model: doctor, date, start and end time, status
- [ ] **Appointment** model: patient, doctor, slot, type (in-clinic or online), status
- [ ] Seed: two weeks of free slots for every doctor
- [ ] Show free slots on the doctor's page (departure-board style)
- [ ] Booking API: **only one patient per slot**
- [ ] Test for this rule: out of 50 simultaneous requests only 1 succeeds

### Block 3: Booking page (2 h)
- [ ] Step by step: visit type → department → doctor → date and time → confirm
- [ ] If the patient is not signed in, sign in right there with SMS

### Block 4: Payments (2.5 h)
- [ ] **Payment** model
- [ ] Payme and Click sandbox
- [ ] "Pay at the clinic" option
- [ ] Protection against **charging twice**
- [ ] If online payment is not completed within 10 minutes, the slot opens again

### Block 5: SMS and patient account (1.5 h)
- [ ] Confirmation SMS and reminders (1 day and 2 hours before)
- [ ] Patient account: "My appointments" (upcoming, past, cancel)

### ✅ Day 2 result
- [ ] A patient signs in with SMS, books and pays (sandbox)
- [ ] Two people cannot book the same slot (proven by a test)
- [ ] The appointment appears in the patient account

---

## 8. Day 3: Online Consultations and AI Assistant

**Goal:** video consultations work and the AI assistant answers using the clinic's data.

### Block 1: Doctor panel (1.5 h)
- [ ] "Today's appointments" list
- [ ] Set own available time slots
- [ ] "Join call" button for online appointments

### Block 2: Video consultation (3 h)
- [ ] Socket.io server: only this appointment's patient and doctor can join
- [ ] Video and audio over WebRTC
- [ ] Controls: microphone, camera, end call
- [ ] "Audio only" mode for slow connections
- [ ] Test on two different devices

### Block 3: Notes and prescriptions (1 h)
- [ ] The doctor writes a summary and prescription after the visit
- [ ] The patient sees them in their account

### Block 4: AI assistant: preparing the data (2 h)
- [ ] Split departments, doctors, services, FAQ and "About" texts into small chunks
- [ ] Turn the chunks into vectors and store them (Atlas Vector Search)
- [ ] Search that finds the chunks most relevant to a question

### Block 5: AI assistant: answering (2.5 h)
- [ ] **Emergency filter:** for phrases like "chest pain" or "can't breathe", show "Call 103!" immediately
- [ ] The AI pulls live data from the database: free slots, prices, doctors
- [ ] The AI answers only from the retrieved data and shows its sources
- [ ] The AI replies in the language the patient writes in (English or Uzbek)

### Block 6: AI "Front Desk" interface (1 h)
- [ ] Side panel that opens from the right on every page, plus a full `/assistant` page
- [ ] Answers stream in word by word
- [ ] Sources as numbered footnotes, and a "Book this doctor" button under relevant answers
- [ ] "This is not a diagnosis" notice

### ✅ Day 3 result
- [ ] Patient and doctor talk over video
- [ ] The patient sees the prescription in their account
- [ ] The AI correctly answers questions about prices, doctors, free slots and opening hours
- [ ] In emergencies the AI does not recommend a doctor

---

## 9. Day 4: Admin Panel and Launch

**Goal:** the admin fully manages the website, and the project is live.

### Block 1: Admin panel foundation (1.5 h)
- [ ] Admin sign-in and protected pages
- [ ] Side navigation, data table component (search and pagination)
- [ ] Bilingual text input (separate tabs for English and Uzbek)
- [ ] Image upload
- [ ] Same design system as the website, in a denser, quieter layout

### Block 2: Content management (3 h)
- [ ] **Departments:** create, edit, delete
- [ ] **Doctors:** create, edit, delete (with a login account)
- [ ] **Services and prices**
- [ ] **FAQ**
- [ ] **Settings:** address, phone, opening hours, "About" text

### Block 3: Appointments and reports (1.5 h)
- [ ] Manage doctor schedules
- [ ] All appointments and payments (with filters)
- [ ] Simple report: appointments today and this month, revenue, busiest doctors

### Block 4: Connecting the AI to the admin panel (1 h)
- [ ] When the admin changes anything, the AI data **updates automatically**
- [ ] Test: add a new doctor, then ask the AI about them

### Block 5: Testing and security (1.5 h)
- [ ] A patient cannot see another patient's appointments, prescriptions or calls
- [ ] Rate limits on SMS codes, AI chat and sign-in
- [ ] Test the AI with 40 questions in English and Uzbek

### Block 6: Deployment (2 h)
- [ ] Backend → Render, website → Vercel
- [ ] Payme and Click sandbox webhook URLs
- [ ] Demo accounts: patient, doctor, admin
- [ ] Test the live site end to end:
  website → AI assistant → booking → payment → video consultation → prescription

### Block 7: README (1 h)
- [ ] What the project does, screenshots
- [ ] How to run it locally
- [ ] Demo link and demo accounts

### ✅ Day 4 result
- [ ] The admin can change everything on the site and changes appear immediately
- [ ] The AI knows about new data automatically
- [ ] The site is live
- [ ] README is ready

---

## 10. Core Rules

### Booking and payments
- **Only one patient** per time slot
- A patient is **never charged twice**
- If online payment is not completed within 10 minutes, the slot **opens again**

### Security
- A patient sees **only their own** appointments, prescriptions and calls
- **Only that patient and that doctor** can join a video call
- **Only admins** can access the admin panel

### AI assistant
- Answers **only from clinic data**; if the answer is not there, it says "I don't have that information, please call us"
- Every answer shows its **sources**
- **Never gives a diagnosis**
- In emergencies: **"Call 103!"**
- Recommends **only** departments, doctors and services the clinic actually has

---

## 11. If You Run Out of Time

These can be postponed (top first):

1. Admin reports
2. SMS reminders (keep the confirmation SMS)
3. Click (keep only Payme)
4. Ornamental pattern and scroll animations (keep the colours and fonts)
5. "Audio only" mode

**Never cut:** one patient per slot, double-charge protection, access checks, the AI emergency filter, video consultations, the core of the admin panel, deployment.

---

## 12. Notes

- Payments run in **Payme and Click sandbox mode**. Accepting real payments requires the clinic to be a registered legal entity with a merchant agreement.
- Before launching for a real clinic, check the legal requirements for **personal data and online medical services** with a lawyer.
- The demo uses **fictional data only**, never real patient data.
- The name, logo, photos and texts are original; no other clinic's branding is used.
