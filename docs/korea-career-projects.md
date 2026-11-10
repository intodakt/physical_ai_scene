# Koreyada Software va AI Engineer bo'lib ishga kirish: portfolio loyihalari bo'yicha qo'llanma

> Bu hujjat Koreya IT bozoridagi umumiy trendlarga asoslangan. Aniq vakansiyalarni **Wanted**, **Jumpit**, **Rocketpunch**, **Programmers Career** va **LinkedIn** saytlarida tekshirib ko'ring.

## Mundarija

1. [Koreya IT bozori haqida qisqacha](#1-koreya-it-bozori-haqida-qisqacha)
2. [Software Engineering loyihalari](#2-software-engineering-loyihalari)
3. [AI Engineering loyihalari](#3-ai-engineering-loyihalari)
4. [Physical AI va Robotics loyihalari](#4-physical-ai-va-robotics-loyihalari)
5. [Full Stack loyihalar (AI qo'shilgan)](#5-full-stack-loyihalar-ai-qoshilgan)
6. [Koreyada talabi eng yuqori sohalar](#6-koreyada-talabi-eng-yuqori-sohalar)
7. [Asosiy loyiha: Telemeditsina ilovasi (Node.js + Next.js + MongoDB)](#7-asosiy-loyiha-telemeditsina-ilovasi-nodejs--nextjs--mongodb)
8. [Ishga kirish bo'yicha umumiy maslahatlar](#8-ishga-kirish-boyicha-umumiy-maslahatlar)
9. [Yakuniy tavsiya va yo'l xaritasi](#9-yakuniy-tavsiya-va-yol-xaritasi)

---

## 1. Koreya IT bozori haqida qisqacha

**Asosiy ish beruvchilar:**

- **Yirik IT kompaniyalar:** Naver, Kakao, Line, Coupang, Toss, Baemin (Woowa Brothers), Danggeun (Karrot)
- **AI kompaniyalari:** Samsung Research, LG AI Research, Upstage, Naver Cloud (HyperCLOVA X), Kakao Brain, Wrtn
- **AI chip (NPU):** Rebellions, FuriosaAI
- **Robototexnika va Physical AI:** Rainbow Robotics, Doosan Robotics, Hyundai / Boston Dynamics, Naver Labs
- **IT xizmatlari:** Samsung SDS, LG CNS, SK C&C

Koreys kompaniyalari **production darajasidagi**, ishlab turgan va o'lchab ko'rilgan loyihalarni qadrlaydi. Tutorial nusxalari ularni qiziqtirmaydi.

---

## 2. Software Engineering loyihalari

### 2.1. Ko'p trafikka chidaydigan backend
- Coupang yoki Baemin tipidagi buyurtma, to'lov yoki inventar tizimi
- **Stack:** Spring Boot (Java/Kotlin), Redis, Kafka, MySQL
- Load test (k6 yoki nGrinder) qiling va TPS hamda latency raqamlarini ko'rsating

### 2.2. Real-time chat yoki bildirishnoma servisi
- KakaoTalk'ning soddalashtirilgan varianti
- WebSocket, Redis Pub/Sub, xabarlarni saqlash, scale-out

### 2.3. Joylashuvga asoslangan marketplace
- Danggeun uslubida
- PostGIS yoki geohash bilan qidiruv, Elasticsearch'da koreys tili tahlilchisi (nori)

### 2.4. DevOps va infratuzilma
- Docker, Kubernetes, CI/CD, Prometheus + Grafana monitoring
- AWS yoki NCP (Naver Cloud) ga deploy

### 2.5. Konsert chiptalarini bron qilish tizimi
- K-pop konsert chiptalari soniyalarda sotiladi (Interpark, Melon Ticket)
- Navbat (queue) tizimi, distributed lock (Redis / Redisson), rate limiting, bot himoyasi
- Intervyudagi "concurrency muammosini qanday hal qildingiz?" savoliga eng yaxshi javob

### 2.6. Birinchi kelganga kupon tizimi (선착순 쿠폰)
- Kichik loyiha, lekin koreys intervyularida juda ko'p so'raladi
- 100 000 so'rovda 1000 ta kuponni to'g'ri taqsimlash

### 2.7. Pul o'tkazish yoki to'lov tizimi
- Toss yoki KakaoPay uslubida
- Tranzaksiyalar, idempotency, ledger, Saga pattern, xatoda pulni qaytarish

### 2.8. Monolitdan mikroservislarga
- Avval monolit, keyin bosqichma-bosqich ajratish
- Har bosqichda nima o'zgarganini va nega shunday qilganingizni hujjatlashtirish

### 2.9. Real foydalanuvchili mobil ilova
- Flutter yoki React Native
- Masalan, Koreyadagi o'zbek yoki xorijiy talabalar jamoasi uchun
- 100 ta real foydalanuvchi har qanday demodan kuchliroq ta'sir qiladi

### 2.10. Tizim dasturlash loyihalari
- **O'z Redis'ingiz:** Go yoki Rust'da key-value store (RESP protokoli, TTL, AOF persistence)
- **O'z message queue'ingiz:** Kafka'ning soddalashtirilgan versiyasi (partition, offset, consumer group)
- **URL shortener + analitika:** Snowflake ID, caching, millionlab so'rov
- **Webtoon yoki video streaming:** CDN, HLS transcoding, lazy loading
- **Real-time hamkorlikdagi muharrir:** CRDT yoki OT, WebSocket
- **Observability platformasi:** OpenTelemetry, loglar, metrikalar, trace'lar

### 2.11. Open source'ga hissa qo'shish
- Spring, Kafka, LangChain, vLLM, LeRobot kabi loyihalarga qabul qilingan PR'lar rezyumeda katta ustunlik beradi

---

## 3. AI Engineering loyihalari

| # | Loyiha | Qisqacha |
|---|---|---|
| 1 | **Koreys tilidagi RAG** | Qonunlar, viza yoki immigratsiya hujjatlari bo'yicha savol-javob. Koreys embedding modellari (bge-m3, KoSimCSE) va baholash tizimi |
| 2 | **LLM fine-tune va serving** | EXAONE, Solar yoki Qwen'ni LoRA bilan fine-tune qilish, vLLM bilan serve qilish, latency va throughput benchmarki |
| 3 | **AI Agent** | Tool-calling bilan ishlaydigan agent (kod review, hujjatlarni avtomatlashtirish) |
| 4 | **Edge / on-device AI** | ONNX, TensorRT, quantization. Samsung, LG va NPU startaplari uchun |
| 5 | **Koreys OCR va hujjat tushunish** | Kvitansiya, ID karta va hujjatlardan ma'lumot ajratish (Upstage, Naver yo'nalishi) |
| 6 | **Ovozli assistent (STT/TTS)** | Whisper'ni koreys tilida fine-tune qilish, real-time ovozli agent |
| 7 | **Tavsiya tizimi (RecSys)** | Collaborative filtering, keyin two-tower model, A/B test |
| 8 | **LLM baholash va xavfsizlik** | KMMLU va HAE-RAE benchmarklari, hallucination aniqlash, guardrail'lar |
| 9 | **MLOps pipeline** | MLflow, Airflow, Kubeflow yoki BentoML, drift detection |
| 10 | **Multimodal qidiruv** | CLIP + vektor baza (Qdrant, Milvus) |
| 11 | **Koreys tili AI tutori** | Talaffuzni baholash, xatolarni tuzatish, TOPIK'ka tayyorlash |
| 12 | **Koreys-o'zbek tarjimon** | Bu juftlik uchun yaxshi model deyarli yo'q, NLLB yoki mT5'ni fine-tune qilish |
| 13 | **Kod review AI boti** | GitHub PR'larni avtomatik tekshiruvchi bot |
| 14 | **Soxta sharhlarni aniqlash** | Koreys sharhlarida soxta va reklama matnlarni topish |
| 15 | **Anomaliya aniqlash** | Sensor yoki server loglari, time-series, autoencoder |
| 16 | **LLM inference optimizatsiyasi** | KV-cache, speculative decoding, quantization'ni implement qilib o'lchash |

---

## 4. Physical AI va Robotics loyihalari

Samsung, Hyundai, Naver Labs va LG bu sohaga hozir katta sarmoya kiritmoqda, raqobat esa kamroq.

- **`physical_ai_scene` reposini rivojlantirish:** simulyatsiya (Isaac Sim, MuJoCo, Genesis), sintetik ma'lumot, imitation learning yoki VLA
- **Sim-to-Real:** simulyatsiyada o'rgatilgan siyosatni arzon robot qo'lida (SO-100 yoki LeRobot, taxminan $200–300) ishlatish
- **Sintetik ma'lumot generatori:** domain randomization (yorug'lik, tekstura, joylashuv), keyin shu ma'lumotda detektor o'rgatib, aniqlikni o'lchash
- **VLA fine-tune:** OpenVLA, π0 yoki SmolVLA'ni o'z sahnangizda o'rgatish ("qizil kubni qutiga sol")
- **Digital Twin:** zavod yoki ombor simulyatsiyasi
- **Dron simulyatsiyasi:** PX4, AirSim yoki Isaac Sim bilan avtonom navigatsiya
- **Mobil robot navigatsiyasi:** ROS 2 + Nav2, SLAM, yo'l rejalash
- **Robot uchun til buyrug'i interfeysi:** LLM foydalanuvchi buyrug'ini robot harakatlari ketma-ketligiga aylantiradi

---

## 5. Full Stack loyihalar (AI qo'shilgan)

Bu loyihalarning har biri to'liq mahsulot: **frontend + backend + ma'lumotlar bazasi + deploy**. AI ular ichida bitta funksiya sifatida ishlaydi.

### Koreyada mashhur stack
- **Frontend:** React yoki Next.js, TypeScript, Tailwind, React Query, Zustand
- **Backend:** Spring Boot (Java/Kotlin) yoki NestJS / Node.js
- **Ma'lumotlar bazasi:** PostgreSQL, MySQL yoki MongoDB, Redis
- **Deploy:** AWS (EC2, S3, RDS), Docker, GitHub Actions, Vercel

### Loyihalar
1. **Koreyadagi xorijliklar uchun super-ilova:** viza, uy ijarasi, ish e'lonlari, forum, Naver yoki Kakao Map, real-time chat. AI qismi: viza bo'yicha RAG chatbot, avtomatik tarjima
2. **AI intervyu tayyorlash SaaS'i:** rezyume asosida savollar, ovozli javoblarni baholash, Toss Payments, obuna, admin panel
3. **Jamoaviy loyiha boshqaruvi (Jira yoki Notion uslubida):** Kanban, real-time tahrirlash, optimistic UI. AI qismi: uchrashuvdan vazifalar yaratish
4. **E-commerce (Coupang yoki Musinsa uslubida):** katalog, savatcha, to'lov, sotuvchi paneli. AI qismi: tavsiyalar, rasm bo'yicha qidiruv
5. **Ta'lim platformasi (Inflearn uslubida):** video darslar (HLS), kurs sotish. AI qismi: subtitr (Whisper), avtomatik test yaratish
6. **Developer blog platformasi (velog uslubida):** Markdown, SSR, SEO. AI qismi: avtomatik teg, o'xshash maqolalar. Birinchi full stack loyiha uchun ideal

### Har bir full stack loyihada bo'lishi kerak bo'lgan narsalar

| Qism | Nima |
|---|---|
| Frontend | Responsive dizayn, loading va xato holatlari, mobil ko'rinish |
| Backend | API hujjati (Swagger), validatsiya, xatolarni boshqarish |
| Test | Unit va integratsion testlar, E2E (Playwright) |
| DevOps | Docker, CI/CD, ishlab turgan haqiqiy domen |
| Hujjat | README: arxitektura diagrammasi, ERD, demo GIF |

---

## 6. Koreyada talabi eng yuqori sohalar

| Soha | Talab | Raqobat | Maosh | Asosiy stack | Kompaniyalar |
|---|---|---|---|---|---|
| Fintech | 🔥🔥🔥 | Yuqori | Juda yuqori | Kotlin, Spring | Toss, KakaoBank, KakaoPay, Naver Pay |
| E-commerce va logistika | 🔥🔥🔥 | O'rta | Yuqori | Java, Spring, Kafka | Coupang, Musinsa, Kurly, CJ Logistics |
| B2B SaaS | 🔥🔥🔥 | O'rta | Yuqori | TypeScript, Next.js | Channel Talk, Flex, Sendbird |
| Enterprise AI Agent | 🔥🔥🔥 | O'rta | Yuqori | Python, LLM, RAG | Samsung SDS, LG CNS, Upstage, Wrtn |
| Data Engineering | 🔥🔥 | Past | Yuqori | Kafka, Spark | Barcha yirik kompaniyalar |
| Smart Factory | 🔥🔥 | Past | O'rta–yuqori | Python, CV | Samsung, SK Hynix, LG, Hyundai, POSCO |
| Healthtech / Legaltech | 🔥🔥 | O'rta | O'rta–yuqori | Full stack + AI | Lunit, Vuno, LawTalk, Doctor Now |

### Har bir soha uchun loyiha
- **Fintech:** shaxsiy moliya boshqaruvi ilovasi (Banksalad uslubida): xarajatlarni kategoriyalash, byudjet, idempotency, audit log
- **E-commerce va logistika:** tez yetkazib berish va ombor tizimi (Coupang Rocket uslubida): kuryer marshruti, real-time kuzatish, flash sale
- **B2B SaaS:** HR va ish vaqti SaaS'i (Flex uslubida): multi-tenant, rollar, tasdiqlash jarayoni (결재); yoki CRM va chat vidjeti (Channel Talk uslubida)
- **Enterprise AI Agent:** ichki hujjatlar bo'yicha AI assistent: PDF, **HWP**, Excel; ruxsatlar; manba ko'rsatish
- **Data Engineering:** real-time analitika: Kafka → Spark/Flink → ClickHouse → Superset
- **Smart Factory:** kamera orqali nuqsonlarni aniqlash (YOLO, anomaly detection), sintetik defekt rasmlari
- **Healthtech:** telemeditsina ilovasi (pastda batafsil)

---

## 7. Asosiy loyiha: Telemeditsina ilovasi (Node.js + Next.js + MongoDB)

### 7.1. Umumiy g'oya

Bemor simptomlarini yozadi. AI qaysi mutaxassisga borish kerakligini tavsiya qiladi, bemor shifokorga yoziladi, video orqali konsultatsiya oladi va elektron retsept oladi.

**Foydalanuvchi turlari:**
- **Bemor:** shifokor qidiradi, yoziladi, video qo'ng'iroq qiladi, retsept oladi
- **Shifokor:** ish jadvalini belgilaydi, qabul qiladi, retsept va xulosa yozadi
- **Admin:** shifokor litsenziyasini tasdiqlaydi, statistikani ko'radi

### 7.2. Foydalanuvchi oqimi

```
1. Bemor: "3 kundan beri boshim og'riyapti, isitmam bor"
        ↓
2. AI: tavsiya qilingan bo'limlar: Ichki kasalliklar (내과) 85%, Nevrologiya 10%
       ⚠️ "Agar to'satdan kuchli og'riq bo'lsa, 119 ga qo'ng'iroq qiling"
        ↓
3. Ichki kasalliklar shifokorlari ro'yxati: reyting, narx, bo'sh vaqtlar
        ↓
4. Vaqt tanlash → to'lov → tasdiq bildirishnomasi
        ↓
5. Belgilangan vaqtda video konsultatsiya (WebRTC)
        ↓
6. Shifokor xulosa va elektron retsept yozadi → dorixonaga yuboriladi
        ↓
7. Bemor sharh qoldiradi
```

### 7.3. Stack

| Qism | Texnologiya |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind, React Query, Zustand |
| Backend | Node.js + Express (TypeScript), Zod validatsiya |
| Ma'lumotlar bazasi | MongoDB + Mongoose (tranzaksiyalar uchun replica set) |
| Kesh va lock | Redis |
| Real-time va video | Socket.io (signaling + chat), WebRTC, TURN server |
| AI | LLM API + MongoDB Atlas Vector Search (RAG) |
| Auth | JWT (access + refresh token), bcrypt |
| Bildirishnomalar | E-mail, push, Kakao Alimtalk |
| To'lov | Toss Payments (test rejimi) |
| Test | Jest, Supertest, Playwright, k6 |
| Deploy | Docker Compose, GitHub Actions, Vercel (frontend), AWS yoki Render (backend) |

### 7.4. Arxitektura

```
[Next.js Web] ──→ [Node.js / Express API] ──→ [MongoDB]
                        │          │
                        │          └──→ [Redis: kesh, rate limit]
                        │
                        ├──→ [Triage moduli] ──→ [LLM + Atlas Vector Search]
                        │
                        └──→ [Socket.io signaling] ←── WebRTC ──→ Bemor ↔ Shifokor
```

### 7.5. Papka tuzilmasi (monorepo)

```
telemed/
├── apps/
│   ├── web/                    # Next.js
│   │   └── app/
│   │       ├── (patient)/      # bemor sahifalari
│   │       ├── doctor/         # shifokor paneli
│   │       ├── admin/
│   │       └── call/[id]/      # video konsultatsiya
│   └── api/                    # Node.js + Express
│       └── src/
│           ├── modules/
│           │   ├── auth/
│           │   ├── doctors/
│           │   ├── appointments/
│           │   ├── triage/     # AI qismi
│           │   ├── prescriptions/
│           │   └── payments/
│           ├── socket/         # WebRTC signaling
│           ├── middlewares/
│           └── app.ts
├── packages/shared/            # umumiy turlar va Zod sxemalar
└── docker-compose.yml          # mongo, redis, api, web
```

### 7.6. MongoDB sxemalari

```ts
// User
{ email, passwordHash, role: 'PATIENT' | 'DOCTOR' | 'ADMIN', name, phone }

// Doctor
{ userId, department: '내과' | '피부과' | ..., licenseNo, verified: Boolean,
  price, rating, bio }

// Slot (shifokorning bo'sh vaqti)
{ doctorId, start: Date, end: Date,
  status: 'OPEN' | 'HELD' | 'BOOKED', heldBy, heldUntil }

// Appointment
{ patientId, doctorId, slotId, symptomText,
  status: 'PENDING' | 'CONFIRMED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED',
  triage: { departments: [{ name, confidence }], urgency, emergency: Boolean } }

// Consultation
{ appointmentId, startedAt, endedAt, doctorNote }

// Prescription
{ appointmentId, items: [{ medicine, dosage, days }], note }

// Payment
{ appointmentId, amount, status, idempotencyKey }   // idempotencyKey: unique index

// Review
{ appointmentId, rating, comment }

// AuditLog (tibbiy ma'lumotga kim kirgani)
{ userId, action, resource, resourceId, at }
```

### 7.7. API ro'yxati (MVP)

```
POST   /auth/register, /auth/login, /auth/refresh
GET    /doctors?department=&date=
GET    /doctors/:id/slots
POST   /triage
POST   /appointments              (slotni HELD qiladi)
POST   /payments/confirm          (Idempotency-Key header bilan)
PATCH  /appointments/:id/status
POST   /prescriptions             (faqat DOCTOR)
GET    /me/appointments
Socket: join-room, offer, answer, ice-candidate, chat-message
```

### 7.8. Bitta vaqtni ikki kishi band qilolmasligi (eng muhim texnik qism)

MongoDB'da bu muammo atomik yangilash bilan hal qilinadi:

```ts
const slot = await Slot.findOneAndUpdate(
  { _id: slotId, status: 'OPEN' },          // faqat bo'sh bo'lsa
  { status: 'HELD', heldBy: userId, heldUntil: in10min },
  { new: true }
);
if (!slot) throw new ConflictError('Bu vaqt allaqachon band');
```

- To'lov o'tsa, **MongoDB tranzaksiyasi** ichida `Slot → BOOKED`, `Appointment` va `Payment` bir vaqtda yoziladi
- To'lov 10 daqiqada o'tmasa, slot avtomatik qaytadan ochiladi (cron job)
- **k6 bilan isbotlash:** 100 ta parallel so'rovdan faqat 1 tasi muvaffaqiyatli bo'lishi kerak. Natijani README'ga yozing

### 7.9. AI triage (simptomlar bo'yicha bo'lim tavsiyasi)

**Oqim:**

```
POST /triage { text: "3 kundan beri boshim og'riyapti, isitma bor" }
   ↓
1. Shoshilinch so'zlar filtri (qoidalar asosida) → emergency bo'lsa, darhol 119 ni ko'rsatadi
   ↓
2. Atlas Vector Search: o'xshash simptom → bo'lim yozuvlarini topadi
   ↓
3. LLM: topilgan kontekst asosida JSON qaytaradi (Zod bilan tekshiriladi)
   ↓
{ departments: [{ name: "내과", confidence: 0.85 }], urgency: "low", emergency: false }
```

**Rivojlantirish bosqichlari:**
1. **Oddiy:** LLM + prompt, JSON javob
2. **Kuchli:** RAG, tibbiy ma'lumotnoma asosida, manba ko'rsatiladi, hallucination kamayadi
3. **Eng kuchli:** AI Hub'dagi ochiq koreys tibbiy datasetlarida o'z klassifikatoringizni o'rgatish, accuracy va F1'ni README'da ko'rsatish

**Xavfsizlik qoidalari:**
- "Ko'krak og'rig'i", "nafas ololmayapman", "o'z joniga qasd qilish" kabi signallarda AI tavsiya bermaydi, darhol 119 yoki inqiroz yordam liniyasini ko'rsatadi
- AI **tashxis qo'ymaydi**, faqat bo'lim tavsiya qiladi. Bu UI'da aniq yoziladi

### 7.10. Intervyu uchun "kuchli" qismlar

1. **Concurrency:** atomik slot band qilish + k6 load test natijasi
2. **To'lovda idempotency:** tugma ikki marta bosilsa ham pul bir marta yechiladi
3. **Holat mashinasi:** `PENDING → CONFIRMED → IN_PROGRESS → COMPLETED / CANCELLED`
4. **Xavfsizlik:** shaxsiy ma'lumotlarni shifrlash, audit log, rollar bo'yicha ruxsat
5. **WebRTC:** NAT ortidagi foydalanuvchilar uchun TURN server, qayta ulanish logikasi
6. **Mas'uliyatli AI:** shoshilinch holat filtri, tashxis qo'ymaslik, baholash metrikalari

### 7.11. Koreyaga xos eslatmalar

- Koreyada telemeditsina (비대면 진료) hali **qonuniy cheklovlar ostida**, pilot dastur sifatida ishlaydi. README'da buni bilishingizni ko'rsating
- Shaxsiy ma'lumotlarni himoya qilish qonuni (개인정보보호법) bo'yicha tibbiy ma'lumotlar maxsus toifa hisoblanadi
- Haqiqiy bemor ma'lumotlarini ishlatmang, faqat test va sintetik ma'lumotlar

### 7.12. 8 haftalik reja

| Hafta | Ish |
|---|---|
| 1 | Monorepo, Docker Compose (Mongo replica set, Redis), auth va rollar |
| 2 | Shifokor profili, slotlar, qidiruv sahifasi |
| 3 | Band qilish (atomik + tranzaksiya), to'lov (Toss test rejimi) |
| 4 | AI triage va shoshilinch holat filtri |
| 5 | Socket.io signaling, WebRTC video, chat |
| 6 | Elektron retsept, bildirishnomalar, sharhlar, admin panel |
| 7 | RAG'ni yaxshilash, testlar (Jest, Playwright), k6 load test |
| 8 | CI/CD, deploy, README, arxitektura diagrammasi, demo video |

---

## 8. Ishga kirish bo'yicha umumiy maslahatlar

- **GitHub va README:** har bir loyiha uchun **"Muammo → Yechim → Natija (raqamlarda) → Nimani o'rgandim"** formatida yozing. Koreys texnik intervyulari (기술 면접) aynan shu tuzilmada savol beradi
- **Raqamlar:** TPS, latency, accuracy, foydalanuvchilar soni
- **Texnik blog:** velog.io yoki Medium'da loyihalaringiz haqida yozing. Koreys kompaniyalari buni juda qadrlaydi
- **Koding test:** Programmers yoki Baekjoon. Kuniga 1–2 masala
- **Koreys tili:** TOPIK 4+ imkoniyatlarni ancha kengaytiradi. Faqat ingliz tili bilan Coupang, Line, Moloco va global startaplarga kirish osonroq
- **Viza:** E-7 ish vizasi uchun odatda bakalavr darajasi va soha tajribasi kerak
- **Ish qidirish saytlari:** Wanted, Jumpit, Rocketpunch, LinkedIn, Programmers Career
- **Open source:** qabul qilingan PR'lar rezyumeda katta ustunlik beradi

---

## 9. Yakuniy tavsiya va yo'l xaritasi

**Asosiy qoida:** 2–3 ta chuqur, tugallangan, deploy qilingan va hujjatlashtirilgan loyiha 15 ta boshlangan loyihadan kuchliroq.

**Tavsiya etilgan kombinatsiya (profil: "AI'ni tushunadigan full stack muhandis"):**

| Bosqich | Loyiha | Muddat |
|---|---|---|
| 1 | Telemeditsina ilovasi (Node.js + Next.js + MongoDB, AI triage bilan) | 8 hafta |
| 2 | Kupon yoki chipta bron qilish tizimi (concurrency, load test) | 3–4 hafta |
| 3 | Koreys tilidagi RAG yoki Enterprise AI Agent (HWP qo'llab-quvvatlashi bilan) | 4–6 hafta |
| 4 | `physical_ai_scene`: sintetik ma'lumot + Sim-to-Real | 2–3 oy |
| Doimiy | Open source PR'lar, blog, algoritm masalalari | har hafta |
