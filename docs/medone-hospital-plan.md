# MedOne Clinic: telemeditsina loyihasi ustiga qurilgan shifoxona veb-sayti

> **Asos:** [telemed-4day-plan.md](./telemed-4day-plan.md) va [telemed-project-plan.md](./telemed-project-plan.md)
> **Bozor:** O'zbekiston
> **Tillar:** o'zbek (lotin), rus, ingliz, koreys
> **Format:** faqat veb-sayt (Telegram bot yo'q)
> **Muddat:** 7 kun, kuniga 10–12 soat
> **Nom:** "MedOne Clinic" vaqtinchalik nom. U bitta konfiguratsiya faylida turadi va istalgan payt o'zgartiriladi.

---

## Mundarija

1. [G'oya](#1-goya)
2. [Avvalgi loyihadan nima olinadi, nima qo'shiladi](#2-avvalgi-loyihadan-nima-olinadi-nima-qoshiladi)
3. [Sayt xaritasi](#3-sayt-xaritasi)
4. [Rollar](#4-rollar)
5. [Stack](#5-stack)
6. [Papka tuzilmasi](#6-papka-tuzilmasi)
7. [Ma'lumotlar modellari](#7-malumotlar-modellari)
8. [API](#8-api)
9. [O'zbekistonga xos qismlar](#9-ozbekistonga-xos-qismlar)
10. [Kunma-kun reja](#10-kunma-kun-reja)
11. [Vaqt yetmasa: qisqartirish tartibi](#11-vaqt-yetmasa-qisqartirish-tartibi)
12. [Qonuniy eslatmalar](#12-qonuniy-eslatmalar)
13. [MVP'dan keyin](#13-mvpdan-keyin)
14. [Yakuniy tekshiruv ro'yxati](#14-yakuniy-tekshiruv-royxati)

---

## 1. G'oya

Telemeditsina loyihasi endi **mustaqil ilova emas**, balki **bitta klinikaning to'liq veb-sayti ichidagi bo'lim** bo'ladi.

- **Ochiq qism:** klinika haqida ma'lumot, bo'limlar, shifokorlar, narxlar, check-up paketlari, yangiliklar, aloqa
- **Onlayn yozilish:** klinikaga kelib ko'rinish yoki video konsultatsiya
- **AI yordamchi:** "Qaysi shifokorga borishim kerak?"
- **Shaxsiy kabinet:** qabullar, retseptlar, tahlil natijalari
- **Boshqaruv paneli:** admin saytni to'liq boshqaradi, operator bemorlarni yozib qo'yadi, shifokor qabullarni olib boradi

Brend, logotip, rasmlar va matnlar **o'zimizniki**. Boshqa klinikalarning (masalan, AKFA Medline) faqat umumiy tuzilishi ilhom uchun olinadi.

---

## 2. Avvalgi loyihadan nima olinadi, nima qo'shiladi

### Avvalgi loyihadan o'zgarishsiz olinadi
| Qism | Izoh |
|---|---|
| Express + Mongoose + Zod backend skeleti | Xato middleware, validatsiya, rol tekshiruvi |
| Slot modeli va **atomik band qilish** | `findOneAndUpdate` + concurrency testi |
| Appointment holat mashinasi | `canTransition(from, to)` |
| **Idempotency + MongoDB tranzaksiyasi** | To'lov tasdiqlashda |
| **AI triage + shoshilinch holat filtri** | Prompt va kalit so'zlar 4 tilga kengaytiriladi |
| Socket.io signaling + WebRTC video + chat | O'zgarishsiz |
| Retsept va sharhlar | Sharhlarga moderatsiya qo'shiladi |

### Avvalgi loyihada o'zgartiriladi
| Avval | Endi | Sabab |
|---|---|---|
| E-mail + parol bilan kirish | **Telefon + SMS kod** (Eskiz.uz) | O'zbekistonda asosiy kirish usuli |
| Ko'p mustaqil shifokorlar | **Bitta klinika**, shifokorlar bo'limlarga biriktirilgan | Shifoxona modeli |
| Shifokor o'zi ro'yxatdan o'tadi, admin tasdiqlaydi | **Admin shifokorni o'zi qo'shadi** | Klinika xodimlari |
| Faqat video qabul | `type: 'CLINIC' \| 'ONLINE'` | Klinikada va onlayn qabul |
| Mock to'lov | **Payme va Click (sandbox)** | Mahalliy to'lov tizimlari |
| Faqat ingliz tili | **uz, ru, en, ko** | O'zbekiston va koreys auditoriyasi |
| Narx `price` | **So'mda**, xizmatga bog'langan | Xizmatlar va narxlar sahifasi |

### Yangi qo'shiladi
| Qism | Vazifasi |
|---|---|
| **Department** | Bo'limlar sahifasi |
| **Service** | Xizmatlar va narxlar |
| **CheckupPackage** | Check-up dasturlari |
| **Article** | Yangiliklar va maqolalar |
| **LabResult** | Tahlil natijalari (PDF) |
| **Notification** | Sayt ichidagi bildirishnomalar + SMS |
| **Setting** | Klinika nomi, logotip, telefon, manzil, ish vaqti, ijtimoiy tarmoqlar |
| **ContactRequest** | "Qayta qo'ng'iroq qiling" formasi |
| **Operator roli** | Qabulxona xodimi |
| **Admin CMS** | Yuqoridagilarning hammasini sayt orqali boshqarish |

---

## 3. Sayt xaritasi

```
/[locale]                          ← uz | ru | en | ko
│
├── /                              Bosh sahifa: banner, bo'limlar, shifokorlar, check-up, statistika, sharhlar, yangiliklar
├── /departments                   Bo'limlar ro'yxati
├── /departments/[slug]            Bo'lim sahifasi: tavsif, xizmatlar, shifokorlar
├── /doctors                       Shifokorlar (filtr: bo'lim, til, onlayn qabul bor/yo'q)
├── /doctors/[slug]                Shifokor: tajriba, ta'lim, tillar, narx, bo'sh vaqtlar, sharhlar
├── /services                      Xizmatlar va narxlar (qidiruv, bo'lim bo'yicha guruhlangan)
├── /checkups                      Check-up paketlari
├── /checkups/[slug]               Paket tarkibi va narxi
├── /news                          Yangiliklar va maqolalar
├── /news/[slug]
├── /about                         Klinika haqida, uskunalar, litsenziyalar
├── /contacts                      Manzil, Yandex xarita, telefonlar, ish vaqti, "qayta qo'ng'iroq" formasi
├── /privacy, /offer               Maxfiylik siyosati, ommaviy oferta
│
├── /ai-assistant                  AI yordamchi: "Qaysi shifokorga borishim kerak?"
├── /booking                       Onlayn yozilish: tur → bo'lim → shifokor → vaqt → tasdiqlash → to'lov
├── /login                         Telefon raqam → SMS kod
│
├── /cabinet                       Shaxsiy kabinet (PATIENT)
│   ├── /appointments              Qabullarim
│   ├── /prescriptions             Retseptlarim
│   ├── /lab-results               Tahlil natijalarim
│   └── /profile
│
├── /call/[appointmentId]          Video konsultatsiya xonasi
│
├── /doctor                        Shifokor paneli: bugungi qabullar, jadval, retsept yozish
├── /operator                      Operator paneli: bemorni yozib qo'yish, kunlik jadval, qayta qo'ng'iroq so'rovlari
└── /admin                         Admin CMS
    ├── /dashboard                 Hisobotlar
    ├── /departments, /doctors, /services, /checkups, /news
    ├── /schedules                 Shifokor jadvallari
    ├── /lab-results               Natija yuklash
    ├── /reviews                   Sharhlarni moderatsiya qilish
    ├── /users
    └── /settings                  Klinika ma'lumotlari
```

---

## 4. Rollar

| Rol | Nima qila oladi |
|---|---|
| **PATIENT** (bemor) | Yozilish, to'lov, video qabul, retsept va natijalarni ko'rish, sharh yozish |
| **DOCTOR** (shifokor) | O'z qabullari, video qabul, xulosa va retsept yozish, o'z jadvalini ko'rish |
| **OPERATOR** (qabulxona) | Telefon orqali murojaat qilgan bemorni yozib qo'yish, qabulni ko'chirish yoki bekor qilish, qayta qo'ng'iroq so'rovlari bilan ishlash |
| **ADMIN** | Hamma narsa: kontent (CMS), shifokorlar, jadvallar, natijalar yuklash, sharhlar, foydalanuvchilar, hisobotlar, sozlamalar |

---

## 5. Stack

| Qism | Texnologiya |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui, React Query |
| Ko'p tillilik | **next-intl** (`uz`, `ru`, `en`, `ko`), kontent ham 4 tilda saqlanadi |
| Backend | Node.js + Express, TypeScript, Mongoose, Zod, JWT (httpOnly cookie) |
| Real-time | Socket.io (signaling, chat, bildirishnomalar), WebRTC (`simple-peer`) |
| Ma'lumotlar bazasi | MongoDB (demo: Atlas M0; haqiqiy klinika: O'zbekistondagi server) |
| SMS | **Eskiz.uz** API (kirish kodi, eslatmalar) |
| To'lov | **Payme** va **Click** (sandbox rejimi) |
| Fayllar | Lokal disk yoki S3-mos saqlash (shifokor rasmlari, tahlil PDF'lari) |
| Xarita | **Yandex Maps** (embed) |
| AI | LLM API (JSON javob) + qoidaga asoslangan shoshilinch filtr |
| Matn muharriri (CMS) | Tiptap yoki oddiy Markdown muharriri |
| Analitika | Yandex Metrica + Google Analytics |
| Test | Vitest + Supertest + mongodb-memory-server |
| Deploy (demo) | Vercel (web) + Render (api) + Atlas |

### Ko'p tilli kontent qanday saqlanadi
```ts
// Har bir tarjima qilinadigan maydon shunday ko'rinishda bo'ladi:
type I18nText = { uz: string; ru: string; en: string; ko: string };

// Misol:
name: { uz: "Kardiologiya", ru: "Кардиология", en: "Cardiology", ko: "심장내과" }
```
Admin CMS'da har bir maydon uchun 4 ta tab bo'ladi. Tarjima yo'q bo'lsa, `uz` ko'rsatiladi.

---

## 6. Papka tuzilmasi

Avvalgi `api/` va `web/` tuzilmasi kengaytiriladi (**yangi** deb belgilanganlar qo'shiladi):

```
medone/
├── api/
│   ├── src/
│   │   ├── config/                 # env, db, clinic.ts (yangi: nom, logotip, aloqa)
│   │   ├── models/
│   │   │   ├── User.ts             # o'zgaradi: phone asosiy, OPERATOR roli
│   │   │   ├── Doctor.ts           # o'zgaradi: departmentId, slug, i18n maydonlar
│   │   │   ├── Slot.ts
│   │   │   ├── Appointment.ts      # o'zgaradi: type CLINIC|ONLINE, serviceId, createdBy
│   │   │   ├── Payment.ts          # o'zgaradi: provider PAYME|CLICK|CASH
│   │   │   ├── Prescription.ts
│   │   │   ├── Review.ts           # o'zgaradi: status PENDING|APPROVED|REJECTED
│   │   │   ├── Department.ts       # yangi
│   │   │   ├── Service.ts          # yangi
│   │   │   ├── CheckupPackage.ts   # yangi
│   │   │   ├── Article.ts          # yangi
│   │   │   ├── LabResult.ts        # yangi
│   │   │   ├── Notification.ts     # yangi
│   │   │   ├── ContactRequest.ts   # yangi
│   │   │   ├── Setting.ts          # yangi
│   │   │   └── OtpCode.ts          # yangi (TTL indeks bilan)
│   │   ├── routes/
│   │   │   ├── public/             # yangi: ochiq sayt uchun (departments, doctors, services, checkups, news, settings)
│   │   │   ├── auth.ts             # o'zgaradi: SMS orqali
│   │   │   ├── booking.ts
│   │   │   ├── payments/           # yangi: payme.ts, click.ts (webhook'lar)
│   │   │   ├── triage.ts
│   │   │   ├── cabinet.ts          # yangi
│   │   │   ├── doctor.ts
│   │   │   ├── operator.ts         # yangi
│   │   │   └── admin/              # yangi: CMS endpoint'lari
│   │   ├── services/
│   │   │   ├── booking.service.ts
│   │   │   ├── triage.service.ts
│   │   │   ├── sms.service.ts      # yangi: Eskiz
│   │   │   ├── notify.service.ts   # yangi: sayt ichida + SMS
│   │   │   └── reminder.service.ts # yangi: eslatmalar
│   │   ├── middlewares/
│   │   ├── socket.ts
│   │   ├── app.ts
│   │   └── server.ts
│   ├── uploads/                    # demo uchun fayllar
│   ├── tests/
│   ├── scripts/seed.ts             # kengaytiriladi: bo'limlar, xizmatlar, paketlar, yangiliklar
│   └── eval/triage-cases.json      # kengaytiriladi: 4 tilda
└── web/
    ├── app/[locale]/
    │   ├── (site)/                 # yangi: ochiq sayt sahifalari
    │   ├── (auth)/login
    │   ├── ai-assistant/
    │   ├── booking/
    │   ├── cabinet/
    │   ├── call/[id]/
    │   ├── doctor/
    │   ├── operator/               # yangi
    │   └── admin/                  # kengaytiriladi: CMS
    ├── components/
    │   ├── site/                   # yangi: Header, Footer, Hero, DepartmentCard, DoctorCard, PriceTable...
    │   └── admin/                  # yangi: I18nInput, DataTable, ImageUpload
    ├── messages/                   # uz.json, ru.json, en.json, ko.json
    └── lib/
```

---

## 7. Ma'lumotlar modellari

### O'zgaradigan modellar
```ts
// User
{ phone (unique), name, role: 'PATIENT'|'DOCTOR'|'OPERATOR'|'ADMIN',
  locale: 'uz'|'ru'|'en'|'ko', birthDate?, gender?, consentAt (rozilik vaqti) }

// Doctor
{ userId, departmentId, slug, photoUrl,
  fullName: I18nText, position: I18nText, bio: I18nText, education: I18nText,
  experienceYears, languages: ['uz','ru','en','ko'],
  consultationPrice (so'm), onlineAvailable: Boolean, isActive, ratingAvg, ratingCount }

// Appointment
{ patientId, doctorId, slotId (unique), serviceId?,
  type: 'CLINIC'|'ONLINE', symptomText?, triage?,
  status: 'PENDING'|'CONFIRMED'|'IN_PROGRESS'|'COMPLETED'|'CANCELLED'|'NO_SHOW',
  createdBy: 'PATIENT'|'OPERATOR', paymentMethod: 'ONLINE'|'AT_CLINIC' }

// Payment
{ appointmentId, amount, provider: 'PAYME'|'CLICK'|'CASH',
  providerTransactionId, status, idempotencyKey (unique) }

// Review
{ ..., status: 'PENDING'|'APPROVED'|'REJECTED' }
```

### Yangi modellar
```ts
// Department
{ slug, name: I18nText, description: I18nText, icon, imageUrl, order, isActive }

// Service
{ departmentId, name: I18nText, description: I18nText,
  price (so'm), durationMin, isActive }

// CheckupPackage
{ slug, name: I18nText, description: I18nText, serviceIds: [ObjectId],
  price, oldPrice, imageUrl, isActive }

// Article
{ slug, title: I18nText, excerpt: I18nText, content: I18nText,
  coverUrl, publishedAt, isPublished }

// LabResult
{ patientId, appointmentId?, title: I18nText, fileUrl, uploadedBy, createdAt }

// Notification
{ userId, type, title: I18nText, body: I18nText, read: Boolean, createdAt }

// ContactRequest
{ name, phone, message?, status: 'NEW'|'CALLED'|'CLOSED', handledBy?, createdAt }

// Setting (bitta hujjat)
{ clinicName, logoUrl, phones: [String], address: I18nText,
  workingHours: I18nText, mapEmbedUrl, socials: { instagram, facebook, youtube } }

// OtpCode
{ phone, codeHash, attempts, expiresAt }   // TTL indeks: expiresAt
```

### Appointment holat mashinasi (kengaytirilgan)
```
PENDING ──(to'lov yoki "klinikada to'layman")──► CONFIRMED ──► IN_PROGRESS ──► COMPLETED
   │                                                │
   └──(10 daqiqa, onlayn to'lov qilinmasa)──► CANCELLED ◄──(bekor qilindi)
                                                    │
                                                    └──(bemor kelmadi, operator belgilaydi)──► NO_SHOW
```

---

## 8. API

### Ochiq (autentifikatsiyasiz)
```
GET  /api/public/settings
GET  /api/public/departments
GET  /api/public/departments/:slug
GET  /api/public/doctors?department=&lang=&online=
GET  /api/public/doctors/:slug
GET  /api/public/doctors/:id/slots?date=
GET  /api/public/services?department=&q=
GET  /api/public/checkups, /api/public/checkups/:slug
GET  /api/public/news?page=, /api/public/news/:slug
GET  /api/public/reviews?doctorId=          (faqat APPROVED)
POST /api/public/contact-requests           (rate limit bilan)
```

### Auth (SMS)
```
POST /api/auth/otp/send       { phone }          → Eskiz orqali 6 xonali kod (1 daqiqada 1 marta, kuniga 5 marta)
POST /api/auth/otp/verify     { phone, code }    → JWT cookie; yangi bo'lsa ism va rozilik so'raladi
POST /api/auth/logout
GET  /api/auth/me
```

### Bemor
```
POST  /api/triage
POST  /api/appointments                  { slotId, type, serviceId?, paymentMethod }
PATCH /api/appointments/:id/cancel
GET   /api/cabinet/appointments
GET   /api/cabinet/prescriptions
GET   /api/cabinet/lab-results
GET   /api/cabinet/lab-results/:id/file  (faqat egasi)
POST  /api/reviews
GET   /api/notifications, PATCH /api/notifications/:id/read
```

### To'lov
```
POST /api/payments/payme/checkout       → Payme to'lov havolasi
POST /api/payments/payme/webhook        → Payme Merchant API (JSON-RPC)
POST /api/payments/click/checkout       → Click to'lov havolasi
POST /api/payments/click/prepare        → Click webhook
POST /api/payments/click/complete       → Click webhook
```
Webhook'larda imzo tekshiriladi, tranzaksiya va idempotency avvalgi loyihadagidek ishlaydi.

### Shifokor
```
GET  /api/doctor/appointments?date=
POST /api/consultations/:appointmentId/start | end
POST /api/prescriptions
```

### Operator
```
GET   /api/operator/schedule?date=&doctorId=
POST  /api/operator/patients              { phone, name }   (yangi bemor yoki mavjudini topish)
POST  /api/operator/appointments          (bemor nomidan yozish)
PATCH /api/operator/appointments/:id      (ko'chirish, bekor qilish, NO_SHOW)
GET   /api/operator/contact-requests
PATCH /api/operator/contact-requests/:id
```

### Admin (CMS)
```
CRUD /api/admin/departments | doctors | services | checkups | news
POST /api/admin/slots/bulk
POST /api/admin/lab-results              (PDF yuklash + bemorga bildirishnoma)
GET  /api/admin/reviews?status=PENDING, PATCH /api/admin/reviews/:id
GET  /api/admin/users, PATCH /api/admin/users/:id/role
GET  /api/admin/stats?from=&to=
GET  /api/admin/settings, PUT /api/admin/settings
POST /api/admin/uploads                  (rasm yuklash)
```

---

## 9. O'zbekistonga xos qismlar

| Qism | Qanday |
|---|---|
| **Telefon formati** | `+998 XX XXX XX XX`, input maskasi, backend'da `^\+998\d{9}$` |
| **SMS kod** | Eskiz.uz; kod bcrypt bilan hash qilinadi; 5 daqiqa amal qiladi; 5 ta noto'g'ri urinishdan keyin bloklanadi. Demo uchun `SMS_MODE=console` (kod logga chiqadi) |
| **SMS eslatmalar** | Qabuldan 1 kun va 2 soat oldin. Har 5 daqiqada ishlaydigan `setInterval` yoki `node-cron` vazifasi; `reminderSentAt` maydoni ikki marta yuborilmasligini ta'minlaydi |
| **To'lov** | Payme va Click sandbox. Klinikada qabul uchun "klinikada to'layman" varianti ham bor |
| **Narx formati** | `Intl.NumberFormat('uz-UZ')` → `250 000 so'm`; tilga qarab `сум`, `UZS`, `숨` |
| **Xarita** | Yandex Maps iframe (`Setting.mapEmbedUrl`) |
| **SEO** | Har bir til uchun alohida URL, `hreflang` teglari, `sitemap.xml`, `robots.txt`, Open Graph, `MedicalClinic` va `Physician` schema.org belgilari |
| **Sekin internet** | Next.js `Image`, lazy loading, video qo'ng'iroqda "faqat ovoz" tugmasi |
| **Keksa foydalanuvchilar** | Katta shrift va tugmalar, header'da doim ko'rinadigan "📞 Qo'ng'iroq qilish" tugmasi |
| **Koreys auditoriyasi** | `ko` tili, shifokor profilida "Koreys tilida gaplashadi" belgisi va shu bo'yicha filtr |

---

## 10. Kunma-kun reja

> Har kun oxirida: commit, push, ishlaydigan holat. "Tekshiruv" bandlari bajarilmaguncha keyingi kunga o'tilmaydi.

### 1-kun: Poydevor, SMS orqali kirish, rollar, asosiy modellar

| Vaqt | Vazifa |
|---|---|
| 1 soat | Repo, `api/` va `web/`, Atlas, `.env`, `clinic.ts` konfiguratsiyasi |
| 2 soat | Backend skeleti (avvalgi loyihadan): env, DB, xato middleware, `validate`, `requireAuth`, `requireRole` |
| 2.5 soat | **SMS orqali kirish:** OtpCode modeli (TTL), `sms.service.ts` (Eskiz + console rejimi), `otp/send`, `otp/verify`, rate limit, rozilik belgisi |
| 2.5 soat | Modellar: User, Department, Doctor, Service, CheckupPackage, Article, Setting, Slot, Appointment, Payment (4 tilli `I18nText` bilan) |
| 2 soat | `web/`: next-intl (4 til), shadcn/ui, asosiy layout (Header: logotip, menyu, til tanlagich, telefon, "Yozilish" tugmasi; Footer), login sahifasi (telefon → kod) |
| 1 soat | `seed.ts`: 8 ta bo'lim, 16 ta shifokor, 40 ta xizmat, 4 ta check-up, 6 ta yangilik, sozlamalar, admin, operator, 5 bemor |

**Tekshiruv:**
- [ ] Telefon va SMS kod bilan kirish ishlaydi (console rejimida)
- [ ] 4 til almashadi
- [ ] Seed ma'lumotlari bazada

---

### 2-kun: Ochiq sayt

| Vaqt | Vazifa |
|---|---|
| 1.5 soat | `/api/public/*` endpoint'lari (settings, departments, doctors, services, checkups, news, reviews) |
| 2.5 soat | **Bosh sahifa:** Hero (sarlavha + "Yozilish" + "AI yordamchi"), bo'limlar to'ri, mashhur shifokorlar, check-up paketlari, raqamlar (yillar, shifokorlar, bemorlar), sharhlar, yangiliklar |
| 2 soat | **Bo'limlar** ro'yxati va bo'lim sahifasi; **shifokorlar** ro'yxati (filtrlar: bo'lim, til, onlayn) va shifokor sahifasi |
| 1.5 soat | **Xizmatlar va narxlar** (qidiruv, bo'lim bo'yicha guruhlash), **check-up** sahifalari |
| 1.5 soat | **Yangiliklar**, **Biz haqimizda**, **Aloqa** (Yandex xarita, "qayta qo'ng'iroq" formasi), Maxfiylik siyosati, Oferta |
| 1 soat | SEO: `generateMetadata`, `hreflang`, `sitemap.xml`, `robots.txt`, schema.org. Mobil ko'rinishni tekshirish |

**Tekshiruv:**
- [ ] Barcha ochiq sahifalar 4 tilda ochiladi
- [ ] Telefonda chiroyli ko'rinadi
- [ ] "Qayta qo'ng'iroq" formasi bazaga yoziladi

---

### 3-kun: Onlayn yozilish va operator

| Vaqt | Vazifa |
|---|---|
| 1 soat | Admin: `POST /admin/slots/bulk` (avvalgi loyihadan), oddiy jadval yaratish sahifasi |
| 2.5 soat | **Band qilish** (avvalgi loyihadan): atomik `findOneAndUpdate`, holat mashinasi (`NO_SHOW` qo'shilgan), `type` va `paymentMethod` maydonlari, bekor qilish qoidalari |
| 1 soat | **Concurrency testi:** 50 ta parallel so'rov → 1 ta `201`, 49 ta `409` |
| 2.5 soat | **Yozilish sahifasi** (qadamma-qadam): qabul turi (klinika yoki video) → bo'lim → shifokor → sana va vaqt → tasdiqlash → to'lov usuli. Kirmagan bo'lsa, shu yerda SMS orqali kirish |
| 2 soat | **Operator paneli:** kunlik jadval (shifokorlar × vaqtlar), telefon bo'yicha bemorni topish yoki yaratish, bemor nomidan yozish, ko'chirish, bekor qilish, `NO_SHOW`; qayta qo'ng'iroq so'rovlari ro'yxati |
| 1 soat | Testlar: operator yozishi, ruxsatlar (bemor operator endpoint'iga kira olmaydi) |

**Tekshiruv:**
- [ ] Bemor saytdan yozila oladi (klinika va video)
- [ ] Operator bemor nomidan yoza oladi
- [ ] Concurrency testi o'tadi

---

### 4-kun: To'lov va AI yordamchi

| Vaqt | Vazifa |
|---|---|
| 3 soat | **Payme** (sandbox): checkout havolasi, Merchant API webhook (`CheckPerformTransaction`, `CreateTransaction`, `PerformTransaction`, `CancelTransaction`, `CheckTransaction`), imzo tekshiruvi, tranzaksiya + idempotency |
| 2 soat | **Click** (sandbox): checkout havolasi, `prepare` va `complete` webhook'lari, imzo tekshiruvi |
| 1 soat | To'lov natijasi sahifalari, "klinikada to'layman" oqimi, idempotency testi |
| 2 soat | **AI yordamchi backend** (avvalgi loyihadan): shoshilinch filtr (uz, ru, en, ko kalit so'zlar), LLM prompt'iga **klinikaning haqiqiy bo'limlari ro'yxati** beriladi, Zod validatsiya, fallback (Terapiya), rate limit |
| 2 soat | **AI yordamchi sahifasi:** simptom formasi, natija (bo'lim + foiz + shu bo'lim shifokorlari + "Yozilish" tugmasi), shoshilinch holat ekrani (**103** tez yordam), "Bu tashxis emas" ogohlantirishi. `eval/triage-cases.json`: 4 tilda 24 ta holat va accuracy skripti |

**Tekshiruv:**
- [ ] Payme va Click sandbox'da to'lov o'tadi, qabul `CONFIRMED` bo'ladi
- [ ] Bir xil webhook ikki marta kelsa, ikki marta yozilmaydi
- [ ] AI 4 tilda ishlaydi, shoshilinch matnlar LLM'ga yuborilmaydi

---

### 5-kun: Video qabul, retsept, tahlil natijalari

| Vaqt | Vazifa |
|---|---|
| 3 soat | **Video qo'ng'iroq** (avvalgi loyihadan): Socket autentifikatsiyasi, xona ruxsati (faqat `ONLINE` qabul, faqat shu bemor va shifokor), `simple-peer`, STUN + TURN, mikrofon va kamera tugmalari, **"faqat ovoz" rejimi** |
| 1 soat | Chat, shifokor uchun "boshlash" va "tugatish" |
| 2 soat | **Shifokor paneli:** bugungi qabullar (klinika va onlayn), bemor tarixi (oldingi qabullar va retseptlar), "qo'ng'iroqqa kirish", xulosa va **retsept** yozish |
| 2 soat | **Tahlil natijalari:** admin PDF yuklaydi (tur va hajm tekshiruvi), bemorga bildirishnoma; bemor kabinetida ko'rish va yuklab olish (faqat egasi) |
| 1.5 soat | **Shaxsiy kabinet:** qabullarim (kelgusi va o'tgan, bekor qilish), retseptlarim (chop etish), natijalarim, profil |
| 0.5 soat | Ikki qurilmada video qo'ng'iroqni sinash |

**Tekshiruv:**
- [ ] Ikki qurilmada video, ovoz va chat ishlaydi
- [ ] Shifokor retsept yozadi, bemor kabinetda ko'radi
- [ ] Bemor faqat o'z natijalarini yuklab oladi

---

### 6-kun: Admin CMS, bildirishnomalar, hisobotlar

| Vaqt | Vazifa |
|---|---|
| 1.5 soat | **CMS komponentlari:** `I18nInput` (4 tab), `DataTable` (qidiruv, sahifalash), `ImageUpload`, matn muharriri |
| 3 soat | **CMS sahifalari:** bo'limlar, shifokorlar (foydalanuvchi akkaunti bilan), xizmatlar, check-up paketlari, yangiliklar, sozlamalar |
| 1 soat | **Sharhlar moderatsiyasi**, foydalanuvchilar va rollar |
| 2 soat | **Bildirishnomalar:** `notify.service.ts` (sayt ichida, Socket.io orqali real-time + SMS); hodisalar: qabul tasdiqlandi, bekor qilindi, natija tayyor, retsept tayyor. **SMS eslatmalar** (1 kun va 2 soat oldin) |
| 1.5 soat | **Hisobotlar** (MongoDB aggregation): bugungi va oylik qabullar, daromad, klinika va onlayn nisbati, eng band shifokorlar, `NO_SHOW` foizi, yangi bemorlar |
| 1 soat | Sharh yozish (faqat `COMPLETED` qabuldan keyin), reyting hisoblash |

**Tekshiruv:**
- [ ] Admin saytdagi har qanday kontentni 4 tilda o'zgartira oladi va o'zgarish ochiq saytda ko'rinadi
- [ ] Bildirishnomalar real-time keladi, eslatmalar ikki marta yuborilmaydi
- [ ] Hisobotlar to'g'ri raqam ko'rsatadi

---

### 7-kun: Testlar, xavfsizlik, deploy, hujjatlar

| Vaqt | Vazifa |
|---|---|
| 2 soat | **Testlar:** SMS kirish (urinishlar limiti), ruxsatlar (IDOR: boshqa bemorning qabuli, retsepti, natijasi), Payme va Click webhook imzosi, holat mashinasi, operator ruxsatlari. GitHub Actions |
| 1 soat | **Xavfsizlik:** helmet, CORS, rate limit (OTP, AI, kontakt formasi), fayl yuklash cheklovlari, loglarda telefon raqam va kodlar yo'qligi, `.env.example` |
| 2.5 soat | **Deploy:** Render (api, WebSocket), Vercel (web), Atlas, production seed, demo akkauntlar (har bir rol uchun), Payme va Click sandbox webhook URL'lari. Productionda to'liq oqimni sinash |
| 1 soat | Lighthouse (mobil): tezlik, accessibility, SEO; topilgan xatolarni tuzatish |
| 2 soat | **README** (ingliz va koreys tillarida): muammo, funksiyalar, skrinshotlar, arxitektura diagrammasi, texnik qiyinchiliklar (concurrency, idempotency, webhook xavfsizligi, WebRTC, AI xavfsizligi, 4 tilli CMS), stack, lokal ishga tushirish, demo akkauntlar |
| 1.5 soat | **Demo video** (3 daqiqa): ochiq sayt → AI yordamchi → yozilish va to'lov → video qabul → retsept → admin CMS → hisobotlar. Rezyumeni yangilash |

**Tekshiruv:** 14-bo'limdagi yakuniy ro'yxat.

---

## 11. Vaqt yetmasa: qisqartirish tartibi

Yuqoridagisini birinchi olib tashlang:

1. Yangiliklar va "Biz haqimizda" sahifalari (statik matn bilan almashtirish)
2. Hisobotlar (faqat 3–4 ta raqam qoldirish)
3. Click (faqat Payme qoldirish)
4. Sharhlar moderatsiyasi (sharhlar ham keyinga)
5. Check-up paketlari
6. Koreys va ingliz tilidagi kontent (interfeys 4 tilda qoladi, kontent faqat uz va ru)

**Olib tashlamang:** SMS orqali kirish, concurrency himoyasi, to'lovda idempotency va webhook imzosi, AI'dagi shoshilinch filtr, ruxsat tekshiruvlari (IDOR), video qabul, admin CMS'ning asosiy qismi, deploy, README.

---

## 12. Qonuniy eslatmalar

> Portfolio va demo uchun quyidagilar majburiy emas, lekin **haqiqiy klinikaga joriy qilishdan oldin** albatta hal qilinishi kerak. Qonunlar o'zgarib turadi, amaldagi talablarni yurist bilan tekshiring.

| Masala | Izoh |
|---|---|
| **Ma'lumotlar lokalizatsiyasi** | O'zbekiston fuqarolarining shaxsiy ma'lumotlari O'zbekiston hududidagi serverlarda saqlanishi talab qilinadi. Haqiqiy klinika uchun mahalliy hosting (UzCloud, Uztelecom va boshqalar) kerak |
| **Rozilik** | Shaxsiy ma'lumotlarni qayta ishlashga rozilik belgisi va uning vaqti (`consentAt`) saqlanadi |
| **Maxfiylik siyosati va ommaviy oferta** | Saytda alohida sahifalar; onlayn to'lov uchun oferta zarur |
| **To'lov tizimlari** | Payme va Click merchant akkaunti faqat yuridik shaxs yoki YaTT uchun. Demo'da sandbox ishlatiladi |
| **Telemeditsina** | Masofaviy tibbiy xizmatlar Sog'liqni saqlash vazirligi talablariga mos bo'lishi kerak |
| **Brend** | Boshqa klinikalarning nomi, logotipi, rasmlari va matnlaridan foydalanilmaydi |
| **Demo ma'lumotlari** | Faqat sintetik ma'lumotlar; haqiqiy bemor ma'lumotlari yo'q |

---

## 13. MVP'dan keyin

| # | Qo'shimcha | Foydasi |
|---|---|---|
| 1 | RAG asosidagi AI yordamchi va 50 ta holatda baholash | Kuchliroq AI |
| 2 | Playwright E2E va k6 load test | Sifatni raqamlar bilan isbotlash |
| 3 | Uzum to'lovi | Yana bir mashhur to'lov usuli |
| 4 | Mahalliy serverga deploy (Docker) | Qonun talablariga moslik |
| 5 | Multi-tenant: bitta tizim, ko'p klinika, har biri o'z domeni va dizayni bilan | SaaS sifatida sotish |
| 6 | Klinikaning MIS tizimi bilan integratsiya | Katta klinikalar uchun |
| 7 | Elektron navbat (klinika ichidagi ekran) | Klinikaga qo'shimcha qiymat |
| 8 | Sentry, o'z domeningiz (`.uz`), Yandex Metrica | Production darajasi |

### Biznes sifatida
- **Pilot:** bitta kichik xususiy klinikaga bepul yoki arzon joriy qilish, evaziga tavsiya va real foydalanish ma'lumotlari
- **Model:** oylik to'lov (hosting, yangilanish va qo'llab-quvvatlash ichida)
- **Paketlar:** Oddiy (sayt + yozilish) → O'rta (+ SMS eslatmalar + operator) → To'liq (+ telemeditsina + AI + natijalar)

### Rezyume uchun namuna
> **MedOne Clinic: 4 tilli shifoxona platformasi** (Next.js, Node.js, MongoDB, Socket.io, WebRTC, LLM)
> - Ochiq sayt, 4 tilli CMS, onlayn yozilish, telemeditsina va AI yordamchidan iborat shifoxona platformasini noldan qurdim va deploy qildim
> - Atomik update va MongoDB tranzaksiyalari bilan bir vaqtni ikki marta band qilishning oldini oldim (50 ta parallel so'rovda 0 ta takroriy band qilish)
> - Payme va Click to'lovlarini imzo tekshiruvi va idempotency bilan integratsiya qildim
> - Shoshilinch holat filtri bilan 4 tilli AI triage qurdim, 24 ta holatda __% aniqlik
> - SMS eslatmalar orqali kelmay qolish holatlarini kamaytirish mexanizmini joriy qildim

---

## 14. Yakuniy tekshiruv ro'yxati

- [ ] Demo havola ishlaydi; bemor, shifokor, operator va admin demo akkauntlari bor
- [ ] Ochiq sayt 4 tilda, mobil ko'rinishi yaxshi, Lighthouse natijalari qoniqarli
- [ ] Bemor oqimi: AI yordamchi → yozilish → to'lov (sandbox) → video qabul → retsept → natija → sharh
- [ ] Operator bemor nomidan yozadi, ko'chiradi, `NO_SHOW` belgilaydi
- [ ] Admin kontentni 4 tilda boshqaradi, natija yuklaydi, sharhlarni moderatsiya qiladi, hisobotlarni ko'radi
- [ ] Concurrency, idempotency, webhook imzosi va IDOR testlari o'tadi, CI yashil
- [ ] README ingliz va koreys tillarida: arxitektura, raqamlar, skrinshotlar, demo video
- [ ] Rezyume yangilangan
