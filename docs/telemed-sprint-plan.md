# Telemeditsina ilovasi: 2–3 kunlik bosqichlarga bo'lingan ish rejasi

> **Asos:** [telemed-project-plan.md](./telemed-project-plan.md)
> **Jami:** 70 kun, 30 ta bosqich (har biri 2–3 kun), kuniga 3–4 soat.
> **Qoida:** har bir bosqich oxirida ishlaydigan natija bo'ladi va GitHub'ga push qilinadi (PR → CI yashil → merge).

---

## Kunlik ish tartibi

1. **10 daqiqa:** bugungi vazifani GitHub Projects'da "In Progress" ga o'tkazish
2. **3 soat:** kod yozish (yangi branch'da)
3. **20 daqiqa:** test yozish yoki ishga tushirish
4. **10 daqiqa:** commit, push, ertangi kun uchun qisqa eslatma

Bosqich tugaganda PR ochiladi, CI yashil bo'lsa `main` ga merge qilinadi.

---

## Umumiy ko'rinish

| Hafta | Kunlar | Bosqichlar | Mavzu |
|---|---|---|---|
| 0 | 1–7 | 1–3 | Tayyorgarlik va loyihalash |
| 1 | 8–14 | 4–6 | Poydevor va autentifikatsiya |
| 2 | 15–21 | 7–9 | Shifokorlar va ish jadvali |
| 3 | 22–28 | 10–12 | Band qilish va to'lov |
| 4 | 29–35 | 13–15 | AI triage |
| 5 | 36–42 | 16–18 | Video konsultatsiya va chat |
| 6 | 43–49 | 19–21 | Retsept, bildirishnomalar, sharhlar, admin |
| 7 | 50–56 | 22–24 | Testlar, xavfsizlik, sifat |
| 8 | 57–63 | 25–27 | Deploy va CI/CD |
| 9 | 64–70 | 28–30 | Hujjatlar, portfolio, ishga topshirish |

---

## 0-hafta: Tayyorgarlik va loyihalash

### Bosqich 1 · Kun 1–2 · Muhit va akkauntlar
- [ ] Node.js 22, pnpm, Docker Desktop, Git, VS Code (ESLint, Prettier, Tailwind kengaytmalari)
- [ ] Akkauntlar: GitHub, MongoDB Atlas, Vercel, Render, Upstash, Sentry, Toss Payments developers, LLM API
- [ ] GitHub'da `telemed` reposi, `main` branch himoyasi (faqat PR orqali)
- [ ] GitHub Projects doskasi: `Backlog / Todo / In Progress / Done` ustunlari
- [ ] Shu rejadagi 30 ta bosqichni Issue sifatida yaratish

**Natija:** barcha vositalar o'rnatilgan, repo va doska tayyor.

### Bosqich 2 · Kun 3–4 · Talablar va wireframe'lar
- [ ] Har bir rol uchun 5–8 ta user story (`docs/user-stories.md`)
- [ ] MVP'ga kiradigan va kirmaydigan narsalar ro'yxatini yakunlash
- [ ] Wireframe'lar (Figma yoki qog'oz): bosh sahifa, login, triage, shifokorlar ro'yxati, shifokor sahifasi, band qilish, to'lov, video xona, retsept, shifokor paneli, admin paneli
- [ ] Ranglar va shrift tanlash (shadcn/ui mavzusi)

**Natija:** `docs/wireframes/` va `docs/user-stories.md`.

### Bosqich 3 · Kun 5–7 · ERD va API spetsifikatsiyasi
- [ ] ERD (dbdiagram.io): users, doctors, slots, appointments, payments, consultations, prescriptions, reviews, triage_knowledge, audit_logs, notifications
- [ ] Indekslar ro'yxati
- [ ] API ro'yxati va xato kodlari (`docs/api.md`)
- [ ] Appointment holat mashinasi diagrammasi
- [ ] Arxitektura diagrammasining birinchi varianti (Excalidraw)

**Natija:** `docs/` papkasi to'liq, kod yozishga tayyor.

---

## 1-hafta: Poydevor va autentifikatsiya

