# MedOne Clinic

Klinika veb-sayti, ichida **qabulga yozilish**, **onlayn (video) qabul** va **AI yordamchi** bor.

Ish uch qismdan iborat va shu tartibda qilinadi:
1. **Klinika veb-sayti**
2. **Qabulga yozilish va onlayn qabul** (to'lov va SMS eslatmalar bilan)
3. **AI yordamchi**

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
| AI | LLM API (masalan, Claude yoki OpenAI) |
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

## 3-QISM: AI yordamchi

Maqsad: bemor qaysi shifokorga borishni bilmasa, AI yordam beradi.

### Qanday ishlaydi

```
1. Bemor yozadi: "3 kundan beri boshim og'riyapti, isitmam bor"
        ↓
2. AI javob beradi: "Sizga Terapevt kerak"
        ↓
3. Shu bo'lim shifokorlari ko'rsatiladi va "Qabulga yozilish" tugmasi chiqadi
```

### Muhim qoidalar

- **AI tashxis qo'ymaydi,** faqat qaysi bo'lim shifokoriga borishni tavsiya qiladi. Buni sahifada aniq yozamiz: "Bu tashxis emas".
- **Xavfli holatlarda AI shifokor tavsiya qilmaydi.** Bemor "ko'kragim qattiq og'riyapti" yoki "nafas ololmayapman" deb yozsa, darhol **"103 ga qo'ng'iroq qiling!"** degan xabar chiqadi.
- AI faqat **klinikamizda bor bo'limlarni** tavsiya qiladi.
- AI 4 tilda ishlaydi: o'zbek, rus, ingliz, koreys.

### Qadamlar

1. Xavfli holatlarni aniqlaydigan filtr (4 tilda kalit so'zlar)
2. AI'ga savol yuborish va javobni olish (klinikadagi bo'limlar ro'yxati bilan)
3. AI yordamchi sahifasi: savol yozish joyi va javob kartochkasi
4. Javobdan keyin shu bo'lim shifokorlarini ko'rsatish va qabulga yozilishga o'tkazish
5. Xavfli holat uchun alohida qizil ogohlantirish ekrani
6. 20–30 ta misol bilan AI javoblarini sinab ko'rish

**3-qism natijasi:** bemorga to'g'ri shifokorni topishga yordam beradigan AI.

---

## Oxirida

1. Saytni internetga joylash (deploy)
2. Hamma narsani boshidan oxirigacha sinab ko'rish: sayt → AI yordamchi → yozilish → to'lov → video qabul → retsept
3. README yozish: loyiha nima qiladi, qanday ishga tushiriladi, skrinshotlar

---

## Eslatma

- To'lov uchun **Payme va Click'ning test (sandbox) rejimi** ishlatiladi. Haqiqiy to'lov qabul qilish uchun klinika yuridik shaxs bo'lishi va ular bilan shartnoma tuzishi kerak.
- Haqiqiy klinikaga joriy qilishdan oldin shaxsiy ma'lumotlar va onlayn tibbiy xizmatlar bo'yicha qonun talablarini yurist bilan tekshirish kerak.
