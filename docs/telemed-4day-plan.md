# Telemeditsina ilovasi: 4 kunlik tezkor reja

> **Asos:** [telemed-project-plan.md](./telemed-project-plan.md) (to'liq versiya, 70 kun)
> **Bu reja:** 4 kun, kuniga **10–12 soat**, qisqartirilgan MVP.
> **Shart:** kodning katta qismi AI yordamchi (Claude Code va boshqalar) bilan yoziladi, siz esa tushunib, tekshirib, sinab borasiz.

---

## Ochiq gap: 4 kunda nima real, nima real emas

70 kunlik rejani 4 kunga sig'dirib bo'lmaydi. Shuning uchun **eng muhim qismlar qoldirildi**, qolganlari soddalashtirildi yoki keyingi versiyaga o'tkazildi. Natijada ishlaydigan, deploy qilingan va intervyuda ko'rsatsa bo'ladigan loyiha chiqadi. Keyin uni bosqichma-bosqich to'liq versiyaga kengaytirasiz.

### Qoldiriladi (intervyuda so'raladigan qismlar)
- ✅ Auth va 3 ta rol (bemor, shifokor, admin)
- ✅ Shifokor profili, admin tasdiqlashi, ish jadvali (slotlar), qidiruv
- ✅ **Atomik band qilish + concurrency testi** (eng muhim texnik qism)
- ✅ To'lov (mock) + **idempotency + MongoDB tranzaksiyasi**
- ✅ **AI triage + shoshilinch holat filtri** + kichik baholash (20 ta holat)
- ✅ **WebRTC video qo'ng'iroq + chat**
- ✅ Elektron retsept, sharhlar
- ✅ Deploy, README, demo video

### Soddalashtiriladi
| To'liq rejada | 4 kunlik rejada |
|---|---|
| Turborepo + `shared` paket | Oddiy ikki papka: `api/` va `web/` |
| Toss Payments | Mock to'lov sahifasi (idempotency va tranzaksiya baribir bor) |
| RAG + Vector Search | LLM + yaxshi prompt + bo'limlar ro'yxati (RAG keyinroq) |
| BullMQ fon vazifalari | So'rov paytida tekshiruv: `heldUntil` o'tgan slot `OPEN` deb hisoblanadi |
| S3 litsenziya yuklash | Faqat litsenziya raqami (fayl keyinroq) |
| 3 til (ko, en, uz) | Faqat ingliz tili |
| E-mail, push bildirishnomalar | Yo'q (faqat UI'dagi holatlar) |
| Retsept PDF | Chop etish uchun qulay sahifa (`window.print()`) |
| Admin grafiklari | Oddiy raqamli kartochkalar |
| Vitest + Playwright + k6 to'liq | Concurrency testi + 5–6 ta asosiy API testi |
| Sentry, Swagger, domen | Yo'q (Vercel va Render subdomenlari) |

---

## Stack (soddalashtirilgan)

| Qism | Texnologiya |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui, React Query |
| Backend | Node.js + Express, TypeScript, Mongoose, Zod, JWT (httpOnly cookie), bcrypt |
| Real-time | Socket.io (signaling + chat), WebRTC (`simple-peer`) |
| AI | LLM API (JSON javob) + qoidaga asoslangan shoshilinch filtr |
| Ma'lumotlar bazasi | MongoDB Atlas (bepul M0, tranzaksiyalar ishlaydi) |
| Test | Vitest + Supertest + mongodb-memory-server (replica set rejimi) |
| Deploy | Vercel (web), Render (api), Atlas |

**Lokal MongoDB o'rniga darhol Atlas** ishlatiladi: replica set va tranzaksiyalar sozlashsiz ishlaydi, deploy kuni vaqt tejaladi.

---

## Papka tuzilmasi

```
telemed/
├── api/
│   ├── src/
│   │   ├── config/        # env.ts, db.ts
│   │   ├── models/        # User, Doctor, Slot, Appointment, Payment, Prescription, Review
│   │   ├── routes/        # auth, doctors, slots, appointments, payments, triage, prescriptions, reviews, admin
│   │   ├── services/      # booking.service.ts, triage.service.ts
│   │   ├── middlewares/   # auth.ts, role.ts, validate.ts, error.ts
│   │   ├── socket.ts      # signaling + chat
│   │   ├── app.ts
│   │   └── server.ts
│   ├── tests/
│   ├── scripts/seed.ts
│   └── eval/triage-cases.json
├── web/
│   ├── app/
│   │   ├── (auth)/login, register
│   │   ├── triage/
│   │   ├── doctors/, doctors/[id]/
│   │   ├── appointments/, appointments/[id]/
│   │   ├── pay/[id]/
│   │   ├── call/[id]/
│   │   ├── doctor/        # shifokor paneli
│   │   └── admin/
│   ├── components/
│   └── lib/               # api.ts, socket.ts
└── README.md
```

