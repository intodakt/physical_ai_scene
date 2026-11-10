# MedOne Clinic

Klinika veb-sayti, ichida **onlayn qabul** bo'limi bor.

Ish ikki qismdan iborat va shu tartibda qilinadi:
1. **Avval:** klinika veb-sayti
2. **Keyin:** saytga onlayn qabul qo'shiladi

---

## Stack

| Qism | Texnologiya |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Node.js, Express |
| Ma'lumotlar bazasi | MongoDB |
| Video qo'ng'iroq | WebRTC, Socket.io |
| Tillar | O'zbek, rus, ingliz, koreys |

---

## 1-QISM: Klinika veb-sayti

Maqsad: odamlar klinika haqida hamma narsani bilib oladigan sayt.

### Sahifalar

| Sahifa | Nima bor |
|---|---|
| **Bosh sahifa** | Katta banner, "Qabulga yozilish" tugmasi, bo'limlar, shifokorlar, mijozlar fikri |
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

**1-qism natijasi:** internetda ishlaydigan, 4 tilli klinika sayti.

---

## 2-QISM: Onlayn qabul

Maqsad: bemor saytdan shifokorga yozilib, **video orqali** maslahat oladi.

### Bemor uchun jarayon

```
1. Saytga telefon raqami bilan kiradi
        ↓
2. Shifokorni tanlaydi
        ↓
3. Bo'sh vaqtni tanlaydi (masalan, ertaga 10:00)
        ↓
4. Qabulni tasdiqlaydi
        ↓
5. Belgilangan vaqtda "Qo'ng'iroqqa kirish" tugmasini bosadi
        ↓
6. Shifokor bilan video orqali gaplashadi
        ↓
7. Shifokorning xulosasi va retseptini shaxsiy kabinetida ko'radi
```

### Kim nima qiladi

| Kim | Nima qiladi |
|---|---|
| **Bemor** | Yoziladi, video qo'ng'iroqda gaplashadi, xulosa va retseptni ko'radi |
| **Shifokor** | Bo'sh vaqtlarini belgilaydi, qabullarini ko'radi, video qo'ng'iroq qiladi, xulosa va retsept yozadi |
| **Admin** | Barcha qabullarni ko'radi |

### Muhim qoidalar

- **Bitta vaqtga faqat bitta bemor yoziladi.** Ikki kishi bir vaqtda bosganda vaqtni faqat bittasi oladi, ikkinchisiga "Bu vaqt band" degan xabar chiqadi.
- **Video qo'ng'iroqqa faqat o'sha bemor va o'sha shifokor kira oladi.**
- **Bemor faqat o'z qabullari va retseptlarini ko'radi.**

### Qadamlar

1. Bemor uchun telefon raqam orqali kirish
2. Shifokor bo'sh vaqtlarini belgilaydigan sahifa
3. Shifokor sahifasida bo'sh vaqtlarni ko'rsatish
4. Qabulga yozilish (bitta vaqtga bitta bemor qoidasi bilan)
5. Bemorning shaxsiy kabineti: "Mening qabullarim"
6. Shifokor paneli: "Bugungi qabullar"
7. Video qo'ng'iroq sahifasi
8. Shifokor xulosa va retsept yozadi, bemor kabinetida ko'radi

**2-qism natijasi:** saytda to'liq ishlaydigan onlayn qabul.

---

## Oxirida

1. Saytni internetga joylash (deploy)
2. Hamma narsani boshidan oxirigacha sinab ko'rish
3. README yozish: loyiha nima qiladi, qanday ishga tushiriladi, skrinshotlar

---

## Keyinroq qo'shish mumkin

Asosiy ish tugagandan keyin, xohlasangiz:
- Onlayn to'lov (Payme, Click)
- SMS eslatmalar
- AI yordamchi: "Qaysi shifokorga borishim kerak?"
- Klinikaga kelib ko'rinish uchun yozilish
