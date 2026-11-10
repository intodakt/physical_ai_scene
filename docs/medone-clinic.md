# MedOne Clinic: 4-Day Build Plan

> A clinic website with appointment booking, online (video) consultations, a RAG-based AI assistant and role-based portals.
> **Design:** follows the look and structure of [campusly.uz](https://campusly.uz/) (a school portfolio project), adapted to a clinic.
> **Website languages:** English and Uzbek.
> **Timeline:** 4 days, 10–12 hours per day. At this pace most of the code is written with an AI coding assistant while you review and test everything.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Campusly → MedOne: Full Mapping](#2-campusly--medone-full-mapping)
3. [Design System](#3-design-system)
4. [Public Website](#4-public-website)
5. [Sign-in Pages](#5-sign-in-pages)
6. [Portals](#6-portals)
7. [Admin Panel](#7-admin-panel)
8. [Tech Stack](#8-tech-stack)
9. [Folder Structure](#9-folder-structure)
10. [Build Order](#10-build-order)
11. [Day 1: Design System and Public Website](#11-day-1-design-system-and-public-website)
12. [Day 2: Sign-in, Booking, Payments, Patient Portal](#12-day-2-sign-in-booking-payments-patient-portal)
13. [Day 3: Doctor Portal, Video Visits, AI Front Desk](#13-day-3-doctor-portal-video-visits-ai-front-desk)
14. [Day 4: Admin Panel, Live Demo, Launch](#14-day-4-admin-panel-live-demo-launch)
15. [Core Rules](#15-core-rules)
16. [If You Run Out of Time](#16-if-you-run-out-of-time)
17. [Notes](#17-notes)

---

## 1. Project Overview

| Part | What it does |
|---|---|
| **Public website** | Clinic, departments, check-ups, health guides, doctors, how a visit works, FAQ |
| **Booking** | In-clinic or online visit, time slot, payment |
| **Patient Portal** | Visits, results, prescriptions, AI Front Desk, notices |
| **Doctor Portal** | Today's queue, schedule, video visits, notes and prescriptions, patient questions |
| **Admin panel** | Manage all content, requests, users, appointments and payments |
| **Video visits** | Doctor and patient talk over video |
| **AI Front Desk** | Answers from clinic data (RAG), helps find the right doctor |
| **Live demo** | One click, no password: patient, doctor or admin; resets every night |

**Roles:** patient, doctor, admin.
**Languages:** English, Uzbek.

---

## 2. Campusly → MedOne: Full Mapping

### Public website

| Campusly | MedOne Clinic |
|---|---|
| Hero: "A calm, focused school where every student is known." | Hero: "A calm, careful clinic where every patient is known." |
| Eyebrow pill "Tashkent · Grades 1–11" | "Tashkent · Open daily 08:00–20:00" |
| Buttons "Enquire now" / "Campusly Portal →" | "Book a visit" / "Patient Portal →" |
| "Live demo: student, parent or teacher — no password" | "Live demo: patient, doctor or admin — no password" |
| Stats: students · teachers · programs · founded | doctors · departments · patients a year · founded |
| News & Events carousel | News & Events (free check-up day, new MRI, vaccination week) |
| Why choose Campusly (4 cards) | Why choose MedOne (4 cards) |
| Facilities (icon list around a student portrait) | Facilities (icon list around a doctor portrait) |
| Campusly Portal showcase (Student / Parent tabs, device mockups) | Patient Portal showcase (Patient / Doctor tabs, device mockups) |
| Partners marquee (CollegeBoard, British Council…) | Partners marquee (insurance companies and labs, fictional names) |
| Programs & clubs (photo cards with schedule) | Departments (photo cards with days and hours) |
| Mock tests (seats left, price, date, room, contact) | Check-ups & screening days (slots left, price, date, place, coordinator) |
| Open Courses (free, filter chips) | Health guides (free, filter chips) |
| Honor Students (gold badge cards) | Recognition (doctors' awards and certifications) |
| Our team (director quote + photo grid) | Our doctors (chief physician quote + photo grid) |
| School stages (Primary / Middle / High) | Care for every age (Children / Adults / 60+) |
| Admission process (6 steps, zig-zag timeline) | Your visit in 6 steps (same timeline) |
| Admissions office form | Patient desk: "Request a call back" form |
| FAQ accordion | FAQ accordion |
| Footer (address, metro, socials, portals, disclaimer) | Same structure, MedOne content |

### Sign-in and portals

| Campusly | MedOne Clinic |
|---|---|
| `/login` Student / Parent tabs + Live demo box | `/login` Patient sign-in (phone + SMS) + Live demo box |
| `/login/teacher` | `/login/staff` (doctors and admins) |
| Student portal: Home, My Courses, Calendar, Grades, AI Study Tutor, Announcements | Patient Portal: Home, My Visits, Calendar, Results, Prescriptions, AI Front Desk, Notices |
| Parent portal: child switcher, Overview, Grades, Attendance, Calendar, Announcements | Family members: switch between your own profile and your children's profiles |
| Teacher portal: Dashboard, My Courses, Gradebook, Attendance, Announcements, Q&A | Doctor Portal: Dashboard, Schedule, Visits, Patients, Notices, Patient Q&A |
| `/_admin`: activity, enquiries, programs, mock tests, news, open courses, honor students, team, users, settings, records | `/admin`: activity, call-back requests, departments, check-ups, news, health guides, recognition, doctors, users, settings, appointments & payments |

### What stays original

MedOne uses the same **visual style and layout patterns**, but its **own name, logo, texts, photos and people**. No images, logos or text are copied from Campusly.

---

## 3. Design System

All values below were measured from campusly.uz.

### Colours

| Token | Hex | Use |
|---|---|---|
| `bg` | `#F8F8F6` | Page background |
| `surface` | `#FFFFFF` | Cards, header after scroll |
| `text` | `#242A27` | Body text |
| `heading` | `#111827` | Headings |
| `primary` | `#2F7A63` | Links, eyebrow labels, stat numbers, accents |
| `primary-dark` | `#1F4E43` | Main buttons, active sidebar item, login panel |
| `primary-deeper` | `#163830` | Pressed states, dark sections |
| `primary-light` | `#4FA383` | Icons, success dots |
| `primary-tint` | `#E5F1EB` | Soft tags ("Covered by insurance"), contact box, live-demo bar |
| `surface-alt` | `#F3F5F2` | Table headers, input backgrounds |
| `border` | `#E7E5E4` | Card and input borders |
| `muted` | `#78716C` | Secondary text |
| `muted-dark` | `#57534E` | Labels |
| `gold` | `#D4A017` | Recognition badge |
| `amber-tint` | `#FEF3C7` (approx.) | "Slots left" pill, "Not taken" style warnings |

**Icon tiles** (square, radius 8–10px, white icon, gradient at 145°, soft coloured shadow):

| Name | Gradient |
|---|---|
| blue | `#4A7FE6 → #1E56C8` |
| violet | `#8466E6 → #5B3FCF` |
| sky | `#2290C8 → #0B6FA8` |
| orange | `#D9722A → #A94C08` |
| teal | `#1A9890 → #0F766E` |
| green | `#4FA383 → #2F7A63` |
| rose | `#E35A7A → #C2304F` |

Shadow: `0 8px 16px -8px <colour at 55%>, inset 0 1px 0 rgba(255,255,255,0.25)`.

### Typography

| Role | Font | Notes |
|---|---|---|
| Headings and body | **Plus Jakarta Sans** | Headings 600–800, letter-spacing `-0.025em` |
| Logo wordmark, quotes | **Lora** 500 | Uppercase wordmark with wide letter-spacing |
| Numbers, IDs, codes | **JetBrains Mono** 500/600 | Plus `font-variant-numeric: tabular-nums` on the body |

| Element | Size |
|---|---|
| Hero heading | 54px desktop / 40px mobile, bold, tight line-height |
| Section heading (H2) | 30–36px (`1.875rem`–`2.25rem`) |
| Card title | 18–20px |
| Body | 15px (`0.9375rem`), line-height 24px |
| Small text | 13–14px |
| Eyebrow label | 12px, uppercase, letter-spacing `0.1em`, `primary` colour |

### Shape, depth, layout

| Token | Value |
|---|---|
| Radius | 8px (buttons, inputs), 12px (cards), 16px (large cards), pill `9999px` (tags, segmented controls) |
| Card border | `1px solid #E7E5E4` |
| Shadow small | `0 1px 2px rgba(0,0,0,0.05)` |
| Shadow card | `0 4px 12px -2px rgba(36,42,39,0.08)` |
| Container | max width `1152px`, side padding 16 / 32 / 48px |
| Header | fixed, 76px tall |

### Motion

| Effect | Value |
|---|---|
| Section reveal on scroll | opacity 700ms + translate 900ms, `cubic-bezier(0.23, 1, 0.32, 1)` |
| Hover and colour changes | 250ms, `cubic-bezier(0.4, 0, 0.2, 1)` |
| Header | transparent over the hero, turns white with border on scroll (300ms) |
| Smooth scrolling | Lenis |
| Stats | count up when visible |
| Hero | slideshow with dots and pause button |
| Partners | infinite horizontal marquee with faded edges |

### Components

| Component | Look |
|---|---|
| **Primary button** | `primary-dark` fill, white text, radius 8px |
| **Hero buttons** | white fill + `primary` text; outline white button |
| **Secondary button** | white, 1px border, dark text |
| **Eyebrow + heading** | small green uppercase label above a bold heading |
| **Tag / pill** | soft tint background, small text (green, amber, gray) |
| **Stat card** | white card overlapping the hero bottom; big green number + "· label" |
| **Feature card** | `surface-alt` card, gradient icon tile, title, text or checklist |
| **Photo card** | image left, title, subtitle, schedule line, description, footer with tag and "→" link |
| **Event card** | slots-left pill, big green price in UZS, date and place with icons, divider, contact person + phone pill |
| **Person card** | photo on top, name, role in green |
| **Timeline** | dashed vertical line, alternating left/right steps, numbered titles, muted icon tiles |
| **Accordion** | white rounded rows, chevron on the right |
| **Segmented control** | pill track with a white active segment |
| **Sidebar item (portal)** | icon + label; active = `primary-dark` pill with white text and soft shadow |
| **Live demo bar (portal)** | `primary-tint` bar: "LIVE DEMO" pill, "Viewing as …", "What to try", "Switch role" |
| **Data table** | gray header row, thin row dividers, mono numbers |
| **Calendar widget** | 7-column grid, selected day = `primary-dark` rounded square, coloured legend dots |

---

## 4. Public Website

### Header
- Logo (MedOne wordmark in Lora + small "CLINIC · TASHKENT" line)
- Menu: **Departments · Check-ups · Health guides · Doctors · How it works · FAQ**
- Language switch (English / O'zbek), **Patient Portal** (outline), **Book a visit** (white)
- Mobile: logo, "Book" button, hamburger menu

### Home page sections (in order)

| # | Section | Content |
|---|---|---|
| 1 | **Hero** | Full-width photo slideshow with a dark green overlay. Pill "Tashkent · Open daily 08:00–20:00". Heading *"A calm, careful clinic where every patient is known."* Subline *"Experienced specialists, clear prices, and visits in the clinic or online."* Buttons **Book a visit**, **Patient Portal →**. Line *"Live demo: patient, doctor or admin — no password"*. Dots + pause |
| 2 | **Stats card** | 40 · doctors / 12 · departments / 25,000 · patients a year / 2018 · founded |
| 3 | **News & Events** | Carousel: photo left, card right (tag, date · place · time, title, text, "Read more →"), arrows top-right |
| 4 | **Why choose MedOne?** | *"Everything you need for your health, in one calm and well-run clinic."* 4 cards: **Digital clinic** (checklist: book online in a minute · results and prescriptions in the Patient Portal · AI Front Desk that answers from clinic data) · **Visits in the clinic or online** · **Doctors who speak English and Uzbek** · **Clear prices, no surprises** |
| 5 | **Facilities** | Doctor portrait in the middle, 10 icon items around it: MRI and CT, same-day lab results, pharmacy on site, children's area, step-free access, parking, 5 minutes from metro, 24/7 emergency line, sterile operating rooms, Wi-Fi and waiting lounge |
| 6 | **Patient Portal showcase** | *"MedOne Portal: your health in one app."* Tabs **Patient / Doctor**; three checklist items per tab; laptop + phone mockups; "Live preview · Web / Mobile" switch |
| 7 | **Partners** | *"Who we work with"*: insurance companies and laboratories, infinite marquee |
| 8 | **Departments** | Eyebrow "Our departments". Photo cards: Cardiology, Neurology, Paediatrics, Gynaecology, ENT, Dermatology… with subtitle, days and hours, description, tag "Online visits available", "See doctors →" |
| 9 | **Check-ups & screening days** | Eyebrow "Open to everyone". Cards: "12 slots left", "450,000 UZS", *Heart Check-up*, what is included, date · time, place, divider, "To book, contact: coordinator name + phone pill" |
| 10 | **Health guides** | Eyebrow "Free · No sign-up". Filter chips (Heart, Children, Women's health, Lifestyle). Cards: cover, "3 articles", title, source, "Start reading" |
| 11 | **Recognition** | Eyebrow "Clinical excellence". Cards with gold badge: doctor photo, name, department, award or certification |
| 12 | **Our doctors** | Chief physician card (round photo, name, title, quote with green left border) + photo grid of doctors |
| 13 | **Care for every age** | 3 photo cards: *Children · 0–17*, *Adults · 18–59*, *60+* with 3 checklist items each |
| 14 | **Your visit in 6 steps** | Zig-zag timeline: 01 Choose a doctor or ask the Front Desk · 02 Pick a time · 03 Pay online or at the clinic · 04 Get SMS reminders · 05 Visit in the clinic or online · 06 Results and prescriptions in your portal |
| 15 | **Patient desk** | Left: eyebrow "Patient desk", *"Questions about a visit or a check-up?"*, green contact box (phones, hours). Right: form (full name, phone +998, department, preferred time), hidden spam field, "Request a call back →", *"We will call you back within 30 minutes during opening hours."* |
| 16 | **FAQ** | Insurance · payment options · children · results timing · online visit requirements · parking |
| 17 | **Footer** | Logo, address, nearest metro, phones, email · "Follow us" (Telegram, Instagram, YouTube with coloured icon tiles) · "Portals" rows (Patient sign in →, Staff sign in →, Live demo →) · © 2026 MedOne Clinic · *"MedOne Clinic is a portfolio project; the clinic and its people are fictional."* · language switch |

### Inner pages

`/departments/[slug]` · `/doctors` · `/doctors/[slug]` (profile + free slots) · `/check-ups/[slug]` · `/guides/[slug]` · `/news/[slug]` · `/booking` · `/assistant`. All use the same header, footer and components.

---

## 5. Sign-in Pages

### `/login` (patients)
Split screen, exactly like Campusly:

- **Left panel** (`primary-dark`): logo, heading *"Your visits, results and prescriptions in one place."*, subline *"For patients and families."*, 3 items with outlined icon boxes (Book and manage visits · See results and prescriptions · Ask the AI Front Desk), quote at the bottom in italic, footer "© 2026 MedOne · Clinic website ↗"
- **Right panel**: language switch; heading **Sign in**; "Use your phone number."; uppercase label PHONE NUMBER with `+998` prefix; **Send code** (full-width `primary-dark` button); then a 6-digit code field
- **"or" divider**, then the **Live demo box**: *"One click, no password. A made-up clinic that resets every night."* Four role cards:
  - **Patient · in-clinic**: Aziz, upcoming visit and lab results
  - **Patient · online**: Madina, video visit today and AI Front Desk
  - **Doctor**: Dr. Nilufar, today's queue and prescriptions
  - **Admin**: clinic manager, content and reports (read-only)
  - Note: *"Sending SMS, payments and file uploads are turned off in the demo."*
- Bottom link: *"Staff? Sign in here →"*

### `/login/staff` (doctors and admins)
Same layout; staff ID + password; link *"Just looking? Open the doctor demo"*.

---

## 6. Portals

### Shared portal layout
- **Left sidebar** (256px): logo with sub-label (PATIENT PORTAL / DOCTOR PORTAL / ADMIN), menu, active item as a dark green pill; bottom: "MedOne · Patient Portal · 2026" and "Clinic website ↗"
- **Top bar**: page title (or breadcrumb), language switch, bell with orange count badge, name + subtitle, round dark green avatar with initials
- **Live demo bar** under the top bar (demo accounts only)
- Page header: small eyebrow (e.g. "November · Week 46"), greeting *"Good morning, Madina"*, one-line summary

### Patient Portal (`/portal`)

| Page | Content |
|---|---|
| **Home** | Greeting, "You have 2 upcoming visits". **Upcoming visits** list (doctor, department, date and time, type tag, buttons **Join call** / **Reschedule**). Right column: **To do** (e.g. "Fasting blood test tomorrow: no food after 22:00") and **Calendar** widget with legend (Visit, Check-up, Result ready, Reminder). **Recent results** cards |
| **My Visits** | Upcoming and past tabs, filter chips, rows with status tags (Confirmed, Paid, Completed, Cancelled) |
| **Calendar** | Month view + day list, filter chips (All, Visits, Check-ups, Results) |
| **Results** | Table: test, date, doctor, status, "Download PDF" |
| **Prescriptions** | Cards: medicine, dose, days, doctor, "Print" |
| **AI Front Desk** | Same layout as Campusly's AI Study Tutor: conversation list on the left, chat on the right, topic selector (Any department), suggestion chips (*"Which doctor for back pain?"*, *"How much is an MRI?"*, *"Free slots for a cardiologist tomorrow?"*), pill input with send button, footer *"Answers from clinic data, not a diagnosis · 10 left today"* |
| **Notices** | Clinic announcements (pinned first) |
| **Family** | Profile switcher in the top bar for your children (like Campusly's parent child switcher) |

### Doctor Portal (`/doctor`)

| Page | Content |
|---|---|
| **Dashboard** | Greeting + date. **Today's visits** card (patient, time, type; status pill "Waiting" / "In progress"; button **Start visit** or **Join call**). **Patient questions** card (unanswered). **Upcoming** list with day badges. **My week** summary cards |
| **Schedule** | Weekly calendar, set free slots, block time off |
| **Visits** | Table with filters; open a visit → notes, prescription, upload result |
| **Patients** | Search; patient page with visit history, results and prescriptions |
| **Notices** | Read clinic notices, post notices to own patients |
| **Patient Q&A** | Questions from patients with "Answer" action |

### Video visit (`/call/[id]`)
Portal layout without sidebar: large video area, small self-view, controls (mic, camera, audio only, end), side panel with chat and, for doctors, a notes and prescription form.

---

## 7. Admin Panel

Route `/admin`, same portal layout.

| Section | Content |
|---|---|
| **Activity** | Recent actions log (who changed what) |
| **Call-back requests** | Inbox: New → Called → Closed |
| **Appointments & payments** | All records with filters, export CSV |
| **Departments** | Create, edit, delete (photo, schedule, description) |
| **Check-ups** | Packages and screening days (price, date, place, total slots, coordinator) |
| **News & events** | Posts and events for the home carousel |
| **Health guides** | Guides with topics and articles |
| **Recognition** | Doctor awards and certifications |
| **Doctors** | Profiles, photos, languages, login accounts |
| **Users** | Patients and staff, roles |
| **Settings** | Clinic name, contacts, hours, stats numbers, hero slides, partners, FAQ |

Every content form has **English / O'zbek** tabs. Any change also **refreshes the AI Front Desk data**.

---

## 8. Tech Stack

Matched to what Campusly uses, so the result looks and behaves the same.

| Part | Technology |
|---|---|
| Framework | Next.js, TypeScript |
| UI | **MUI** with a custom theme (Emotion), tokens from section 3 |
| Fonts | `next/font`: Plus Jakarta Sans, Lora, JetBrains Mono |
| Smooth scroll and motion | Lenis + CSS transitions / Framer Motion |
| Internationalization | next-intl (`en`, `uz`) |
| Backend | Node.js, Express, TypeScript |
| Database | MongoDB Atlas |
| Patient sign-in | Phone + SMS code (Eskiz.uz) |
| Staff sign-in | Staff ID + password |
| Payments | Payme, Click (sandbox) |
| Video | WebRTC + Socket.io |
| AI | RAG: LLM API + MongoDB Atlas Vector Search |
| Deploy | Vercel (web), Render (api) |

---

## 9. Folder Structure

```
medone-clinic/
├── web/
│   ├── app/[locale]/
│   │   ├── (site)/                   # public website
│   │   ├── login/, login/staff/
│   │   ├── booking/
│   │   ├── portal/                   # patient portal
│   │   ├── doctor/                   # doctor portal
│   │   ├── admin/                    # admin panel
│   │   ├── call/[id]/                # video visit
│   │   └── assistant/                # public AI Front Desk page
│   ├── components/
│   │   ├── theme/                    # MUI theme: colours, typography, shapes, component overrides
│   │   ├── ui/                       # IconTile, Eyebrow, Tag, StatCard, PhotoCard, EventCard, PersonCard, Timeline...
│   │   ├── site/                     # home page sections
│   │   └── portal/                   # Sidebar, TopBar, LiveDemoBar, CalendarWidget, DataTable...
│   ├── messages/                     # en.json, uz.json
│   └── public/images/                # our own photos and mockups
├── api/
│   ├── src/models, routes, services, middlewares
│   ├── src/socket.ts
│   └── scripts/seed.ts, scripts/reset-demo.ts
└── README.md
```

---

## 10. Build Order

```
Day 1                    Day 2                         Day 3                          Day 4
DESIGN SYSTEM       →   SIGN-IN + BOOKING        →   DOCTOR PORTAL             →   ADMIN PANEL
+ PUBLIC WEBSITE         + PAYMENTS                    + VIDEO VISITS                  + LIVE DEMO
                         + PATIENT PORTAL              + AI FRONT DESK (RAG)           + DEPLOY
```

Until the admin panel exists, data comes from the seed script. Every evening: commit, push, working state.

---

## 11. Day 1: Design System and Public Website

**Goal:** the full public website, looking like Campusly, in English and Uzbek.

### Block 1: Setup (1 h)
- [ ] `web` (Next.js + MUI + Emotion) and `api` (Express), MongoDB Atlas, `.env`
- [ ] next-intl with `en` and `uz`

### Block 2: Theme and base components (2 h)
- [ ] MUI theme with all tokens from section 3 (colours, fonts, radius, shadows, button and input overrides)
- [ ] Fonts: Plus Jakarta Sans, Lora, JetBrains Mono
- [ ] Components: IconTile (7 gradients), Eyebrow + SectionHeading, Tag, StatCard, FeatureCard, PhotoCard, EventCard, PersonCard, Timeline, Accordion, SegmentedControl
- [ ] Reveal-on-scroll wrapper and Lenis

### Block 3: Data and API (1.5 h)
- [ ] Models: Department, Doctor, CheckupEvent, Guide, News, Recognition, Partner, FAQ, CallbackRequest, Settings
- [ ] Public APIs + `POST /callback-requests` (rate limit + hidden spam field)
- [ ] Seed: bilingual content for every section

### Block 4: Header and footer (1 h)
- [ ] Transparent-to-white header on scroll, language switch, mobile menu
- [ ] Footer with portals rows and portfolio disclaimer

### Block 5: Home page (4 h)
- [ ] Hero slideshow, stats card, news carousel
- [ ] Why choose MedOne, facilities
- [ ] Portal showcase (tabs, mockups, Web / Mobile)
- [ ] Partners marquee, departments, check-ups
- [ ] Health guides, recognition, our doctors
- [ ] Care for every age, 6-step timeline, patient desk form, FAQ

### Block 6: Inner pages (1.5 h)
- [ ] Department, doctor list and profile, check-up, guide, news pages

### Block 7: Review (0.5 h)
- [ ] Side by side with campusly.uz on desktop and mobile: spacing, sizes, colours, motion
- [ ] Both languages

### ✅ Day 1 result
- [ ] Public website matches the Campusly look, with MedOne content
- [ ] Works on mobile and in both languages
- [ ] Call-back requests are saved

---

## 12. Day 2: Sign-in, Booking, Payments, Patient Portal

**Goal:** a patient signs in, books, pays and manages visits in the portal.

### Block 1: Sign-in pages (2 h)
- [ ] User model (patient, doctor, admin)
- [ ] `/login`: split-screen design, phone + SMS code (Eskiz; console in development)
- [ ] `/login/staff`: staff ID + password
- [ ] Role-based access

### Block 2: Slots and booking (3 h)
- [ ] Slot and Appointment models (in-clinic or online)
- [ ] Free slots on the doctor profile
- [ ] Booking API: **one patient per slot** + test (50 parallel requests → 1 success)
- [ ] Check-up booking: slots left never below zero

### Block 3: Booking page (1.5 h)
- [ ] Steps: visit type → department → doctor → date and time → confirm, in the Campusly card style

### Block 4: Payments and SMS (2 h)
- [ ] Payme and Click sandbox, "Pay at the clinic"
- [ ] **No double charging**; unpaid online bookings free the slot after 10 minutes
- [ ] Confirmation SMS and reminders (1 day and 2 hours before)

### Block 5: Patient Portal (3 h)
- [ ] Portal layout: sidebar, top bar, bell, avatar
- [ ] Home (upcoming visits, to do, calendar widget, recent results)
- [ ] My Visits, Calendar, Results, Prescriptions, Notices
- [ ] Family profile switcher

### ✅ Day 2 result
- [ ] Sign in → book → pay (sandbox) → see the visit in the portal
- [ ] Double booking and double charging are impossible (tests)
- [ ] Portal looks like the Campusly student portal

---

## 13. Day 3: Doctor Portal, Video Visits, AI Front Desk

**Goal:** doctors run their day, video visits work, and the AI answers from clinic data.

### Block 1: Doctor Portal (2.5 h)
- [ ] Dashboard (today's visits, patient questions, upcoming, week summary)
- [ ] Schedule (set free slots, time off), Visits, Patients, Notices, Patient Q&A

### Block 2: Video visits (3 h)
- [ ] Socket.io: only this visit's patient and doctor can join
- [ ] WebRTC video and audio, controls, audio-only mode
- [ ] Chat side panel; doctor notes and prescription form
- [ ] Test on two devices

### Block 3: AI data (2 h)
- [ ] Chunk departments, doctors, check-ups, guides, FAQ, settings
- [ ] Embed and store (Atlas Vector Search); retrieval

### Block 4: AI answers (2 h)
- [ ] **Emergency filter** first → "Call 103!"
- [ ] Live tools: free slots, prices, check-up slots left, doctors
- [ ] Answers only from retrieved data, with sources; English or Uzbek

### Block 5: AI Front Desk interface (1.5 h)
- [ ] Portal page in the Campusly AI Tutor layout (conversation list, topic selector, suggestion chips, pill input, daily limit)
- [ ] Public `/assistant` page and a "Ask the Front Desk" entry on the website
- [ ] "Book this doctor" button under answers; "This is not a diagnosis"

### ✅ Day 3 result
- [ ] Doctor sees the queue, runs a video visit, writes a prescription; patient sees it
- [ ] AI correctly answers about prices, doctors, slots, check-ups and hours
- [ ] Emergencies never get a doctor recommendation

---

## 14. Day 4: Admin Panel, Live Demo, Launch

**Goal:** admins manage everything, anyone can try the demo, the site is live.

### Block 1: Admin layout and tables (1 h)
- [ ] Sidebar sections from section 7, data table, bilingual form tabs, image upload

### Block 2: Content sections (3 h)
- [ ] Departments, check-ups, news, health guides, recognition, doctors, settings (stats, hero slides, partners, FAQ)

### Block 3: Operations (1.5 h)
- [ ] Call-back requests inbox, appointments and payments (filters, CSV export), users, activity log

### Block 4: AI sync (0.5 h)
- [ ] Admin changes refresh AI data automatically; test with a new doctor

### Block 5: Live demo (1.5 h)
- [ ] Live demo box on `/login` with 4 role cards
- [ ] Live demo bar in portals: "Viewing as …", **What to try** tips, **Switch role**
- [ ] Demo limits: no real SMS, sandbox payments, no uploads, admin read-only
- [ ] `reset-demo` script runs every night

### Block 6: Testing and security (1 h)
- [ ] Patients see only their own data and calls
- [ ] Rate limits: SMS codes, sign-in, AI, call-back form
- [ ] 40 AI test questions in English and Uzbek

### Block 7: Deploy and README (2.5 h)
- [ ] Render (api), Vercel (web), sandbox payment webhooks
- [ ] Full test on the live site: website → Front Desk → booking → payment → video → prescription → admin
- [ ] README: screenshots, live demo link, how to run locally

### ✅ Day 4 result
- [ ] Admin manages all content; changes show on the site and in the AI
- [ ] One-click demo for patient, doctor and admin
- [ ] Live site and README

---

## 15. Core Rules

### Booking and payments
- **One patient per slot**; check-up slots never below zero
- **Never charge twice**
- Unpaid online bookings release the slot after **10 minutes**

### Security
- Patients see **only their own** visits, results, prescriptions and calls
- **Only that patient and that doctor** can join a video visit
- **Only admins** open the admin panel
- Demo accounts: no real SMS, sandbox payments, nightly reset

### AI Front Desk
- Answers **only from clinic data**; otherwise "I don't have that information, please call us"
- Always shows **sources**
- **Never diagnoses**
- Emergencies: **"Call 103!"**
- Recommends **only** what the clinic has

---

## 16. If You Run Out of Time

Postpone in this order (top first):

1. Recognition section
2. Health guides
3. Family profile switcher
4. Patient Q&A in the Doctor Portal
5. Activity log and CSV export
6. Click (keep Payme)
7. Hero slideshow (keep one image) and partners marquee (static row)

**Never cut:** one patient per slot, no double charging, access checks, AI emergency filter, video visits, core admin, live demo, deployment.

---

## 17. Notes

- Campusly is the **design reference**. MedOne uses its own name, logo, texts, photos and people; nothing is copied from Campusly's content or images.
- Photos: licensed stock or our own generated images, credited in the README if required.
- Payments run in **Payme and Click sandbox**. Real payments need a registered legal entity and merchant agreements.
- Before using this for a real clinic, check **personal data and online medical services** rules with a lawyer.
- All demo data is **fictional**; the footer says so.