### Bosqich 4 · Kun 8–9 · Monorepo va lokal muhit
- [ ] pnpm workspaces, Turborepo (`turbo.json`: `dev`, `build`, `lint`, `test`, `typecheck`)
- [ ] `apps/web` (create-next-app), `apps/api`, `packages/shared`
- [ ] ESLint, Prettier, Husky + lint-staged, umumiy `tsconfig.base.json`
- [ ] `docker-compose.yml`: MongoDB (replica set yoki `mongodb-atlas-local`), Redis
- [ ] `.env.example`, `.gitignore`
- [ ] `pnpm dev` bitta buyruq bilan web va api'ni ishga tushiradi

**Natija:** `docker compose up -d && pnpm dev` ishlaydi.

### Bosqich 5 · Kun 10–12 · Backend skeleti va auth API
- [ ] Express ilovasi: `app.ts`, `server.ts`, helmet, cors, cookie-parser, JSON limit
- [ ] `config/env.ts` (Zod bilan tekshiruv), `config/db.ts`, `config/redis.ts`
- [ ] pino logger, `AppError` klassi, markaziy xato middleware, `/api/health`
- [ ] `packages/shared`: `Role`, `Department` enum'lari, `registerSchema`, `loginSchema`
- [ ] User modeli
- [ ] `register`, `login`, `refresh` (rotatsiya bilan), `logout`, `me`
- [ ] Middleware'lar: `requireAuth`, `requireRole`, `validate`
- [ ] Rate limit (login uchun)
- [ ] Vitest + Supertest + mongodb-memory-server sozlash, auth uchun integratsion testlar

**Natija:** auth API Postman yoki testlar orqali to'liq ishlaydi.

