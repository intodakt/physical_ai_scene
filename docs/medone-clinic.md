# MedOne Clinic

Klinika veb-sayti, ichida **qabulga yozilish**, **onlayn (video) qabul** va **AI yordamchi** bor.

Ish uch qismdan iborat va shu tartibda qilinadi:
1. **Klinika veb-sayti**
2. **Qabulga yozilish va onlayn qabul** (to'lov va SMS eslatmalar bilan)
3. **AI yordamchi (RAG):** klinikaning barcha ma'lumotlariga qarab javob beradi

---

## Stack

| Qism | Texnologiya |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Node.js, Express |
| Ma'lumotlar bazasi | MongoDB |
| Video qo'ng'iroq | WebRTC, Socket.io |
| To'lov | Payme, Click |
| SMS | Eskiz.uz |
| AI | RAG: LLM API (masalan, Claude yoki OpenAI) + MongoDB Atlas Vector Search |
| Tillar | O'zbek, rus, ingliz, koreys |

---

## 1-QISM: Klinika veb-sayti

Maqsad: odamlar klinika haqida hamma narsani bilib oladigan sayt.

### Sahifalar

| Sahifa | Nima bor |
|---|---|
| **Bosh sahifa** | Katta banner, "Qabulga yozilish" va "AI yordamchi" tugmalari, bo'limlar, shifokorlar, mijozlar fikri |
| **Bo'limlar** | Kardiologiya, Nevrologiya, Pediatriya, Ginekologiya va boshqalar |
| **Shifokorlar** | Rasmi, ismi, mutaxassisligi, tajribasi, qaysi tillarda gaplashishi |
| **Xizmatlar va narxlar** | Xizmat nomi va narxi (so'mda) |
| **Biz haqimizda** | Klinika tarixi, uskunalar |
| **Aloqa** | Manzil, xarita, telefon, ish vaqti |

### Admin paneli

Admin sayt orqali quyidagilarni qo'shadi, o'zgartiradi va o'chiradi:
- Bo'limlar
- Shifokorlar
- Xizmatlar va narxlar

### Qadamlar

1. Loyihani yaratish: `web` (Next.js) va `api` (Express) papkalari, MongoDB ulanishi
2. Sayt dizayni: header (logotip, menyu, til tanlash, telefon) va footer
3. 4 tilni sozlash
4. Ma'lumotlar bazasi: bo'limlar, shifokorlar, xizmatlar
5. Sahifalarni yasash: bosh sahifa → bo'limlar → shifokorlar → narxlar → biz haqimizda → aloqa
6. Admin uchun kirish va admin paneli
7. Telefonda chiroyli ko'rinishini tekshirish

**1-qism natijasi:** 4 tilli klinika sayti.

---

## 2-QISM: Qabulga yozilish va onlayn qabul

Maqsad: bemor saytdan shifokorga yoziladi, to'laydi va klinikaga keladi yoki **video orqali** maslahat oladi.

### Qabul turlari

| Tur | Qanday |
|---|---|
| **Klinikada qabul** | Bemor vaqt band qiladi va belgilangan vaqtda klinikaga keladi |
| **Onlayn qabul** | Bemor belgilangan vaqtda saytdan shifokor bilan video orqali gaplashadi |

### Bemor uchun jarayon

```
1. Saytga telefon raqami bilan kiradi (SMS kod orqali)
        ↓
2. Qabul turini tanlaydi: klinikada yoki onlayn
        ↓
3. Shifokorni tanlaydi
        ↓
4. Bo'sh vaqtni tanlaydi (masalan, ertaga 10:00)
        ↓
5. To'laydi: Payme, Click yoki "klinikada to'layman"
        ↓
6. Tasdiq SMS'i keladi. Qabuldan 1 kun va 2 soat oldin eslatma SMS'i keladi
        ↓
7a. Klinikada qabul: belgilangan vaqtda klinikaga keladi
7b. Onlayn qabul: "Qo'ng'iroqqa kirish" tugmasini bosib, shifokor bilan video orqali gaplashadi
        ↓
8. Shifokorning xulosasi va retseptini shaxsiy kabinetida ko'radi
```

### Kim nima qiladi

| Kim | Nima qiladi |
|---|---|
| **Bemor** | Yoziladi, to'laydi, video qo'ng'iroqda gaplashadi, xulosa va retseptni ko'radi |
| **Shifokor** | Bo'sh vaqtlarini belgilaydi, qabullarini ko'radi, video qo'ng'iroq qiladi, xulosa va retsept yozadi |
| **Admin** | Barcha qabullar va to'lovlarni ko'radi |

### Muhim qoidalar

- **Bitta vaqtga faqat bitta bemor yoziladi.** Ikki kishi bir vaqtda bosganda vaqtni faqat bittasi oladi, ikkinchisiga "Bu vaqt band" degan xabar chiqadi.
- **Pul ikki marta yechilmaydi.** Tugma ikki marta bosilsa ham to'lov bir marta o'tadi.
- **Onlayn to'lov 10 daqiqada qilinmasa,** vaqt boshqalar uchun qayta ochiladi.
- **Video qo'ng'iroqqa faqat o'sha bemor va o'sha shifokor kira oladi.**
- **Bemor faqat o'z qabullari va retseptlarini ko'radi.**

### Qadamlar

1. Telefon raqam va SMS kod orqali kirish (Eskiz.uz)
2. Shifokor bo'sh vaqtlarini belgilaydigan sahifa
3. Shifokor sahifasida bo'sh vaqtlarni ko'rsatish
4. Qabulga yozilish: tur tanlash (klinikada yoki onlayn), bitta vaqtga bitta bemor qoidasi bilan
5. To'lov: Payme, Click va "klinikada to'layman"
6. SMS: tasdiq va eslatmalar (1 kun va 2 soat oldin)
7. Bemorning shaxsiy kabineti: "Mening qabullarim"
8. Shifokor paneli: "Bugungi qabullar"
9. Video qo'ng'iroq sahifasi (onlayn qabul uchun)
10. Shifokor xulosa va retsept yozadi, bemor kabinetida ko'radi

**2-qism natijasi:** saytda to'liq ishlaydigan qabul tizimi.

---

## 3-QISM: AI yordamchi (RAG)

Maqsad: klinika haqidagi **har qanday savolga klinikaning o'z ma'lumotlari asosida** javob beradigan AI yordamchi. U o'zidan narsa to'qimaydi, faqat klinika bazasidagi ma'lumotlarga qarab javob beradi.

### RAG nima (sodda qilib)

RAG: AI javob berishdan oldin **klinika bazasidan kerakli ma'lumotni qidirib topadi**, keyin faqat shu ma'lumotga tayanib javob yozadi.

```
Bemor savoli
    ↓
1. Klinika bazasidan savolga mos ma'lumotlar qidiriladi
    ↓
2. Topilgan ma'lumotlar + savol AI'ga beriladi
    ↓
3. AI faqat shu ma'lumotlarga qarab javob yozadi va manbani ko'rsatadi
```

### AI qaysi ma'lumotlarni biladi

AI klinikaning **butun bazasi** bilan bog'langan:

| Ma'lumot | Misol savol |
|---|---|
| **Bo'limlar** | "Sizda nevrolog bormi?" |
| **Shifokorlar** (tajriba, mutaxassislik, tillar) | "Koreys tilida gaplashadigan kardiolog bormi?" |
| **Xizmatlar va narxlar** | "MRT qancha turadi?" |
| **Shifokorlarning bo'sh vaqtlari** | "Ertaga pediatrga yozilsa bo'ladimi?" |
| **Klinika haqida** (manzil, ish vaqti, telefon, uskunalar) | "Shanba kuni ishlaysizlarmi?" |
| **Ko'p so'raladigan savollar (FAQ)** | "Tahlil topshirishdan oldin ovqat yesa bo'ladimi?" |
| **Simptomlar va bo'limlar bog'liqligi** | "Boshim og'riyapti, qaysi shifokorga boray?" |

### Ma'lumotlarning ikki turi

| Tur | Nima | Qanday olinadi |
|---|---|---|
| **Matnli ma'lumotlar** | Bo'limlar, shifokorlar haqida, xizmatlar tavsifi, klinika haqida, FAQ | **Vektor qidiruv (RAG)** orqali |
| **Tez o'zgaradigan ma'lumotlar** | Bo'sh vaqtlar, joriy narxlar | AI kerak bo'lganda **bazadan to'g'ridan-to'g'ri so'raydi** (tool calling) |

Bo'sh vaqtlar har daqiqada o'zgaradi. Shuning uchun AI ularni eski nusxadan emas, har safar bazadan yangisini oladi.

### Ma'lumotlar doim yangi bo'ladi

Admin panelda biror narsa o'zgarsa (yangi shifokor qo'shildi, narx o'zgardi, FAQ yozildi), **AI bazasi avtomatik yangilanadi**. Admin alohida hech narsa qilmaydi.

### Misol suhbat

```
Bemor: Koreys tilida gaplashadigan kardiolog bormi? Narxi qancha?

AI:    Ha, Kardiologiya bo'limida Dr. Kim Min-jun koreys va rus tillarida qabul qiladi.
       Konsultatsiya narxi: 250 000 so'm.
       Eng yaqin bo'sh vaqtlar: ertaga 10:00, 11:30.
       [Qabulga yozilish]

       Manba: Shifokorlar · Xizmatlar va narxlar
```

### Muhim qoidalar

- **AI faqat klinika ma'lumotlariga tayanadi.** Bazada javob bo'lmasa: *"Bu haqida ma'lumotim yo'q, iltimos +998 XX XXX XX XX raqamiga qo'ng'iroq qiling"*.
- **Har bir javobda manba ko'rsatiladi** (qaysi sahifa yoki bo'limdan olingani).
- **AI tashxis qo'ymaydi,** faqat qaysi shifokorga borishni tavsiya qiladi. Sahifada aniq yoziladi: "Bu tashxis emas".
- **Xavfli holatlarda shifokor tavsiya qilmaydi.** "Ko'kragim qattiq og'riyapti" yoki "nafas ololmayapman" kabi xabarlarda darhol **"103 ga qo'ng'iroq qiling!"** degan xabar chiqadi.
- **Faqat klinikada bor** bo'lim, shifokor va xizmatlarni tavsiya qiladi.
- **4 tilda ishlaydi:** bemor qaysi tilda yozsa, shu tilda javob beradi.
- **Javobdan to'g'ridan-to'g'ri qabulga yozilish** mumkin.

### Texnologiyalar

| Qism | Texnologiya |
|---|---|
| Vektor qidiruv | MongoDB Atlas Vector Search |
| Embedding (matnni vektorga aylantirish) | Ko'p tilli embedding modeli |
| AI modeli | LLM API (masalan, Claude yoki OpenAI), tool calling bilan |
| Javobni ekranga chiqarish | Streaming (javob so'zma-so'z chiqadi) |

### Qadamlar

1. **FAQ bo'limi:** admin panelga savol-javoblar qo'shish imkoniyati (4 tilda)
2. **Ma'lumotlarni bo'laklash:** har bir bo'lim, shifokor, xizmat, FAQ va "Biz haqimizda" matnini kichik bo'laklarga ajratish
3. **Vektorlash:** bo'laklarni embedding orqali vektorga aylantirib, MongoDB'ga saqlash
4. **Avtomatik yangilash:** admin biror narsani o'zgartirsa, shu ma'lumotning vektori ham yangilanadi
5. **Qidiruv:** savolga eng mos 5–8 ta bo'lakni topish
6. **Bazadan jonli so'rovlar (tools):** "bo'sh vaqtlarni ko'r", "narxni ko'r", "shifokorlarni qidir"
7. **Xavfli holatlar filtri** (4 tilda kalit so'zlar), AI'dan oldin ishlaydi
8. **AI javobi:** tizim ko'rsatmasi (qoidalar), topilgan ma'lumotlar, savol → javob va manbalar
9. **Chat sahifasi:** suhbat oynasi, javob so'zma-so'z chiqadi, manbalar, "Qabulga yozilish" tugmasi, "Bu tashxis emas" ogohlantirishi
10. **Saytning har bir sahifasida** pastki o'ng burchakda AI chat tugmasi
11. **Sinash:** 4 tilda 40–50 ta savol tayyorlab, javoblar to'g'ri ma'lumotga asoslanganini va to'qib chiqarilmaganini tekshirish

**3-qism natijasi:** klinikaning barcha ma'lumotlarini biladigan, aniq va manbali javob beradigan, bemorni to'g'ridan-to'g'ri qabulga yozdira oladigan AI yordamchi.

---

## Oxirida

1. Saytni internetga joylash (deploy)
2. Hamma narsani boshidan oxirigacha sinab ko'rish: sayt → AI yordamchi → yozilish → to'lov → video qabul → retsept
3. README yozish: loyiha nima qiladi, qanday ishga tushiriladi, skrinshotlar

---

## Eslatma

- To'lov uchun **Payme va Click'ning test (sandbox) rejimi** ishlatiladi. Haqiqiy to'lov qabul qilish uchun klinika yuridik shaxs bo'lishi va ular bilan shartnoma tuzishi kerak.
- Haqiqiy klinikaga joriy qilishdan oldin shaxsiy ma'lumotlar va onlayn tibbiy xizmatlar bo'yicha qonun talablarini yurist bilan tekshirish kerak.
