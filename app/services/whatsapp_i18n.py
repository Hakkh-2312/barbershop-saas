from datetime import date

DEFAULT_LANGUAGE = "ar"

DAY_NAMES: dict[str, list[str]] = {
    "ar": ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"],
    "he": ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"],
    "en": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ar": {
        "welcome_header": "القائمة الرئيسية",
        "welcome_body": "مرحباً بكم في {shop_name}! كيف يمكننا مساعدتك؟",
        "menu_button": "اختر",
        "menu_book": "حجز موعد",
        "menu_language": "تغيير اللغة",
        "menu_call": "اتصل بنا",
        "menu_address": "العنوان",
        "lang_header": "اللغة",
        "lang_body": "الرجاء اختيار لغتك المفضلة",
        "lang_ar": "العربية",
        "lang_he": "עברית",
        "lang_en": "English",
        "more_options": "المزيد",
        "service_header": "الخدمات",
        "service_body": "ما هي الخدمة التي ترغب بحجزها؟",
        "no_services": "عذراً، لم يتم إعداد أي خدمات بعد.",
        "booking_unavailable": "عذراً، لا يمكن الحجز حالياً. يرجى التواصل مع المتجر مباشرة.",
        "date_header": "اختر التاريخ",
        "date_body": "اختر التاريخ المناسب لك",
        "no_dates": "عذراً، لا توجد مواعيد متاحة خلال الأسبوعين القادمين.",
        "slot_header": "اختر الوقت",
        "slot_body": "الأوقات المتاحة يوم {date}",
        "no_slots": "عذراً، لا توجد أوقات متاحة في هذا اليوم.",
        "booking_conflict": "عذراً، تم حجز هذا الموعد للتو. الرجاء اختيار وقت آخر.",
        "booking_error": "عذراً، حدث خطأ. الرجاء المحاولة مرة أخرى.",
        "booking_summary": (
            "تم تأكيد حجزك بنجاح! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nنراكم قريباً!"
        ),
        "call_reply": "يمكنكم الاتصال بنا على:\n{phone}",
        "call_not_set": "عذراً، رقم الهاتف غير متوفر حالياً.",
        "address_reply": "📍 عنواننا:\n{address}",
        "address_not_set": "عذراً، العنوان غير متوفر حالياً.",
        "ask_name": "قبل أن نبدأ، ما اسمك؟",
        "appt_header": "موعدك الحالي",
        "appt_body": "لديك موعد: {service_name}\n📅 {date}\n🕐 {time}\nماذا تريد أن تفعل؟",
        "appt_reschedule": "إعادة الجدولة",
        "appt_cancel": "إلغاء الموعد",
        "appt_cancelled": "تم إلغاء موعدك. ✅",
        "appt_confirm": "سأحضر",
        "appt_confirmed": "رائع، نراك حينها! ✅",
        "reschedule_summary": (
            "تم تعديل موعدك بنجاح! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nنراكم قريباً!"
        ),
        "dashboard_booking_confirmation": (
            "تم حجز موعد لك! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nنراكم قريباً!"
        ),
        "dashboard_cancellation_confirmation": (
            "تم إلغاء موعدك مع {shop_name} يوم {date} الساعة {time}."
        ),
        "dashboard_reschedule_confirmation": (
            "تم تغيير موعدك مع {shop_name}! ✅\n📅 {date}\n🕐 {time}\nنراكم قريباً!"
        ),
    },
    "he": {
        "welcome_header": "תפריט ראשי",
        "welcome_body": "ברוכים הבאים ל-{shop_name}! איך נוכל לעזור?",
        "menu_button": "בחר",
        "menu_book": "קביעת תור",
        "menu_language": "שינוי שפה",
        "menu_call": "התקשרו אלינו",
        "menu_address": "כתובת",
        "lang_header": "שפה",
        "lang_body": "אנא בחרו את השפה המועדפת",
        "lang_ar": "العربية",
        "lang_he": "עברית",
        "lang_en": "English",
        "more_options": "עוד",
        "service_header": "שירותים",
        "service_body": "איזה שירות תרצו להזמין?",
        "no_services": "מצטערים, עדיין לא הוגדרו שירותים.",
        "booking_unavailable": "מצטערים, לא ניתן להזמין תור כרגע. אנא צרו קשר ישירות עם העסק.",
        "date_header": "בחרו תאריך",
        "date_body": "בחרו תאריך מתאים",
        "no_dates": "מצטערים, אין תורים פנויים בשבועיים הקרובים.",
        "slot_header": "בחרו שעה",
        "slot_body": "שעות פנויות ביום {date}",
        "no_slots": "מצטערים, אין שעות פנויות ביום זה.",
        "booking_conflict": "מצטערים, התור הזה נתפס הרגע. אנא בחרו שעה אחרת.",
        "booking_error": "מצטערים, אירעה שגיאה. נסו שוב.",
        "booking_summary": (
            "התור אושר בהצלחה! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nנתראה בקרוב!"
        ),
        "call_reply": "ניתן להתקשר אלינו:\n{phone}",
        "call_not_set": "מצטערים, מספר הטלפון אינו זמין כרגע.",
        "address_reply": "📍 הכתובת שלנו:\n{address}",
        "address_not_set": "מצטערים, הכתובת אינה זמינה כרגע.",
        "ask_name": "לפני שנתחיל, מה השם שלך?",
        "appt_header": "התור שלך",
        "appt_body": "יש לך תור: {service_name}\n📅 {date}\n🕐 {time}\nמה תרצו לעשות?",
        "appt_reschedule": "שינוי מועד",
        "appt_cancel": "ביטול התור",
        "appt_cancelled": "התור בוטל. ✅",
        "appt_confirm": "אגיע",
        "appt_confirmed": "מעולה, נתראה אז! ✅",
        "reschedule_summary": (
            "התור עודכן בהצלחה! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nנתראה בקרוב!"
        ),
        "dashboard_booking_confirmation": (
            "נקבע לך תור! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nנתראה בקרוב!"
        ),
        "dashboard_cancellation_confirmation": (
            "התור שלך עם {shop_name} בתאריך {date} בשעה {time} בוטל."
        ),
        "dashboard_reschedule_confirmation": (
            "התור שלך עם {shop_name} עודכן! ✅\n📅 {date}\n🕐 {time}\nנתראה בקרוב!"
        ),
    },
    "en": {
        "welcome_header": "Main Menu",
        "welcome_body": "Welcome to {shop_name}! How can we help you?",
        "menu_button": "Choose",
        "menu_book": "Book an appointment",
        "menu_language": "Change language",
        "menu_call": "Call the shop",
        "menu_address": "Address",
        "lang_header": "Language",
        "lang_body": "Please choose your preferred language",
        "lang_ar": "العربية",
        "lang_he": "עברית",
        "lang_en": "English",
        "more_options": "More options",
        "service_header": "Services",
        "service_body": "Which service would you like to book?",
        "no_services": "Sorry, no services have been set up yet.",
        "booking_unavailable": (
            "Sorry, booking isn't available right now. Please contact the shop directly."
        ),
        "date_header": "Choose a date",
        "date_body": "Choose a date that works for you",
        "no_dates": "Sorry, nothing available in the next two weeks.",
        "slot_header": "Choose a time",
        "slot_body": "Available times on {date}",
        "no_slots": "Sorry, no times available on this day.",
        "booking_conflict": "Sorry, that slot was just taken. Please pick another time.",
        "booking_error": "Sorry, something went wrong. Please try again.",
        "booking_summary": (
            "Your booking is confirmed! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nSee you soon!"
        ),
        "call_reply": "You can reach us at:\n{phone}",
        "call_not_set": "Sorry, no phone number is set up yet.",
        "address_reply": "📍 Our address:\n{address}",
        "address_not_set": "Sorry, no address is set up yet.",
        "ask_name": "Before we start, what's your name?",
        "appt_header": "Your appointment",
        "appt_body": (
            "You have an appointment: {service_name}\n📅 {date}\n🕐 {time}\n"
            "What would you like to do?"
        ),
        "appt_reschedule": "Reschedule",
        "appt_cancel": "Cancel appointment",
        "appt_cancelled": "Your appointment has been cancelled. ✅",
        "appt_confirm": "I'll be there",
        "appt_confirmed": "Great, see you then! ✅",
        "reschedule_summary": (
            "Your appointment has been updated! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nSee you soon!"
        ),
        "dashboard_booking_confirmation": (
            "An appointment has been booked for you! ✅\n{shop_name}\n{service_name} - {price} ₪\n"
            "📅 {date}\n🕐 {time}\nSee you soon!"
        ),
        "dashboard_cancellation_confirmation": (
            "Your appointment with {shop_name} on {date} at {time} has been cancelled."
        ),
        "dashboard_reschedule_confirmation": (
            "Your appointment with {shop_name} has been updated! ✅\n"
            "📅 {date}\n🕐 {time}\nSee you soon!"
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    strings = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    template = strings.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    return template.format(**kwargs) if kwargs else template


def day_name(lang: str, day_of_week: int) -> str:
    names = DAY_NAMES.get(lang, DAY_NAMES[DEFAULT_LANGUAGE])
    return names[day_of_week]


def format_date_row_title(lang: str, d: date) -> str:
    day_of_week = (d.weekday() + 1) % 7
    return f"{day_name(lang, day_of_week)} {d.day}/{d.month}"


def format_date_full(lang: str, d: date) -> str:
    day_of_week = (d.weekday() + 1) % 7
    return f"{day_name(lang, day_of_week)}, {d.day}/{d.month}/{d.year}"