---

## 1-kun: Poydevor, auth, shifokorlar va slotlar

**Maqsad:** kun oxirida bemor shifokorlarni qidirib, bo'sh vaqtlarni ko'radi.

| Vaqt | Vazifa |
|---|---|
| 1 soat | Repo, `api/` (Express + TS), `web/` (create-next-app + shadcn/ui), Atlas klasteri, `.env` |
| 2 soat | Backend asos: env tekshiruvi, DB ulanish, xato middleware, `/health`. User modeli. Auth: `register`, `login`, `logout`, `me` (JWT httpOnly cookie). `requireAuth`, `requireRole`, `validate` |
| 2 soat | Frontend auth: login, register sahifalari, `useMe` hook, rolga qarab yo'naltirish, header |
| 2 soat | Doctor modeli, profil API va sahifasi. Admin: kutilayotgan shifokorlar ro'yxati, tasdiqlash yoki rad etish |
| 2 soat | Slot modeli (unique `{doctorId, start}`), `POST /slots/bulk` (sana, vaqt oralig'i, davomiylik), shifokor uchun jadval yaratish sahifasi |
| 2 soat | `GET /doctors` (bo'lim filtri, sahifalash), `GET /doctors/:id/slots`, shifokorlar ro'yxati va shifokor sahifasi, `seed.ts` (1 admin, 10 shifokor, 5 bemor, slotlar) |

**Kun oxiri tekshiruvi:**
- [ ] Uch rol bilan kirish ishlaydi
- [ ] Admin shifokorni tasdiqlaydi
- [ ] Shifokor slot yaratadi
- [ ] Bemor shifokorlar va bo'sh vaqtlarni ko'radi
- [ ] Hammasi GitHub'da

---

## 2-kun: Band qilish, to'lov va AI triage

**Maqsad:** bemor simptom yozadi, AI bo'lim tavsiya qiladi, bemor vaqt band qilib to'laydi.

| Vaqt | Vazifa |
|---|---|
| 2.5 soat | **Band qilish:** Appointment modeli, holat mashinasi (`canTransition`), `POST /appointments` atomik `findOneAndUpdate` bilan (`OPEN` yoki `heldUntil` o'tgan `HELD` → `HELD`), `GET /appointments/me`, bekor qilish |
| 1 soat | **Concurrency testi:** 50 ta parallel so'rov → 1 ta `201`, 49 ta `409` |
| 2 soat | **To'lov:** Payment modeli (`idempotencyKey` unique), `POST /payments/confirm` tranzaksiya ichida (Payment `PAID`, Slot `BOOKED`, Appointment `CONFIRMED`). Mock to'lov sahifasi. Idempotency testi |
| 1.5 soat | Frontend: vaqt tanlash → band qilish → to'lov → "Mening qabullarim" |
| 2 soat | **AI triage backend:** shoshilinch filtr (kalit so'zlar), LLM chaqiruvi (bo'limlar ro'yxati bilan prompt, JSON javob), Zod validatsiya, 1 marta qayta urinish, fallback `Family Medicine`, timeout, rate limit |
| 1.5 soat | **Triage UI:** simptom formasi, natija kartochkalari, shoshilinch holat ekrani (119, 1393), "Bu tashxis emas" ogohlantirishi, "shifokorlarni ko'rish" tugmasi. `eval/triage-cases.json` (20 ta holat) va accuracy skripti |

**Kun oxiri tekshiruvi:**
- [ ] Concurrency va idempotency testlari o'tadi
- [ ] Triage → shifokor → band qilish → to'lov oqimi oxirigacha ishlaydi
- [ ] Shoshilinch matnlar LLM'ga yuborilmaydi
- [ ] Triage aniqligi hisoblangan

---

## 3-kun: Video qo'ng'iroq, chat, retsept, sharhlar

**Maqsad:** MVP funksional jihatdan to'liq.

| Vaqt | Vazifa |
|---|---|
| 2 soat | **Socket server:** cookie'dagi JWT bilan autentifikatsiya, `call:join` (faqat shu qabul bemori va shifokori), `signal` (offer, answer, ICE), `chat:message`, `call:leave` |
| 3 soat | **Video UI:** `simple-peer` bilan ulanish, STUN (Google) + bepul TURN (Metered.ca), ikki video oyna, mikrofon va kamera tugmalari, tugatish, ulanish holati, kamera ruxsati xatosi. **Ikki qurilmada sinash** |
| 1 soat | Qo'ng'iroq ichida chat, xabarlarni saqlash. Shifokor uchun "boshlash" va "tugatish" → `IN_PROGRESS` → `COMPLETED` |
| 1.5 soat | **Retsept:** model, `POST /prescriptions` (faqat shu shifokor, `COMPLETED` dan keyin), shifokor formasi (dinamik qatorlar), bemor uchun retsept sahifasi va chop etish |
| 1 soat | **Sharhlar:** faqat `COMPLETED` qabul, bir marta, reytingni yangilash, shifokor sahifasida ko'rsatish |
| 1.5 soat | **Dashboard'lar:** shifokor (bugungi qabullar, "qo'ng'iroqqa kirish"), admin (foydalanuvchilar, qabullar, daromad raqamlari) |

**Kun oxiri tekshiruvi:**
- [ ] Ikki qurilmada video va chat ishlaydi
- [ ] Shifokor retsept yozadi, bemor ko'radi
- [ ] Sharh qoldiriladi, reyting yangilanadi
- [ ] Begona foydalanuvchi qo'ng'iroq xonasiga kira olmaydi

---

## 4-kun: Testlar, deploy, README, demo

**Maqsad:** loyiha internetda, rekruterga yuborishga tayyor.

| Vaqt | Vazifa |
|---|---|
| 2 soat | **Testlar:** auth, ruxsatlar (IDOR: bemor boshqa bemorning qabulini ko'ra olmaydi), retsept ruxsati, holat mashinasi. GitHub Actions: lint + test |
| 1 soat | **Xavfsizlik:** helmet, CORS faqat frontend domeni, login va triage rate limit, loglarda parol va token yo'qligi, `.env.example` |
| 2.5 soat | **Deploy:** Render (api, WebSocket yoqilgan), Vercel (web), env o'zgaruvchilari, turli domenlar uchun cookie (`SameSite=None; Secure`), production seed va demo akkauntlar. **Productionda to'liq oqimni va ikki qurilmada videoni sinash** |
| 1 soat | Topilgan xatolarni tuzatish |
| 2 soat | **README:** muammo, funksiyalar, arxitektura diagrammasi, texnik qiyinchiliklar (concurrency, idempotency, WebRTC, AI xavfsizligi) va raqamlar, stack, lokal ishga tushirish, demo akkauntlar, "keyingi qadamlar" ro'yxati |
| 1.5 soat | **Demo:** 2 daqiqalik video (bemor → shifokor → admin), 3 ta GIF, rezyumega 3–4 qator qo'shish |

**Kun oxiri tekshiruvi:**
- [ ] Demo havola ishlaydi, demo akkauntlar bilan kirish mumkin
- [ ] CI yashil
- [ ] README'da raqamlar, diagramma va demo video bor
- [ ] Rezyume yangilangan

---

## Agar vaqt yetmasa: qisqartirish tartibi

Shu tartibda olib tashlang (yuqoridagisini birinchi):

1. Admin dashboard raqamlari
2. Sharhlar
3. Qo'ng'iroq ichidagi chat
4. Shifokor dashboardi (oddiy ro'yxat bilan almashtirish)
5. GIF'lar (faqat demo video qoladi)

**Olib tashlamang:** concurrency testi, idempotency, shoshilinch filtr, ruxsat tekshiruvlari, video qo'ng'iroq, deploy, README.

---

## 4 kundan keyin: to'liq versiyaga kengaytirish

Loyiha ishlab turgan holatda quyidagilarni bittadan qo'shib boring (har biri 1–2 kun):

| # | Qo'shimcha | Nima beradi |
|---|---|---|
| 1 | RAG + Atlas Vector Search, 50 ta holatda baholash | Kuchliroq AI qismi |
| 2 | Toss Payments test integratsiyasi | Koreya bozoriga moslik |
| 3 | BullMQ: muddat tugashi va eslatmalar | Fon vazifalari tajribasi |
| 4 | Playwright E2E + k6 load test | Raqamlar bilan sifat isboti |
| 5 | next-intl: koreys va o'zbek tillari | Koreyadagi foydalanuvchilar uchun |
| 6 | Litsenziya yuklash (S3), e-mail bildirishnomalar | To'liq mahsulot hissi |
| 7 | Sentry, Swagger, o'z domeningiz | Production darajasi |
| 8 | Blog maqolalar | Rekruterlar uchun qo'shimcha ishonch |
