# MedOne Clinic: 4 kunlik reja

> Klinika veb-sayti: qabulga yozilish, onlayn (video) qabul va RAG asosidagi AI yordamchi bilan.
> **Muddat:** 4 kun, kuniga 10–12 soat. Bunday tezlik uchun kodning katta qismi AI yordamchi bilan yoziladi, siz esa tekshirib va sinab borasiz.

---

## Mundarija

1. [Loyiha haqida](#1-loyiha-haqida)
2. [Ish tartibi](#2-ish-tartibi)
3. [Stack](#3-stack)
4. [Papka tuzilmasi](#4-papka-tuzilmasi)
5. [1-kun: To'liq veb-sayt](#5-1-kun-toliq-veb-sayt)
6. [2-kun: Qabulga yozilish va to'lov](#6-2-kun-qabulga-yozilish-va-tolov)
7. [3-kun: Onlayn qabul va AI yordamchi](#7-3-kun-onlayn-qabul-va-ai-yordamchi)
8. [4-kun: Admin panel va ishga tushirish](#8-4-kun-admin-panel-va-ishga-tushirish)
9. [Muhim qoidalar](#9-muhim-qoidalar)
10. [Vaqt yetmasa](#10-vaqt-yetmasa)
11. [Eslatmalar](#11-eslatmalar)

---

## 1. Loyiha haqida

**MedOne Clinic** — klinikaning veb-sayti. Unda:

| Qism | Nima qiladi |
|---|---|
| **Veb-sayt** | Klinika, bo'limlar, shifokorlar, narxlar va aloqa haqida ma'lumot |
| **Qabulga yozilish** | Klinikaga kelib yoki onlayn ko'rinish uchun vaqt band qilish va to'lash |
| **Onlayn qabul** | Shifokor bilan video orqali gaplashish |
| **AI yordamchi** | Klinika ma'lumotlari asosida savollarga javob beradi va to'g'ri shifokorni topib beradi |
| **Admin panel** | Saytdagi barcha ma'lumotlarni boshqarish |

**Foydalanuvchilar:** bemor, shifokor, admin.
**Tillar:** o'zbek, rus, ingliz, koreys.

---

## 2. Ish tartibi

```
1-kun                 2-kun                    3-kun                      4-kun
TO'LIQ VEB-SAYT  →  QABULGA YOZILISH     →  ONLAYN QABUL           →  ADMIN PANEL
(barcha sahifalar)   + TO'LOV + SMS            + AI YORDAMCHI (RAG)       + DEPLOY + TEST
```

- **Avval sayt to'liq tayyor bo'ladi**, keyin unga bo'limlar birma-bir qo'shiladi.
- Admin panel tayyor bo'lguncha (1–3-kunlar) ma'lumotlar **seed skripti** orqali bazaga yoziladi.
- Har kun oxirida: commit, push va ishlaydigan holat.

---

## 3. Stack

| Qism | Texnologiya |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui |
| Tillar | next-intl (uz, ru, en, ko) |
| Backend | Node.js, Express, TypeScript |
| Ma'lumotlar bazasi | MongoDB Atlas |
| Kirish | Telefon raqam + SMS kod (Eskiz.uz) |
| To'lov | Payme, Click (test rejimi) |
| Video qo'ng'iroq | WebRTC, Socket.io |
| AI | RAG: LLM API + MongoDB Atlas Vector Search |
| Deploy | Vercel (sayt), Render (backend) |

---

## 4. Papka tuzilmasi

```
medone-clinic/
├── web/                         # Next.js sayt
│   ├── app/[locale]/
│   │   ├── (site)/              # bosh sahifa, bo'limlar, shifokorlar, narxlar, biz haqimizda, aloqa
│   │   ├── login/
│   │   ├── booking/             # qabulga yozilish
│   │   ├── cabinet/             # bemor kabineti
│   │   ├── call/[id]/           # video qabul
│   │   ├── assistant/           # AI yordamchi
│   │   ├── doctor/              # shifokor paneli
│   │   └── admin/               # admin panel
│   ├── components/
│   ├── messages/                # uz.json, ru.json, en.json, ko.json
│   └── lib/
│
├── api/                         # Express backend
│   ├── src/
│   │   ├── models/              # ma'lumotlar modellari
│   │   ├── routes/              # API yo'llari
│   │   ├── services/            # biznes logika (booking, payment, sms, ai)
│   │   ├── middlewares/         # auth, rollar, validatsiya, xatolar
│   │   ├── socket.ts            # video qo'ng'iroq uchun
│   │   └── server.ts
│   └── scripts/seed.ts          # boshlang'ich ma'lumotlar
│
└── README.md
```

---

## 5. 1-kun: To'liq veb-sayt

**Maqsad:** kun oxirida klinika sayti 4 tilda to'liq ishlaydi.

### 1-blok: Loyiha poydevori (2 soat)
- [ ] `web` (Next.js) va `api` (Express) papkalarini yaratish
- [ ] MongoDB Atlas'ga ulanish
- [ ] `.env` va `.env.example`
- [ ] Tailwind va shadcn/ui o'rnatish
- [ ] 4 tilni sozlash (next-intl)

### 2-blok: Ma'lumotlar va API (2 soat)
- [ ] Modellar: **Bo'lim**, **Shifokor**, **Xizmat**, **Sozlamalar** (manzil, telefon, ish vaqti), **FAQ**
- [ ] Ochiq API'lar: bo'limlar, shifokorlar, xizmatlar, sozlamalar, FAQ
- [ ] Seed skripti: 8 ta bo'lim, 16 ta shifokor, 40 ta xizmat, 15 ta FAQ (4 tilda)

### 3-blok: Sayt dizayni (1.5 soat)
- [ ] **Header:** logotip, menyu, til tanlash, telefon, "Qabulga yozilish" tugmasi
- [ ] **Footer:** manzil, telefon, ish vaqti, ijtimoiy tarmoqlar
- [ ] Mobil menyu

### 4-blok: Sahifalar (5 soat)
- [ ] **Bosh sahifa:** banner, "Qabulga yozilish" va "AI yordamchi" tugmalari, bo'limlar, shifokorlar, raqamlar, mijozlar fikri
- [ ] **Bo'limlar:** ro'yxat va har bir bo'lim sahifasi
- [ ] **Shifokorlar:** ro'yxat (bo'lim va til bo'yicha filtr) va har bir shifokor sahifasi
- [ ] **Xizmatlar va narxlar:** bo'limlar bo'yicha guruhlangan jadval, qidiruv
- [ ] **Biz haqimizda**
- [ ] **Aloqa:** xarita, manzil, telefon, ish vaqti
- [ ] **FAQ:** ko'p so'raladigan savollar

### 5-blok: Tekshiruv (0.5 soat)
- [ ] Telefonda ko'rinishi
- [ ] 4 tilda barcha sahifalar

### ✅ 1-kun natijasi
- [ ] Barcha sahifalar 4 tilda ishlaydi
- [ ] Ma'lumotlar bazadan keladi
- [ ] Telefonda chiroyli ko'rinadi

---

## 6. 2-kun: Qabulga yozilish va to'lov

**Maqsad:** bemor saytga kiradi, qabulga yoziladi va to'laydi.

### 1-blok: Kirish (2 soat)
- [ ] **Foydalanuvchi** modeli: telefon, ism, rol (bemor, shifokor, admin)
- [ ] SMS kod yuborish va tekshirish (Eskiz.uz; sinov uchun kod konsolga chiqadi)
- [ ] Kirish sahifasi: telefon raqam → SMS kod
- [ ] Rollar bo'yicha ruxsat tekshiruvi

### 2-blok: Bo'sh vaqtlar va yozilish (3.5 soat)
- [ ] **Vaqt (slot)** modeli: shifokor, sana, boshlanish va tugash vaqti, holati
- [ ] **Qabul** modeli: bemor, shifokor, vaqt, turi (klinikada yoki onlayn), holati
- [ ] Seed: shifokorlarga 2 haftalik bo'sh vaqtlar
- [ ] Shifokor sahifasida bo'sh vaqtlarni ko'rsatish
- [ ] Qabulga yozilish API'si: **bitta vaqtga faqat bitta bemor**
- [ ] Shu qoida uchun test: 50 ta bir vaqtdagi so'rovdan faqat 1 tasi o'tadi

### 3-blok: Yozilish sahifasi (2 soat)
- [ ] Qadamma-qadam: qabul turi → bo'lim → shifokor → sana va vaqt → tasdiqlash
- [ ] Kirmagan bo'lsa, shu yerning o'zida SMS orqali kirish

### 4-blok: To'lov (2.5 soat)
- [ ] **To'lov** modeli
- [ ] Payme va Click test rejimi
- [ ] "Klinikada to'layman" varianti
- [ ] **Pul ikki marta yechilmasligi** uchun himoya
- [ ] To'lov 10 daqiqada qilinmasa, vaqt qayta ochiladi

### 5-blok: SMS va kabinet (1.5 soat)
- [ ] Tasdiq SMS'i va eslatmalar (1 kun va 2 soat oldin)
- [ ] Bemor kabineti: "Mening qabullarim" (kelgusi, o'tgan, bekor qilish)

### ✅ 2-kun natijasi
- [ ] Bemor SMS bilan kiradi, yoziladi va to'laydi (test rejimida)
- [ ] Bitta vaqtga ikki kishi yozila olmaydi (test bilan isbotlangan)
- [ ] Qabul bemor kabinetida ko'rinadi

---

## 7. 3-kun: Onlayn qabul va AI yordamchi

**Maqsad:** video qabul ishlaydi va AI yordamchi klinika ma'lumotlari asosida javob beradi.

### 1-blok: Shifokor paneli (1.5 soat)
- [ ] "Bugungi qabullar" ro'yxati
- [ ] O'z bo'sh vaqtlarini belgilash
- [ ] Onlayn qabul uchun "Qo'ng'iroqqa kirish" tugmasi

### 2-blok: Video qabul (3 soat)
- [ ] Socket.io serveri: faqat shu qabulning bemori va shifokori kira oladi
- [ ] WebRTC orqali video va ovoz
- [ ] Tugmalar: mikrofon, kamera, qo'ng'iroqni tugatish
- [ ] Internet sekin bo'lsa "faqat ovoz" rejimi
- [ ] Ikki xil qurilmada sinash

### 3-blok: Xulosa va retsept (1 soat)
- [ ] Shifokor qabuldan keyin xulosa va retsept yozadi
- [ ] Bemor ularni kabinetida ko'radi

### 4-blok: AI yordamchi: ma'lumotlarni tayyorlash (2 soat)
- [ ] Bo'limlar, shifokorlar, xizmatlar, FAQ va "Biz haqimizda" matnlarini kichik bo'laklarga ajratish
- [ ] Bo'laklarni vektorga aylantirib bazaga saqlash (Atlas Vector Search)
- [ ] Savolga eng mos bo'laklarni topadigan qidiruv

### 5-blok: AI yordamchi: javob berish (2.5 soat)
- [ ] **Xavfli holatlar filtri:** "ko'krak og'rig'i", "nafas ololmayapman" kabi so'zlarda darhol "103 ga qo'ng'iroq qiling!"
- [ ] AI bazadan jonli ma'lumot oladi: bo'sh vaqtlar, narxlar, shifokorlar
- [ ] AI faqat topilgan ma'lumotga tayanib javob beradi va manbani ko'rsatadi
- [ ] Bemor qaysi tilda yozsa, shu tilda javob beradi

### 6-blok: AI chat sahifasi (1 soat)
- [ ] Suhbat oynasi, javob so'zma-so'z chiqadi
- [ ] Javob ostida manbalar va "Qabulga yozilish" tugmasi
- [ ] "Bu tashxis emas" ogohlantirishi
- [ ] Har bir sahifada pastki o'ng burchakda AI chat tugmasi

### ✅ 3-kun natijasi
- [ ] Bemor va shifokor video orqali gaplashadi
- [ ] Bemor retseptni kabinetida ko'radi
- [ ] AI narx, shifokor, bo'sh vaqt va ish vaqti haqidagi savollarga to'g'ri javob beradi
- [ ] Xavfli holatlarda AI shifokor tavsiya qilmaydi

---

## 8. 4-kun: Admin panel va ishga tushirish

**Maqsad:** admin saytni to'liq boshqaradi, loyiha internetda ishlaydi.

### 1-blok: Admin panel asosi (1.5 soat)
- [ ] Admin kirishi va himoyalangan sahifalar
- [ ] Yon menyu, jadval komponenti (qidiruv va sahifalash)
- [ ] 4 tilda matn kiritish maydoni (har til uchun alohida tab)
- [ ] Rasm yuklash

### 2-blok: Kontentni boshqarish (3 soat)
- [ ] **Bo'limlar:** qo'shish, o'zgartirish, o'chirish
- [ ] **Shifokorlar:** qo'shish, o'zgartirish, o'chirish (kirish akkaunti bilan)
- [ ] **Xizmatlar va narxlar**
- [ ] **FAQ**
- [ ] **Sozlamalar:** manzil, telefon, ish vaqti, "Biz haqimizda" matni

### 3-blok: Qabullar va hisobot (1.5 soat)
- [ ] Shifokorlar jadvalini boshqarish
- [ ] Barcha qabullar va to'lovlar ro'yxati (filtr bilan)
- [ ] Oddiy hisobot: bugungi va oylik qabullar, daromad, eng band shifokorlar

### 4-blok: AI'ni admin panel bilan bog'lash (1 soat)
- [ ] Admin biror narsani o'zgartirsa, AI ma'lumotlari **avtomatik yangilanadi**
- [ ] Sinov: yangi shifokor qo'shib, AI'dan u haqida so'rash

### 5-blok: Tekshiruv va xavfsizlik (1.5 soat)
- [ ] Bemor boshqa bemorning qabulini, retseptini va qo'ng'irog'ini ko'ra olmaydi
- [ ] SMS kodi, AI chat va kirish uchun so'rovlar soni cheklangan
- [ ] AI'ni 4 tilda 40 ta savol bilan sinash

### 6-blok: Deploy (2 soat)
- [ ] Backend → Render, sayt → Vercel
- [ ] Payme va Click test webhook manzillari
- [ ] Demo akkauntlar: bemor, shifokor, admin
- [ ] Internetdagi saytda boshidan oxirigacha sinash:
  sayt → AI yordamchi → yozilish → to'lov → video qabul → retsept

### 7-blok: README (1 soat)
- [ ] Loyiha nima qiladi, skrinshotlar
- [ ] Qanday ishga tushiriladi
- [ ] Demo havola va demo akkauntlar

### ✅ 4-kun natijasi
- [ ] Admin saytdagi hamma narsani o'zgartira oladi va o'zgarish saytda darhol ko'rinadi
- [ ] AI yangi ma'lumotlarni avtomatik biladi
- [ ] Sayt internetda ishlaydi
- [ ] README tayyor

---

## 9. Muhim qoidalar

### Qabul va to'lov
- Bitta vaqtga **faqat bitta bemor** yoziladi
- Pul **ikki marta yechilmaydi**
- Onlayn to'lov 10 daqiqada qilinmasa, vaqt **qayta ochiladi**

### Xavfsizlik
- Bemor **faqat o'z** qabullari, retseptlari va qo'ng'iroqlarini ko'radi
- Video qo'ng'iroqqa **faqat o'sha bemor va o'sha shifokor** kira oladi
- Admin panelga **faqat admin** kira oladi

### AI yordamchi
- **Faqat klinika ma'lumotlariga** tayanadi, javob bo'lmasa "ma'lumotim yo'q, qo'ng'iroq qiling" deydi
- Har bir javobda **manba** ko'rsatiladi
- **Tashxis qo'ymaydi**
- Xavfli holatlarda **"103 ga qo'ng'iroq qiling!"**
- Faqat **klinikada bor** bo'lim, shifokor va xizmatlarni tavsiya qiladi

---

## 10. Vaqt yetmasa

Quyidagilarni keyinga qoldirish mumkin (yuqoridagisi birinchi):

1. Admin paneldagi hisobot
2. SMS eslatmalar (tasdiq SMS'i qoladi)
3. Click (faqat Payme qoladi)
4. Koreys va ingliz tilidagi kontent (sayt tugmalari 4 tilda qoladi)
5. "Faqat ovoz" rejimi

**Qisqartirib bo'lmaydi:** bitta vaqtga bitta bemor qoidasi, to'lov himoyasi, ruxsatlar, AI'dagi xavfli holatlar filtri, video qabul, admin panelning asosiy qismi, deploy.

---

## 11. Eslatmalar

- To'lov **Payme va Click'ning test rejimida** ishlaydi. Haqiqiy to'lov uchun klinika yuridik shaxs bo'lishi va ular bilan shartnoma tuzishi kerak.
- Haqiqiy klinikaga joriy qilishdan oldin **shaxsiy ma'lumotlar va onlayn tibbiy xizmatlar** bo'yicha qonun talablarini yurist bilan tekshirish kerak.
- Demo'da faqat **o'ylab topilgan ma'lumotlar** ishlatiladi, haqiqiy bemor ma'lumotlari yo'q.