### Bosqich 6 · Kun 13–14 · Frontend auth va CI
- [ ] shadcn/ui o'rnatish, asosiy layout (header, til tanlagich)
- [ ] next-intl: `ko`, `en`, `uz` (`messages/*.json`)
- [ ] API klienti (fetch wrapper, cookie bilan, 401 bo'lsa avtomatik refresh)
- [ ] React Query provider, `useAuth` hook, Zustand store
- [ ] Login va register sahifalari (React Hook Form + Zod)
- [ ] Next.js middleware: himoyalangan sahifalar va rolga qarab yo'naltirish
- [ ] GitHub Actions `ci.yml`: install → lint → typecheck → test

**Natija:** foydalanuvchi ro'yxatdan o'tadi, kiradi, roliga mos panelga tushadi. CI yashil. ✅ **1-hafta tugadi**

---

## 2-hafta: Shifokorlar va ish jadvali

### Bosqich 7 · Kun 15–16 · Shifokor profili va litsenziya
- [ ] Doctor modeli va indekslar
- [ ] `POST /doctors/profile`, `GET /doctors/:id`
- [ ] Litsenziya yuklash: multer, fayl turi (pdf, jpg, png) va hajmi (5 MB) cheklovi, S3 yoki Cloudinary
- [ ] Frontend: shifokor profilini to'ldirish sahifasi, "tasdiqlash kutilmoqda" holati
- [ ] Testlar: faqat DOCTOR roli profil yarata oladi

**Natija:** shifokor profil yaratib, litsenziya yuklaydi.

### Bosqich 8 · Kun 17–18 · Admin tasdiqlash va slotlar
- [ ] Admin: `GET /admin/doctors?status=PENDING`, `approve`, `reject`
- [ ] Admin sahifasi: kutilayotgan shifokorlar jadvali, litsenziyani ko'rish, tasdiqlash tugmalari
- [ ] Slot modeli, unique indeks `{ doctorId, start }`
- [ ] `POST /slots/bulk`: kunlar, vaqt oralig'i va davomiylik bo'yicha slotlar yaratish (ustma-ust tushmasligi tekshiriladi)
- [ ] `DELETE /slots/:id` (faqat `OPEN` bo'lsa)
- [ ] Shifokor sahifasi: haftalik jadval yaratish formasi va slotlar ko'rinishi

**Natija:** admin shifokorni tasdiqlaydi, shifokor ish jadvalini yaratadi.

### Bosqich 9 · Kun 19–21 · Qidiruv va seed
- [ ] `GET /doctors`: bo'lim, sana, narx, reyting bo'yicha filtr, saralash, sahifalash (faqat `APPROVED`)
- [ ] `GET /doctors/:id/slots?date=`
- [ ] Frontend: shifokorlar ro'yxati (filtrlar, kartochkalar), shifokor sahifasi (profil + kalendar + bo'sh vaqtlar)
- [ ] `scripts/seed.ts`: 1 admin, 20 shifokor (turli bo'limlar), 10 bemor, 2 haftalik slotlar
- [ ] Loading, bo'sh natija va xato holatlari

**Natija:** bemor shifokor qidirib, bo'sh vaqtlarni ko'radi. ✅ **2-hafta tugadi**

---

## 3-hafta: Band qilish va to'lov

### Bosqich 10 · Kun 22–23 · Atomik band qilish va holat mashinasi
- [ ] Appointment modeli (`slotId` unique)
- [ ] `canTransition(from, to)` funksiyasi va to'liq unit testlari
- [ ] `POST /appointments`: `findOneAndUpdate` bilan slotni `HELD` qilish, `PENDING` appointment yaratish
- [ ] `GET /appointments/me`, `GET /appointments/:id` (egalik tekshiruvi bilan)
- [ ] **Concurrency testi:** 50 ta parallel so'rov → 1 ta `201`, 49 ta `409`

**Natija:** bir slotni ikki kishi band qila olmasligi test bilan isbotlangan.

### Bosqich 11 · Kun 24–25 · Muddat tugashi va bekor qilish
- [ ] BullMQ ulash, `jobs/slot-expiry.ts`: har daqiqada `heldUntil` o'tgan slotlarni `OPEN`, appointment'larni `CANCELLED` qiladi
- [ ] `PATCH /appointments/:id/cancel`: qoidalar (masalan, qabulga 1 soatdan kam qolganda bekor qilib bo'lmaydi)
- [ ] Testlar: muddati o'tgan slot qayta ochiladi; bekor qilingan slot boshqalarga ko'rinadi

**Natija:** to'lanmagan band qilishlar avtomatik bekor bo'ladi.

### Bosqich 12 · Kun 26–28 · To'lov va band qilish oqimi (frontend)
- [ ] Payment modeli, `idempotencyKey` unique indeksi
- [ ] Toss Payments test rejimi: frontend'da to'lov oynasi, `successUrl` / `failUrl`
- [ ] `POST /payments/confirm`: Toss tasdiqlash API'si + MongoDB tranzaksiyasi (Payment `PAID`, Slot `BOOKED`, Appointment `CONFIRMED`)
- [ ] Bir xil `Idempotency-Key` bilan qayta so'rov → avvalgi natija qaytadi
- [ ] Refund: bekor qilinganda Toss orqali qaytarish
- [ ] Frontend: vaqt tanlash → tasdiqlash → to'lov → muvaffaqiyat sahifasi; "Mening qabullarim" sahifasi
- [ ] Testlar: idempotency, to'lov xatosi holati

**Natija:** bemor to'liq band qilish va to'lov oqimini o'tadi. ✅ **3-hafta tugadi**

---

## 4-hafta: AI triage

### Bosqich 13 · Kun 29–30 · Shoshilinch filtr va bilimlar bazasi
- [ ] `triage/emergency.ts`: ko, en, uz tillarida kalit so'zlar va iboralar
- [ ] Unit testlar: kamida 30 ta holat (shoshilinch va oddiy)
- [ ] `triage_knowledge` uchun ma'lumot: 100–300 ta "simptom → bo'lim" yozuvi (ochiq tibbiy manbalardan), `data/triage-knowledge.json`
- [ ] Bo'limlar ro'yxatini `shared` paketda yakunlash (내과, 소아과, 피부과, 이비인후과, 정형외과, 신경과, 정신건강의학과, 산부인과, 안과, 가정의학과...)

**Natija:** shoshilinch holatlar ishonchli aniqlanadi, RAG uchun ma'lumot tayyor.

### Bosqich 14 · Kun 31–32 · RAG va LLM chaqiruvi
- [ ] `scripts/embed-knowledge.ts`: yozuvlarni embedding qilib bazaga yozish
- [ ] Atlas Vector Search indeksi (lokalda `mongodb-atlas-local`)
- [ ] `triage.service.ts`: filtr → embedding → vector search (top 5) → LLM → Zod validatsiya → 1 marta qayta urinish → fallback `가정의학과`
- [ ] Timeout (10 soniya), xatolarni boshqarish, rate limit (daqiqasiga 5 ta)
- [ ] `POST /triage` endpoint'i va integratsion test (LLM mock bilan)

**Natija:** API simptom matni uchun bo'lim tavsiyasini JSON'da qaytaradi.

### Bosqich 15 · Kun 33–35 · Triage UI va baholash
- [ ] Frontend: simptom kiritish sahifasi, natija kartochkalari (bo'lim + foiz + urgency)
- [ ] Shoshilinch holat uchun qizil ogohlantirish ekrani (119, 1393)
- [ ] "Bu tashxis emas" ogohlantirishi
- [ ] "Shu bo'lim shifokorlarini ko'rish" tugmasi → filtrlangan qidiruv; triage natijasi appointment'ga saqlanadi
- [ ] `eval/triage-cases.json`: 50 ta test holati
- [ ] `scripts/eval-triage.ts`: accuracy va top-2 accuracy'ni hisoblash, natijani `docs/triage-eval.md` ga yozish

**Natija:** AI triage ishlaydi, aniqligi raqamda o'lchangan. ✅ **4-hafta tugadi**

---

## 5-hafta: Video konsultatsiya va chat

### Bosqich 16 · Kun 36–37 · Socket server va signaling
- [ ] Socket.io serverini HTTP serverga ulash, CORS
- [ ] Socket autentifikatsiyasi (cookie'dagi JWT)
- [ ] `call:join`: faqat shu qabul bemori va shifokori, faqat qabul vaqtidan 10 daqiqa oldin va keyin
- [ ] `call:offer`, `call:answer`, `call:ice-candidate`, `call:leave`, `call:peer-joined`
- [ ] Testlar: begona foydalanuvchi xonaga kira olmaydi

**Natija:** signaling server xavfsiz ishlaydi.

### Bosqich 17 · Kun 38–40 · WebRTC va video UI
- [ ] `hooks/useWebRTC.ts`: `getUserMedia`, `RTCPeerConnection`, offer/answer, ICE, ulanish holati
- [ ] STUN (Google) va TURN (Metered.ca) sozlamalari, env orqali
- [ ] `/call/[id]` sahifasi: ikki video oyna, mikrofon va kamera tugmalari, tugatish tugmasi, ulanish holati ko'rsatkichi
- [ ] Kamera yoki mikrofon ruxsati berilmasa, tushunarli xabar
- [ ] Ikki xil qurilmada (kompyuter + telefon) sinab ko'rish

**Natija:** bemor va shifokor bir-birini ko'rib gaplashadi.

### Bosqich 18 · Kun 41–42 · Qayta ulanish, chat, konsultatsiya holati
- [ ] Internet uzilganda ICE restart va qayta ulanish
- [ ] `chat:message`: qo'ng'iroq ichida chat, xabarlar `consultations.messages` ga saqlanadi
- [ ] `POST /consultations/:id/start` → `IN_PROGRESS`, `end` → `COMPLETED`
- [ ] Shifokor uchun qo'ng'iroq yonida xulosa yozish maydoni

**Natija:** video konsultatsiya to'liq ishlaydi. ✅ **5-hafta tugadi**

---

## 6-hafta: Retsept, bildirishnomalar, sharhlar, admin

### Bosqich 19 · Kun 43–44 · Elektron retsept
- [ ] Prescription modeli, `POST /prescriptions` (faqat shu qabul shifokori, faqat `COMPLETED` dan keyin)
- [ ] Shifokor uchun dorilar ro'yxati formasi (dinamik qatorlar)
- [ ] `GET /prescriptions/me`, bemor uchun retseptlar sahifasi
- [ ] Retseptni PDF qilib yuklab olish

**Natija:** shifokor retsept yozadi, bemor uni ko'rib yuklab oladi.

### Bosqich 20 · Kun 45–46 · Bildirishnomalar
- [ ] Notification modeli, `GET /notifications`, `PATCH /notifications/:id/read`
- [ ] Hodisalar: band qilish tasdiqlandi, qabulga 10 daqiqa qoldi (BullMQ delayed job), retsept tayyor, shifokor tasdiqlandi
- [ ] Ilova ichida: `notification:new` socket hodisasi, header'da qo'ng'iroqcha belgisi va ro'yxat
- [ ] E-mail: Resend yoki Nodemailer, oddiy HTML shablonlar

**Natija:** foydalanuvchilar muhim hodisalar haqida xabar oladi.

### Bosqich 21 · Kun 47–49 · Sharhlar va dashboard'lar
- [ ] Review modeli, `POST /reviews`: faqat `COMPLETED` qabul, faqat bir marta, reytingni qayta hisoblash
- [ ] Shifokor sahifasida sharhlar ro'yxati
- [ ] Shifokor dashboardi: bugungi qabullar, kelgusi jadval, "qo'ng'iroqqa kirish" tugmasi
- [ ] Admin dashboardi (MongoDB aggregation): foydalanuvchilar soni, kunlik qabullar, daromad, eng ko'p tavsiya qilingan bo'limlar, grafiklar (Recharts)

**Natija:** MVP funksional jihatdan to'liq. ✅ **6-hafta tugadi**

---

## 7-hafta: Testlar, xavfsizlik, sifat

### Bosqich 22 · Kun 50–51 · Unit va integratsion testlar
- [ ] Yetishmayotgan unit testlar: holat mashinasi, shoshilinch filtr, narx, ruxsatlar
- [ ] Integratsion testlar: auth, shifokorlar, band qilish, to'lov, retsept, sharhlar
- [ ] Qamrov hisoboti (`vitest --coverage`), asosiy modullarda kamida 70%
- [ ] CI'da qamrov hisobotini ko'rsatish

**Natija:** backend testlar bilan himoyalangan.

### Bosqich 23 · Kun 52–53 · E2E va load test
- [ ] Playwright: ro'yxatdan o'tish → triage → shifokor tanlash → band qilish → to'lov (test) → qabullar sahifasi
- [ ] Playwright: shifokor oqimi (jadval yaratish, retsept yozish), admin oqimi (tasdiqlash)
- [ ] `load-tests/booking.js` (k6): 100 ta virtual foydalanuvchi bitta slotga → 1 ta muvaffaqiyatli, 99 ta `409`
- [ ] Qidiruv endpoint'i uchun load test: p95 latency
- [ ] Natijalarni `docs/load-test.md` ga yozish (skrinshot bilan)

**Natija:** asosiy oqimlar avtomatik tekshiriladi, raqamlar README uchun tayyor.

### Bosqich 24 · Kun 54–56 · Xavfsizlik, monitoring, hujjat
- [ ] Xavfsizlik ro'yxatidagi har bir bandni tekshirish (asosiy rejadagi 10-bo'lim)
- [ ] IDOR testlari: bemor boshqa bemorning qabuli, retsepti va chatini ko'ra olmaydi
- [ ] Audit log middleware (tibbiy yozuvlarga kirish)
- [ ] Loglarda parol, token va simptom matni yozilmasligini tekshirish
- [ ] Sentry: frontend va backend
- [ ] Swagger: barcha endpoint'lar `/api/docs` da
- [ ] Lighthouse: accessibility va mobil ko'rinish, topilgan muammolarni tuzatish

**Natija:** loyiha xavfsiz, monitoring qilinadi, API hujjatlashtirilgan. ✅ **7-hafta tugadi**

---

## 8-hafta: Deploy va CI/CD

### Bosqich 25 · Kun 57–58 · Bulutli ma'lumotlar bazalari
- [ ] MongoDB Atlas M0 klasteri, foydalanuvchi va IP ruxsatlari
- [ ] Atlas Vector Search indeksi, `embed-knowledge` skriptini ishga tushirish
- [ ] Upstash Redis (BullMQ uchun mos ulanish sozlamalari)
- [ ] Production seed: demo akkauntlar va shifokorlar

**Natija:** production ma'lumotlar bazalari tayyor.

### Bosqich 26 · Kun 59–60 · Backend va frontend deploy
- [ ] `apps/api/Dockerfile` (multi-stage build), lokalda sinab ko'rish
- [ ] Render (yoki Railway): Docker deploy, env o'zgaruvchilari, WebSocket yoqilgan
- [ ] Vercel: `apps/web`, env o'zgaruvchilari
- [ ] Turli domenlar orasida cookie va CORS sozlamalarini tekshirish (`SameSite=None; Secure` yoki umumiy domen)
- [ ] Production'da to'liq oqimni qo'lda sinab ko'rish

**Natija:** loyiha internetda ishlaydi.

### Bosqich 27 · Kun 61–63 · Domen, CD va monitoring
- [ ] Domen sotib olish, `app.` (Vercel) va `api.` (Render) subdomenlari, HTTPS
- [ ] GitHub Actions: `main` ga merge bo'lganda avtomatik deploy
- [ ] UptimeRobot: `/api/health` ni kuzatish
- [ ] Demo akkauntlar: `patient@demo.com`, `doctor@demo.com`, `admin@demo.com`
- [ ] Ikki qurilmada production video qo'ng'iroq testi (TURN ishlayaptimi)
- [ ] Topilgan xatolarni tuzatish

**Natija:** barqaror, avtomatik deploy qilinadigan demo. ✅ **8-hafta tugadi**

---

## 9-hafta: Hujjatlar, portfolio, ishga topshirish

### Bosqich 28 · Kun 64–65 · README va hujjatlar
- [ ] README (asosiy rejadagi 12-bo'lim tuzilmasi): muammo, funksiyalar, arxitektura, texnik qiyinchiliklar, raqamlar, stack, lokal ishga tushirish
- [ ] Arxitektura diagrammasi va ERD rasmlari (yakuniy variant)
- [ ] `docs/decisions/`: 3–5 ta ADR (atomik band qilish, Node.js va MongoDB tanlovi, WebRTC + TURN, AI xavfsizlik qatlami)
- [ ] Koreys va ingliz tillarida qisqa README bo'limi

**Natija:** repo rekruter uchun tushunarli.

### Bosqich 29 · Kun 66–67 · Demo video va vizual materiallar
- [ ] 2–3 daqiqalik demo video (Loom yoki OBS): bemor oqimi → shifokor oqimi → admin
- [ ] README uchun 4–5 ta GIF: triage, band qilish, video qo'ng'iroq, retsept, admin dashboard
- [ ] Videoni YouTube'ga yuklash, README'ga havola

**Natija:** loyihani 3 daqiqada ko'rsatish mumkin.

### Bosqich 30 · Kun 68–70 · Blog, rezyume, topshirish
- [ ] Birinchi blog maqola (velog yoki Medium): "MongoDB'da ikki kishi bitta vaqtni band qilishining oldini olish"
- [ ] Rezyumeni yangilash (asosiy rejadagi namuna bo'yicha, haqiqiy raqamlar bilan)
- [ ] LinkedIn profilini yangilash, loyiha haqida post
- [ ] Yakuniy tekshiruv ro'yxatini (asosiy rejadagi 14-bo'lim) bandma-band o'tish
- [ ] Wanted, Jumpit, Rocketpunch, LinkedIn'da 10 ta vakansiyaga topshirish

**Natija:** loyiha tugadi, ishga topshirish boshlandi. 🎉

---

## Agar orqada qolsangiz: nimani qisqartirish mumkin

Asosiy oqim (auth → triage → band qilish → to'lov → video → retsept) albatta bo'lishi kerak. Vaqt yetmasa, quyidagilarni keyinga qoldiring:

| Qisqartirish | Tejaladigan vaqt |
|---|---|
| Ko'p tillilik o'rniga faqat ingliz va koreys tili | 1 kun |
| E-mail o'rniga faqat ilova ichidagi bildirishnomalar | 1 kun |
| Retseptni PDF qilish o'rniga oddiy sahifa | 1 kun |
| Admin grafiklari o'rniga oddiy raqamlar | 1 kun |
| RAG o'rniga avval faqat LLM + prompt (RAG'ni keyinroq qo'shish) | 2 kun |
| O'z domeningiz o'rniga Vercel va Render subdomenlari | 1 kun |

**Hech qachon qisqartirmang:** concurrency testi, idempotency, shoshilinch holat filtri, IDOR himoyasi, README va demo video. Intervyuda aynan shular so'raladi.

---

## Haftalik nazorat

Har yakshanba 30 daqiqa ajrating:
- [ ] Shu haftaning barcha bosqichlari tugadimi?
- [ ] CI yashilmi, `main` ishlaydimi?
- [ ] Orqada qolgan bo'lsam, qaysi vazifani qisqartiraman?
- [ ] Shu haftada nimani o'rgandim? (blog uchun 3–4 qator eslatma)
