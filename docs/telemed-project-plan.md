# Telemeditsina ilovasi: 0 dan tugatguncha to'liq reja

> **Stack:** Node.js (Express) + Next.js + MongoDB, butun loyiha TypeScript'da.
> **Muddat:** taxminan 10 hafta (0-hafta tayyorgarlik + 8 hafta ishlab chiqish + 1 hafta yakunlash), kuniga 3–4 soat ishlaganda.
> **Maqsad:** Koreyadagi kompaniyalarga ko'rsatish mumkin bo'lgan, deploy qilingan, testlangan va hujjatlashtirilgan full stack + AI loyiha.

---

## Mundarija

1. [Loyiha nima qiladi](#1-loyiha-nima-qiladi)
2. [Stack va nima uchun aynan shu](#2-stack-va-nima-uchun-aynan-shu)
3. [Arxitektura](#3-arxitektura)
4. [Papka tuzilmasi](#4-papka-tuzilmasi)
5. [Ma'lumotlar bazasi sxemasi](#5-malumotlar-bazasi-sxemasi)
6. [API va Socket hodisalari](#6-api-va-socket-hodisalari)
7. [Ish tartibi: Git, branch, commit](#7-ish-tartibi-git-branch-commit)
8. [Hafta-hafta reja](#8-hafta-hafta-reja)
9. [Test strategiyasi](#9-test-strategiyasi)
10. [Xavfsizlik ro'yxati](#10-xavfsizlik-royxati)
11. [Deploy](#11-deploy)
12. [README va portfolio](#12-readme-va-portfolio)
13. [Loyiha tugagandan keyin](#13-loyiha-tugagandan-keyin)
14. [Yakuniy tekshiruv ro'yxati](#14-yakuniy-tekshiruv-royxati)

---

## 1. Loyiha nima qiladi

Bemor simptomlarini yozadi. AI qaysi bo'lim shifokoriga borish kerakligini tavsiya qiladi, bemor shifokorga yoziladi, to'lov qiladi, video orqali konsultatsiya oladi va elektron retsept oladi.

### Rollar
| Rol | Nima qila oladi |
|---|---|
| **Bemor (PATIENT)** | Ro'yxatdan o'tish, simptom yozish, shifokor qidirish, vaqt band qilish, to'lov, video qo'ng'iroq, retsept ko'rish, sharh yozish |
| **Shifokor (DOCTOR)** | Profil to'ldirish, litsenziya yuklash, ish jadvali (slotlar) yaratish, qabullar ro'yxati, video qo'ng'iroq, xulosa va retsept yozish |
| **Admin (ADMIN)** | Shifokorlarni tasdiqlash yoki rad etish, foydalanuvchilarni boshqarish, statistika |

### MVP'ga kiradi
- Auth va rollar
- Shifokor profili va slotlar
- AI triage (bo'lim tavsiyasi) va shoshilinch holat filtri
- Band qilish (concurrency himoyasi bilan) va test to'lov
- Video konsultatsiya va chat
- Elektron retsept, sharhlar, bildirishnomalar
- Admin panel

### MVP'ga kirmaydi (keyinroq)
- Mobil ilova
- Haqiqiy dorixona integratsiyasi
- Sug'urta, haqiqiy to'lov

---

## 2. Stack va nima uchun aynan shu

### Umumiy
| Vosita | Nima uchun |
|---|---|
| **TypeScript** | Frontend va backend bitta tilda, turlarni (types) umumiy paketda ulashish mumkin |
| **pnpm workspaces + Turborepo** | Monorepo: `web`, `api`, `shared` bitta repoda, tez build |
| **Docker Compose** | MongoDB, Redis va boshqa servislarni bitta buyruq bilan lokal ishga tushirish |
| **ESLint + Prettier + Husky + lint-staged** | Kod sifati va bir xil formatlash, commit oldidan avtomatik tekshiruv |

### Backend (`apps/api`)
| Vosita | Vazifasi |
|---|---|
| **Node.js 22 LTS + Express** | HTTP server |
| **Mongoose** | MongoDB bilan ishlash, sxemalar |
| **Zod** | So'rovlarni validatsiya qilish (sxemalar `shared` paketda) |
| **jsonwebtoken + bcrypt** | Auth: access token (15 daq) + refresh token (7 kun), httpOnly cookie'da |
| **ioredis** | Kesh, rate limit, refresh token blacklist |
| **BullMQ** | Fon vazifalari: muddati o'tgan slotlarni ochish, eslatma xabarlari |
| **Socket.io** | WebRTC signaling va chat |
| **pino** | Strukturali loglar |
| **helmet, cors, express-rate-limit** | Xavfsizlik |
| **multer + S3 (yoki Cloudinary)** | Shifokor litsenziyasi va avatar fayllarini yuklash |
| **swagger-ui-express** | API hujjati |
| **Nodemailer (Resend)** | E-mail bildirishnomalar |

### Frontend (`apps/web`)
| Vosita | Vazifasi |
|---|---|
| **Next.js 15 (App Router)** | Sahifalar, SSR, routing |
| **Tailwind CSS + shadcn/ui** | Tez va chiroyli UI komponentlari |
| **TanStack Query (React Query)** | Server ma'lumotlarini olish va keshlash |
| **Zustand** | Kichik global holat (foydalanuvchi, qo'ng'iroq holati) |
| **React Hook Form + Zod** | Formalar va validatsiya |
| **next-intl** | Ko'p tillilik: koreys, ingliz, o'zbek |
| **socket.io-client** | Real-time ulanish |
| **Toss Payments SDK** | To'lov oynasi (test rejimi) |

### AI
| Vosita | Vazifasi |
|---|---|
| **LLM API** (Claude yoki OpenAI) | Simptomlarni tahlil qilib JSON qaytarish |
| **Embedding modeli** | Simptom matnlarini vektorga aylantirish |
| **MongoDB Atlas Vector Search** | RAG uchun o'xshash yozuvlarni topish (lokalda `mongodb/mongodb-atlas-local` Docker image'i bilan) |

### Test va sifat
| Vosita | Vazifasi |
|---|---|
| **Vitest** | Unit testlar |
| **Supertest + mongodb-memory-server** | API integratsion testlari |
| **Playwright** | E2E testlar (brauzerda butun oqim) |
| **k6** | Load test (concurrency isboti) |

### Deploy
| Qism | Qayerga |
|---|---|
| Frontend | Vercel |
| Backend (Socket.io bor, shuning uchun doimiy server kerak) | Render, Railway yoki AWS EC2 |
| MongoDB | MongoDB Atlas (bepul M0 klaster) |
| Redis | Upstash yoki Redis Cloud (bepul) |
| TURN server | Metered.ca bepul tarifi yoki o'z coturn serveringiz |
| Xatolar monitoringi | Sentry |
| CI/CD | GitHub Actions |

---

## 3. Arxitektura

```
                     ┌──────────────────────┐
                     │   Next.js (Vercel)   │
                     │ bemor / shifokor /   │
                     │ admin sahifalari     │
                     └─────┬──────────┬─────┘
                  REST (HTTPS)     Socket.io (WSS)
                           │          │
                ┌──────────▼──────────▼──────────┐
                │   Node.js + Express API        │
                │  ┌──────┐ ┌──────┐ ┌────────┐  │
                │  │ auth │ │ appt │ │ triage │  │
                │  └──────┘ └──────┘ └───┬────┘  │
                │  ┌──────────────┐      │       │
                │  │ socket (sig.)│      │       │
                │  └──────────────┘      │       │
                └───┬─────────┬──────────┼───────┘
                    │         │          │
             ┌──────▼──┐ ┌────▼────┐ ┌───▼────────────┐
             │ MongoDB │ │  Redis  │ │ LLM API +      │
             │ (Atlas) │ │ BullMQ  │ │ Vector Search  │
             └─────────┘ └─────────┘ └────────────────┘

   Bemor ◄──── WebRTC (peer-to-peer video, kerak bo'lsa TURN orqali) ────► Shifokor
```

**Backend ichki qatlamlari (har bir modulda):**
```
route → middleware (auth, validate) → controller → service → model (Mongoose)
```
- **controller:** faqat so'rov va javob bilan ishlaydi
- **service:** biznes logika (testlash oson)
- **model:** ma'lumotlar bazasi

---

## 4. Papka tuzilmasi

```
telemed/
├── apps/
│   ├── api/
│   │   ├── src/
│   │   │   ├── config/            # env, db, redis ulanishlari
│   │   │   ├── modules/
│   │   │   │   ├── auth/          # auth.routes.ts, auth.controller.ts, auth.service.ts
│   │   │   │   ├── users/
│   │   │   │   ├── doctors/
│   │   │   │   ├── slots/
│   │   │   │   ├── appointments/
│   │   │   │   ├── payments/
│   │   │   │   ├── triage/
│   │   │   │   ├── consultations/
│   │   │   │   ├── prescriptions/
│   │   │   │   ├── reviews/
│   │   │   │   ├── notifications/
│   │   │   │   └── admin/
│   │   │   ├── socket/            # signaling.ts, chat.ts
│   │   │   ├── jobs/              # BullMQ: slot-expiry.ts, reminders.ts
│   │   │   ├── middlewares/       # auth.ts, role.ts, validate.ts, error.ts, audit.ts
│   │   │   ├── utils/             # errors.ts, logger.ts
│   │   │   ├── app.ts             # express ilovasi
│   │   │   └── server.ts          # http + socket.io ishga tushirish
│   │   ├── tests/
│   │   ├── scripts/seed.ts        # test ma'lumotlari
│   │   └── Dockerfile
│   └── web/
│       ├── app/
│       │   ├── [locale]/
│       │   │   ├── (public)/      # bosh sahifa, login, register
│       │   │   ├── (patient)/     # triage, doctors, appointments, prescriptions
│       │   │   ├── doctor/        # dashboard, schedule, appointments
│       │   │   ├── admin/         # doctors approval, stats
│       │   │   └── call/[id]/     # video konsultatsiya xonasi
│       ├── components/
│       ├── hooks/                 # useWebRTC.ts, useAuth.ts
│       ├── lib/                   # api client, socket client
│       ├── messages/              # ko.json, en.json, uz.json
│       └── e2e/                   # Playwright testlari
├── packages/
│   └── shared/                    # Zod sxemalar, turlar, enum'lar
├── load-tests/                    # k6 skriptlari
├── docs/                          # arxitektura, ERD, qarorlar (ADR)
├── .github/workflows/ci.yml
├── docker-compose.yml
├── turbo.json
├── pnpm-workspace.yaml
└── README.md
```

---

## 5. Ma'lumotlar bazasi sxemasi

```ts
// users
{
  _id, email (unique), passwordHash, role: 'PATIENT' | 'DOCTOR' | 'ADMIN',
  name, phone, locale: 'ko' | 'en' | 'uz', createdAt
}

// doctors
{
  _id, userId (ref users, unique), department, licenseNo, licenseFileUrl,
  status: 'PENDING' | 'APPROVED' | 'REJECTED',
  price, bio, languages: [String], ratingAvg, ratingCount
}
// index: { department: 1, status: 1, ratingAvg: -1 }

// slots
{
  _id, doctorId, start: Date, end: Date,
  status: 'OPEN' | 'HELD' | 'BOOKED', heldBy, heldUntil
}
// index: { doctorId: 1, start: 1 } unique, { status: 1, heldUntil: 1 }

// appointments
{
  _id, patientId, doctorId, slotId (unique), symptomText,
  triage: { departments: [{ name, confidence }], urgency, emergency },
  status: 'PENDING' | 'CONFIRMED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED',
  createdAt
}

// payments
{ _id, appointmentId, amount, provider: 'TOSS', providerPaymentKey,
  status: 'READY' | 'PAID' | 'FAILED' | 'REFUNDED', idempotencyKey (unique) }

// consultations
{ _id, appointmentId, startedAt, endedAt, doctorNote,
  messages: [{ senderId, text, at }] }

// prescriptions
{ _id, appointmentId, doctorId, patientId,
  items: [{ medicine, dosage, timesPerDay, days }], note, createdAt }

// reviews
{ _id, appointmentId (unique), patientId, doctorId, rating: 1-5, comment }

// triage_knowledge (RAG uchun)
{ _id, symptom, description, department, source, embedding: [Number] }

// audit_logs
{ _id, userId, action, resource, resourceId, ip, at }

// notifications
{ _id, userId, type, title, body, read: Boolean, createdAt }
```

**Appointment holat mashinasi:**
```
PENDING ──(to'lov o'tdi)──► CONFIRMED ──(qo'ng'iroq boshlandi)──► IN_PROGRESS ──► COMPLETED
   │                            │
   └──(10 daqiqa o'tdi)──► CANCELLED ◄──(bekor qilindi)
```
Faqat ruxsat etilgan o'tishlarga ruxsat beriladi, qolganlari `409 Conflict` qaytaradi.

---

## 6. API va Socket hodisalari

### REST API
```
# Auth
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout
GET    /api/auth/me

# Shifokorlar
GET    /api/doctors?department=&date=&page=
GET    /api/doctors/:id
POST   /api/doctors/profile                 (DOCTOR)
POST   /api/doctors/license                 (DOCTOR, fayl yuklash)

# Slotlar
GET    /api/doctors/:id/slots?date=
POST   /api/slots/bulk                      (DOCTOR: haftalik jadval yaratish)
DELETE /api/slots/:id                       (DOCTOR)

# AI triage
POST   /api/triage

# Qabullar
POST   /api/appointments                    (slotni HELD qiladi)
GET    /api/appointments/me
GET    /api/appointments/:id
PATCH  /api/appointments/:id/cancel

# To'lov
POST   /api/payments/confirm                (Idempotency-Key header)

# Konsultatsiya va retsept
POST   /api/consultations/:appointmentId/start   (DOCTOR)
POST   /api/consultations/:appointmentId/end     (DOCTOR)
POST   /api/prescriptions                        (DOCTOR)
GET    /api/prescriptions/me                     (PATIENT)

# Sharhlar
POST   /api/reviews

# Bildirishnomalar
GET    /api/notifications
PATCH  /api/notifications/:id/read

# Admin
GET    /api/admin/doctors?status=PENDING
PATCH  /api/admin/doctors/:id/approve
PATCH  /api/admin/doctors/:id/reject
GET    /api/admin/stats
```

### Socket.io hodisalari
```
Client → Server:  call:join { appointmentId }
Server → Client:  call:peer-joined
Client ↔ Server:  call:offer, call:answer, call:ice-candidate
Client → Server:  call:leave
Client ↔ Server:  chat:message { appointmentId, text }
Server → Client:  notification:new
```
Socket ulanishida ham JWT tekshiriladi, foydalanuvchi faqat o'z qabuli xonasiga kira oladi.

### Xato javobi formati (barcha API uchun bir xil)
```json
{ "error": { "code": "SLOT_ALREADY_BOOKED", "message": "Bu vaqt allaqachon band" } }
```

---

## 7. Ish tartibi: Git, branch, commit

- `main` branch'i doim ishlaydigan holatda bo'ladi
- Har bir funksiya alohida branch'da: `feat/auth`, `feat/booking`, `fix/slot-expiry`
- Har bir branch Pull Request orqali birlashtiriladi, CI yashil bo'lishi kerak (o'zingiz uchun ham PR oching, bu rekruterlarga ish uslubingizni ko'rsatadi)
- Commit xabarlari **Conventional Commits** formatida:
  ```
  feat(booking): add atomic slot hold with 10-minute expiry
  fix(auth): rotate refresh token on use
  test(booking): add concurrency test for double booking
  docs: add architecture diagram
  ```
- GitHub Issues va Projects (Kanban) doskasida haftalik vazifalarni yuritish

---

## 8. Hafta-hafta reja

### 0-hafta: Tayyorgarlik va loyihalash (kod yozmasdan)

**Vazifalar:**
- [ ] Kompyuterga o'rnatish: Node.js 22, pnpm, Docker Desktop, Git, VS Code
- [ ] Akkauntlar: GitHub, MongoDB Atlas, Vercel, Render, Upstash, Sentry, Toss Payments developers (test kalitlari), LLM API
- [ ] **User story'lar** yozish (masalan: "Bemor sifatida men simptomlarimni yozib, qaysi shifokorga borishni bilmoqchiman")
- [ ] **Wireframe'lar** (Figma yoki qog'ozda): bosh sahifa, triage, shifokorlar ro'yxati, band qilish, video xona, shifokor paneli, admin
- [ ] **ERD** chizish (dbdiagram.io yoki Excalidraw)
- [ ] API ro'yxatini yakunlash (yuqoridagi 6-bo'lim)
- [ ] GitHub'da `telemed` reposi va Projects doskasi

**Natija:** `docs/` papkasida wireframe, ERD va user story'lar.

---

### 1-hafta: Loyiha poydevori va autentifikatsiya

**Sozlash:**
```bash
mkdir telemed && cd telemed
pnpm init
# pnpm-workspace.yaml: packages: ["apps/*", "packages/*"]
pnpm dlx create-next-app@latest apps/web --ts --tailwind --app --eslint
mkdir -p apps/api/src packages/shared/src
pnpm add -D turbo typescript prettier husky lint-staged -w
```

**docker-compose.yml:**
- `mongo` (replica set rejimida, tranzaksiyalar uchun shart) yoki `mongodb/mongodb-atlas-local` (vector search ham ishlaydi)
- `redis`
- `mongo-express` (ixtiyoriy, bazani ko'rish uchun)

**Vazifalar:**
- [ ] Monorepo, Turborepo, ESLint, Prettier, Husky
- [ ] `apps/api`: Express, TypeScript, `config/env.ts` (Zod bilan env tekshiruvi), pino logger, markaziy xato middleware
- [ ] `packages/shared`: Zod sxemalar (`registerSchema`, `loginSchema`), enum'lar (`Role`, `Department`)
- [ ] User modeli
- [ ] Auth: register, login, refresh (token rotatsiyasi), logout, `/me`
- [ ] Middleware'lar: `requireAuth`, `requireRole('DOCTOR')`, `validate(schema)`
- [ ] Frontend: login va register sahifalari, `AuthProvider`, himoyalangan sahifalar (Next.js middleware)
- [ ] next-intl sozlash (ko, en, uz)
- [ ] GitHub Actions: lint + typecheck + test
- [ ] Auth uchun birinchi integratsion testlar

**Natija:** foydalanuvchi ro'yxatdan o'tadi, kiradi, roliga qarab boshqa sahifaga yo'naltiriladi. CI yashil.

---

### 2-hafta: Shifokorlar va ish jadvali

**Vazifalar:**
- [ ] Doctor modeli, profil to'ldirish sahifasi
- [ ] Litsenziya faylini yuklash (multer → S3 yoki Cloudinary), fayl turi va hajmini tekshirish
- [ ] Admin: tasdiqlanmagan shifokorlar ro'yxati, tasdiqlash yoki rad etish
- [ ] Slot modeli, shifokor uchun haftalik jadval yaratish (masalan, "dushanba–juma, 09:00–12:00, 30 daqiqalik") → `POST /slots/bulk`
- [ ] Shifokorlar qidiruvi: bo'lim, sana, narx, reyting bo'yicha filtr va sahifalash (pagination)
- [ ] Shifokor sahifasi: profil va bo'sh vaqtlar kalendari
- [ ] `scripts/seed.ts`: 20 ta shifokor, slotlar va bemorlar

**Natija:** bemor shifokorlarni qidirib, bo'sh vaqtlarini ko'ra oladi.

---

### 3-hafta: Band qilish va to'lov (eng muhim backend hafta)

**Band qilish:**
```ts
// 1. Slotni atomik tarzda ushlab qolish
const slot = await Slot.findOneAndUpdate(
  { _id: slotId, status: 'OPEN', start: { $gt: new Date() } },
  { status: 'HELD', heldBy: userId, heldUntil: addMinutes(new Date(), 10) },
  { new: true }
);
if (!slot) throw new AppError(409, 'SLOT_ALREADY_BOOKED');

// 2. PENDING holatidagi appointment yaratish
```

**To'lovni tasdiqlash (tranzaksiya ichida):**
```ts
const session = await mongoose.startSession();
await session.withTransaction(async () => {
  // Idempotency: shu kalit bilan to'lov bormi?
  // Toss API orqali to'lovni tasdiqlash
  // Payment → PAID
  // Slot → BOOKED
  // Appointment → CONFIRMED
});
```

**Vazifalar:**
- [ ] Atomik slot band qilish
- [ ] BullMQ job: muddati o'tgan `HELD` slotlarni qayta `OPEN` qilish va appointment'ni `CANCELLED` qilish
- [ ] Toss Payments test integratsiyasi (frontend'da to'lov oynasi, backend'da tasdiqlash)
- [ ] `Idempotency-Key` header va unique index
- [ ] Appointment holat mashinasi (`canTransition(from, to)` funksiyasi va unit testlari)
- [ ] Bekor qilish va pulni qaytarish (refund) logikasi
- [ ] Frontend: band qilish oqimi, "Mening qabullarim" sahifasi
- [ ] **Concurrency testi:** 50 ta parallel so'rovdan faqat 1 tasi muvaffaqiyatli bo'lishi kerak

**Natija:** bemor vaqt band qilib, test to'lov qiladi. Bir slotni ikki kishi band qila olmasligi test bilan isbotlangan.

---

### 4-hafta: AI triage

**Oqim:**
```
1. Shoshilinch filtr (qoidalar): ko'krak og'rig'i, nafas qisishi, hushdan ketish,
   kuchli qon ketishi, o'z joniga qasd qilish fikrlari...
   → emergency: true, 119 / 1393 (inqiroz liniyasi) ko'rsatiladi, LLM chaqirilmaydi
2. Matnni embedding'ga aylantirish
3. Atlas Vector Search: eng o'xshash 5 ta yozuv (triage_knowledge)
4. LLM'ga: tizim ko'rsatmasi + topilgan kontekst + bemor matni
5. Javobni Zod bilan tekshirish; noto'g'ri bo'lsa, 1 marta qayta urinish, keyin "Umumiy amaliyot (가정의학과)"
6. Natijani appointment.triage'ga saqlash
```

**Vazifalar:**
- [ ] `triage_knowledge` ma'lumotlari: simptom → bo'lim bog'liqliklari (100–300 ta yozuv, ochiq manbalardan), embedding skripti
- [ ] Vector Search indeksi
- [ ] Shoshilinch filtr (ko, en, uz tillarida kalit so'zlar) va unit testlar
- [ ] LLM chaqiruvi, JSON javob, Zod validatsiya, timeout va xatolarni boshqarish
- [ ] Rate limit: bir foydalanuvchi daqiqasiga 5 ta so'rov
- [ ] Frontend: simptom kiritish sahifasi, natija kartochkalari (bo'lim + foiz), "shu bo'lim shifokorlarini ko'rish" tugmasi
- [ ] UI'da ogohlantirish: "Bu tashxis emas, faqat yo'naltiruvchi tavsiya"
- [ ] **Baholash to'plami:** 50 ta test holati (matn → kutilgan bo'lim), accuracy'ni hisoblaydigan skript

**Natija:** AI bo'lim tavsiya qiladi, shoshilinch holatlarni ushlaydi, aniqlik raqamda o'lchangan.

---

### 5-hafta: Video konsultatsiya va chat

**WebRTC oqimi:**
```
1. Ikkala tomon /call/[appointmentId] sahifasiga kiradi
2. Socket orqali call:join → server ruxsatni tekshiradi (faqat shu bemor va shifokor, faqat qabul vaqti atrofida)
3. Birinchi kelgan kutadi, ikkinchisi kelganda offer → answer → ICE candidate almashinuvi
4. Peer-to-peer video ulanadi (NAT ortida bo'lsa TURN orqali)
```

**Vazifalar:**
- [ ] Socket.io serveri, JWT bilan socket autentifikatsiyasi
- [ ] Signaling hodisalari
- [ ] `useWebRTC` hook: kamera va mikrofon olish, `RTCPeerConnection`, ulanish holati
- [ ] STUN va TURN sozlamalari
- [ ] UI: video oynalar, mikrofon va kamerani o'chirish, qo'ng'iroqni tugatish
- [ ] Qayta ulanish: internet uzilsa, avtomatik qayta urinish
- [ ] Qo'ng'iroq ichidagi chat (xabarlar `consultations` ga saqlanadi)
- [ ] Shifokor "boshlash" va "tugatish" → `IN_PROGRESS` va `COMPLETED`

**Natija:** ikki xil brauzer yoki qurilmada bemor va shifokor bir-birini ko'rib gaplasha oladi.

---

### 6-hafta: Retsept, bildirishnomalar, sharhlar, admin

**Vazifalar:**
- [ ] Shifokor qo'ng'iroqdan keyin xulosa va retsept yozadi (dorilar ro'yxati formasi)
- [ ] Bemor retseptni ko'radi va PDF qilib yuklab oladi
- [ ] Bildirishnomalar: band qilish tasdiqlandi, qabulga 10 daqiqa qoldi (BullMQ delayed job), retsept tayyor. Kanallar: ilova ichida (socket), e-mail
- [ ] Sharhlar: faqat `COMPLETED` qabuldan keyin va faqat bir marta; shifokor reytingini qayta hisoblash
- [ ] Admin dashboard: foydalanuvchilar soni, kunlik qabullar, daromad, eng ko'p tavsiya qilingan bo'limlar (MongoDB aggregation)
- [ ] Shifokor dashboardi: bugungi qabullar, kelgusi jadval

**Natija:** MVP funksional jihatdan to'liq.

---

### 7-hafta: Sifat, xavfsizlik va testlar

**Vazifalar:**
- [ ] Unit testlar: holat mashinasi, shoshilinch filtr, narx hisoblash, ruxsatlar
- [ ] Integratsion testlar: auth, band qilish, to'lov, retsept (mongodb-memory-server)
- [ ] E2E (Playwright): ro'yxatdan o'tish → triage → band qilish → to'lov → retsept ko'rish
- [ ] **k6 load test:** 100 ta virtual foydalanuvchi bitta slotni band qilishga urinadi → natija: 1 ta muvaffaqiyatli, 99 ta `409`. p95 latency'ni yozib oling
- [ ] Audit log middleware (tibbiy ma'lumotga kim kirgani)
- [ ] Xavfsizlik ro'yxatini (10-bo'lim) bandma-band tekshirish
- [ ] Sentry ulash (frontend va backend)
- [ ] Swagger API hujjati
- [ ] Accessibility va mobil ko'rinishni tekshirish (Lighthouse)

**Natija:** test qamrovi kamida 70% (asosiy modullar), load test natijalari, xavfsizlik tekshirilgan.

---

### 8-hafta: Deploy va CI/CD

**Vazifalar:**
- [ ] MongoDB Atlas klasteri, Vector Search indeksi, seed ma'lumotlari
- [ ] Upstash Redis
- [ ] Backend: Dockerfile (multi-stage build), Render yoki Railway'ga deploy
- [ ] Frontend: Vercel'ga deploy, env o'zgaruvchilari
- [ ] Domen (masalan, `telemed-demo.xyz`) va HTTPS
- [ ] GitHub Actions: PR'da lint + test, `main` ga merge bo'lganda avtomatik deploy
- [ ] Health check endpoint (`/api/health`) va uptime monitoringi (UptimeRobot)
- [ ] Demo akkauntlar: `patient@demo.com`, `doctor@demo.com`, `admin@demo.com`

**Natija:** loyiha internetda ishlaydi, har bir push avtomatik tekshiriladi va deploy qilinadi.

---

### 9-hafta: Hujjatlar, portfolio va yakunlash

**Vazifalar:**
- [ ] README (12-bo'limdagi tuzilma bo'yicha)
- [ ] Arxitektura diagrammasi va ERD rasmlari
- [ ] 2–3 daqiqalik demo video (YouTube yoki Loom) va GIF'lar
- [ ] `docs/decisions/`: muhim qarorlar (ADR), masalan "Nima uchun slot band qilish uchun atomik update tanlandi"
- [ ] Texnik blog maqolalari (velog yoki Medium):
  1. "MongoDB'da ikki kishi bitta vaqtni band qilishining oldini olish"
  2. "Telemeditsina uchun WebRTC: signaling'dan TURN'gacha"
  3. "Tibbiy AI triage: xavfsiz LLM tizimini qanday qurdim"
- [ ] Rezyumeni yangilash (13-bo'lim)

---

## 9. Test strategiyasi

| Daraja | Vosita | Nimani tekshiradi | Qachon ishlaydi |
|---|---|---|---|
| Unit | Vitest | Holat mashinasi, shoshilinch filtr, utility'lar | Har bir commit (CI) |
| Integratsion | Supertest + mongodb-memory-server | API endpoint'lari, ruxsatlar, tranzaksiyalar | Har bir PR (CI) |
| Concurrency | Vitest + `Promise.all` | Bir slotni ikki marta band qilib bo'lmasligi | Har bir PR (CI) |
| E2E | Playwright | Bemorning to'liq oqimi brauzerda | Har bir PR yoki kechasi |
| Load | k6 | Yuklama ostida to'g'rilik va latency | Qo'lda, natija README'ga |
| AI baholash | O'z skriptingiz | Triage aniqligi (50 ta holat) | Prompt yoki model o'zgarganda |

---

## 10. Xavfsizlik ro'yxati

- [ ] Parollar bcrypt bilan (cost 12)
- [ ] Token'lar httpOnly, Secure, SameSite cookie'da; refresh token rotatsiyasi
- [ ] Barcha kiruvchi ma'lumotlar Zod bilan validatsiya qilinadi
- [ ] Har bir endpoint'da rol va **egalik** tekshiruvi (bemor faqat o'z qabulini ko'radi: IDOR himoyasi)
- [ ] Rate limit: login, triage, band qilish
- [ ] helmet, CORS faqat frontend domeni uchun
- [ ] MongoDB so'rov injeksiyasidan himoya (`express-mongo-sanitize` yoki strict Zod)
- [ ] Fayl yuklashda tur va hajm cheklovi
- [ ] Maxfiy kalitlar faqat env'da, `.env` gitignore'da, `.env.example` repoda
- [ ] Audit log: tibbiy yozuvlarga har bir kirish yoziladi
- [ ] Loglarda shaxsiy ma'lumotlar (parol, token, simptom matni) yozilmaydi
- [ ] Socket xonalariga faqat ruxsat etilgan foydalanuvchilar kiradi
- [ ] Faqat sintetik ma'lumotlar, haqiqiy bemor ma'lumotlari yo'q

### `.env.example`
```
# API
NODE_ENV=development
PORT=4000
MONGODB_URI=mongodb://localhost:27017/telemed?replicaSet=rs0
REDIS_URL=redis://localhost:6379
JWT_ACCESS_SECRET=
JWT_REFRESH_SECRET=
CLIENT_URL=http://localhost:3000
LLM_API_KEY=
EMBEDDING_API_KEY=
TOSS_SECRET_KEY=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
TURN_URL=
TURN_USERNAME=
TURN_CREDENTIAL=
SENTRY_DSN=

# Web
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_SOCKET_URL=http://localhost:4000
NEXT_PUBLIC_TOSS_CLIENT_KEY=
```

---

## 11. Deploy

```
GitHub (main) ──► GitHub Actions ──┬──► lint, typecheck, test
                                   ├──► Vercel  (apps/web)
                                   └──► Render  (apps/api, Docker)
                                            │
                       MongoDB Atlas ◄──────┼──────► Upstash Redis
                                            └──────► Sentry
```

- Frontend Vercel'da, backend alohida serverda, chunki Socket.io doimiy ulanish talab qiladi
- Bepul tariflarda server "uxlab qolishi" mumkin, demo oldidan uyg'otib qo'ying yoki kichik pullik tarif oling
- Production'da `NODE_ENV=production`, Sentry yoqilgan, loglar JSON formatda

---

## 12. README va portfolio

### README tuzilmasi
```
# Telemed: AI Triage bilan telemeditsina platformasi

[Demo havola] [Demo video] [Swagger]

## Muammo
Bemorlar qaysi bo'lim shifokoriga borishni bilmaydi; ...

## Asosiy funksiyalar (GIF'lar bilan)

## Arxitektura (diagramma)

## Texnik qiyinchiliklar va yechimlar
1. Ikki kishi bitta vaqtni band qilishi → atomik update + tranzaksiya
   Natija: 100 ta parallel so'rov → 1 muvaffaqiyatli, 99 ta 409, p95 = __ ms
2. To'lovning ikki marta yechilishi → idempotency key
3. NAT ortidagi video → TURN server, qayta ulanish
4. AI xavfsizligi → shoshilinch filtr, Zod validatsiya, baholash: accuracy __%

## Stack

## Lokal ishga tushirish
docker compose up -d && pnpm install && pnpm dev

## Testlar va qamrov

## Nimani o'rgandim / keyingi qadamlar
```

### Rezyume uchun namuna
> **Telemed: AI triage bilan telemeditsina platformasi** (Next.js, Node.js, MongoDB, Redis, WebRTC, LLM)
> - Atomik update va MongoDB tranzaksiyalari bilan bir vaqtni ikki marta band qilishning oldini oldim; 100 ta parallel so'rovda 0 ta takroriy band qilish (k6 bilan tekshirildi)
> - RAG asosidagi simptom triage tizimini qurdim, 50 ta test holatida __% aniqlik, shoshilinch holatlar uchun alohida xavfsizlik filtri
> - Socket.io signaling va TURN bilan WebRTC video konsultatsiyani amalga oshirdim
> - GitHub Actions bilan CI/CD, Playwright E2E testlar, Sentry monitoringi

---

## 13. Loyiha tugagandan keyin

- **Real foydalanuvchilar:** do'stlar va tanishlarga shifokor va bemor rolida sinab ko'rishni so'rang, fikrlarini yig'ing
- **Blog maqolalari:** 9-haftadagi uchta mavzu
- **Ish e'lonlariga topshirish:** Wanted, Jumpit, Rocketpunch, LinkedIn. Healthtech (Doctor Now, Lunit, Vuno) va B2B SaaS kompaniyalarini birinchi o'ringa qo'ying
- **Intervyuga tayyorgarlik:** README'dagi har bir "texnik qiyinchilik"ni 2 daqiqada tushuntira olishni mashq qiling (Muammo → Variantlar → Tanlov → Natija)
- **Keyingi versiya g'oyalari:** React Native mobil ilova, koreys tibbiy datasetida o'z klassifikatoringizni o'rgatish, ko'p shifokorli klinika rejimi (multi-tenant)

---

## 14. Yakuniy tekshiruv ro'yxati

- [ ] Demo havola ishlaydi, demo akkauntlar bilan kirish mumkin
- [ ] Bemorning to'liq oqimi: ro'yxatdan o'tish → triage → band qilish → to'lov → video → retsept → sharh
- [ ] Shifokor va admin oqimlari ishlaydi
- [ ] CI yashil, testlar o'tadi, qamrov ko'rsatilgan
- [ ] Load test natijalari README'da
- [ ] AI baholash natijalari README'da
- [ ] Arxitektura diagrammasi, ERD, demo video
- [ ] `.env.example`, lokal ishga tushirish yo'riqnomasi
- [ ] Kamida 1 ta blog maqola
- [ ] Rezyume yangilangan
