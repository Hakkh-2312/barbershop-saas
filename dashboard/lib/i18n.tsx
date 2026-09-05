"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "en" | "ar";

const STORAGE_KEY = "lang";

const TRANSLATIONS: Record<Lang, Record<string, string>> = {
  en: {
    "lang.switchTo": "العربية",

    "common.save": "Save",
    "common.saving": "Saving...",
    "common.cancel": "Cancel",
    "common.edit": "Edit",
    "common.delete": "Delete",
    "common.add": "Add",
    "common.adding": "Adding...",
    "common.loading": "Loading...",
    "common.whatsapp": "Chat on WhatsApp",
    "common.min": "min",

    "status.booked": "Booked",
    "status.cancelled": "Cancelled",
    "status.completed": "Completed",

    "nav.shopFallback": "Your Shop",
    "nav.today": "Today",
    "nav.appointments": "Appointments",
    "nav.customers": "Customers",
    "nav.services": "Services",
    "nav.workingHours": "Working Hours",
    "nav.timeOff": "Time Off",
    "nav.settings": "Settings",
    "nav.logout": "Log out",

    "today.blockOffTime": "Block off time",
    "today.appointmentsToday": "Appointments today",
    "today.nextUp": "Next up",
    "today.nothingScheduled": "Nothing scheduled today.",
    "today.blocked": "Blocked",

    "appointments.title": "Appointments",
    "appointments.description": "Every booking for your shop, past and upcoming.",
    "appointments.allStatuses": "All statuses",
    "appointments.reschedule": "Reschedule",
    "appointments.noneFound": "No appointments found.",

    "customers.title": "Customers",
    "customers.description": "Everyone who's booked with your shop.",
    "customers.addHeading": "Add a customer",
    "customers.name": "Name",
    "customers.phone": "Phone",
    "customers.emailOptional": "Email (optional)",
    "customers.noneYet": "No customers yet.",

    "services.title": "Services",
    "services.description": "What customers can book, with duration and price.",
    "services.addHeading": "Add a service",
    "services.duration": "Duration (min)",
    "services.price": "Price (₪)",
    "services.noneYet": "No services yet.",

    "workingHours.title": "Working Hours",
    "workingHours.description": "When your shop is open for bookings.",
    "workingHours.notSet": "(not set)",
    "workingHours.to": "to",
    "workingHours.closed": "Closed",
    "workingHours.day.0": "Sunday",
    "workingHours.day.1": "Monday",
    "workingHours.day.2": "Tuesday",
    "workingHours.day.3": "Wednesday",
    "workingHours.day.4": "Thursday",
    "workingHours.day.5": "Friday",
    "workingHours.day.6": "Saturday",

    "timeOff.title": "Time Off",
    "timeOff.description":
      "Block off periods when you're unavailable - customers won't be able to book into them, on WhatsApp or the API.",
    "timeOff.addHeading": "Add a block",
    "timeOff.date": "Date",
    "timeOff.from": "From",
    "timeOff.to": "To",
    "timeOff.reasonOptional": "Reason (optional)",
    "timeOff.reasonPlaceholder": "Doctor's appointment",
    "timeOff.addBlock": "Add block",
    "timeOff.noneBlocked": "No blocked periods.",
    "timeOff.remove": "Remove",

    "settings.title": "Shop Settings",
    "settings.description":
      "Shown to customers on WhatsApp when they ask to call you or for your address.",
    "settings.shopName": "Shop name",
    "settings.phone": "Phone number",
    "settings.address": "Address",
    "settings.countryCode": "WhatsApp country code",
    "settings.countryCodeHelp":
      "Used to build correct WhatsApp links for customers whose number is saved without one, e.g. 972 for Israel/Palestine.",
    "settings.saved": "Saved.",

    "login.title": "Log in",
    "login.subtitle": "Welcome back to your shop dashboard.",
    "login.email": "Email",
    "login.password": "Password",
    "login.submit": "Log in",
    "login.submitting": "Logging in...",
    "login.noShop": "No shop yet?",
    "login.signUp": "Sign up",

    "signup.title": "Set up your shop",
    "signup.subtitle": "Start taking bookings in a couple of minutes.",
    "signup.shopName": "Shop name",
    "signup.email": "Email",
    "signup.password": "Password (min. 8 characters)",
    "signup.submit": "Create shop",
    "signup.submitting": "Creating...",
    "signup.haveAccount": "Already have an account?",
    "signup.logIn": "Log in",
  },
  ar: {
    "lang.switchTo": "English",

    "common.save": "حفظ",
    "common.saving": "جارٍ الحفظ...",
    "common.cancel": "إلغاء",
    "common.edit": "تعديل",
    "common.delete": "حذف",
    "common.add": "إضافة",
    "common.adding": "جارٍ الإضافة...",
    "common.loading": "جارٍ التحميل...",
    "common.whatsapp": "تواصل عبر واتساب",
    "common.min": "دقيقة",

    "status.booked": "محجوز",
    "status.cancelled": "ملغى",
    "status.completed": "مكتمل",

    "nav.shopFallback": "متجرك",
    "nav.today": "اليوم",
    "nav.appointments": "المواعيد",
    "nav.customers": "العملاء",
    "nav.services": "الخدمات",
    "nav.workingHours": "ساعات العمل",
    "nav.timeOff": "إجازة",
    "nav.settings": "الإعدادات",
    "nav.logout": "تسجيل الخروج",

    "today.blockOffTime": "حجب وقت",
    "today.appointmentsToday": "مواعيد اليوم",
    "today.nextUp": "التالي",
    "today.nothingScheduled": "لا يوجد شيء مجدول اليوم.",
    "today.blocked": "محجوب",

    "appointments.title": "المواعيد",
    "appointments.description": "جميع الحجوزات لمتجرك، السابقة والقادمة.",
    "appointments.allStatuses": "كل الحالات",
    "appointments.reschedule": "إعادة الجدولة",
    "appointments.noneFound": "لا توجد مواعيد.",

    "customers.title": "العملاء",
    "customers.description": "كل من قام بالحجز في متجرك.",
    "customers.addHeading": "إضافة عميل",
    "customers.name": "الاسم",
    "customers.phone": "رقم الهاتف",
    "customers.emailOptional": "البريد الإلكتروني (اختياري)",
    "customers.noneYet": "لا يوجد عملاء بعد.",

    "services.title": "الخدمات",
    "services.description": "ما يمكن للعملاء حجزه، مع المدة والسعر.",
    "services.addHeading": "إضافة خدمة",
    "services.duration": "المدة (دقيقة)",
    "services.price": "السعر (₪)",
    "services.noneYet": "لا توجد خدمات بعد.",

    "workingHours.title": "ساعات العمل",
    "workingHours.description": "متى يكون متجرك مفتوحًا للحجز.",
    "workingHours.notSet": "(غير محدد)",
    "workingHours.to": "إلى",
    "workingHours.closed": "مغلق",
    "workingHours.day.0": "الأحد",
    "workingHours.day.1": "الاثنين",
    "workingHours.day.2": "الثلاثاء",
    "workingHours.day.3": "الأربعاء",
    "workingHours.day.4": "الخميس",
    "workingHours.day.5": "الجمعة",
    "workingHours.day.6": "السبت",

    "timeOff.title": "إجازة",
    "timeOff.description":
      "احجب الفترات التي تكون فيها غير متاح - لن يتمكن العملاء من الحجز فيها، سواء عبر واتساب أو التطبيق.",
    "timeOff.addHeading": "إضافة حجب",
    "timeOff.date": "التاريخ",
    "timeOff.from": "من",
    "timeOff.to": "إلى",
    "timeOff.reasonOptional": "السبب (اختياري)",
    "timeOff.reasonPlaceholder": "موعد طبيب",
    "timeOff.addBlock": "إضافة حجب",
    "timeOff.noneBlocked": "لا توجد فترات محجوبة.",
    "timeOff.remove": "إزالة",

    "settings.title": "إعدادات المتجر",
    "settings.description": "تظهر للعملاء على واتساب عند سؤالهم عن رقم التواصل أو العنوان.",
    "settings.shopName": "اسم المتجر",
    "settings.phone": "رقم الهاتف",
    "settings.address": "العنوان",
    "settings.countryCode": "رمز الدولة لواتساب",
    "settings.countryCodeHelp":
      "يُستخدم لإنشاء روابط واتساب صحيحة للعملاء الذين حُفظ رقمهم بدون رمز الدولة، مثلاً 972 لفلسطين/إسرائيل.",
    "settings.saved": "تم الحفظ.",

    "login.title": "تسجيل الدخول",
    "login.subtitle": "مرحبًا بعودتك إلى لوحة تحكم متجرك.",
    "login.email": "البريد الإلكتروني",
    "login.password": "كلمة المرور",
    "login.submit": "تسجيل الدخول",
    "login.submitting": "جارٍ تسجيل الدخول...",
    "login.noShop": "ليس لديك متجر بعد؟",
    "login.signUp": "إنشاء حساب",

    "signup.title": "أنشئ متجرك",
    "signup.subtitle": "ابدأ باستقبال الحجوزات خلال دقائق.",
    "signup.shopName": "اسم المتجر",
    "signup.email": "البريد الإلكتروني",
    "signup.password": "كلمة المرور (٨ أحرف على الأقل)",
    "signup.submit": "إنشاء المتجر",
    "signup.submitting": "جارٍ الإنشاء...",
    "signup.haveAccount": "لديك حساب بالفعل؟",
    "signup.logIn": "تسجيل الدخول",
  },
};

interface LanguageContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
  dir: "ltr" | "rtl";
}

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "ar") {
      setLangState(stored);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === "ar" ? "ar" : "en";
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  function setLang(next: Lang) {
    localStorage.setItem(STORAGE_KEY, next);
    setLangState(next);
  }

  function t(key: string): string {
    return TRANSLATIONS[lang][key] ?? key;
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t, dir: lang === "ar" ? "rtl" : "ltr" }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return ctx;
}

/** Locale to format dates/numbers with - keeps Western digits in Arabic
 * (the regional convention here) instead of Intl's default Arabic-Indic
 * numerals. */
export function dateLocale(lang: Lang): string {
  return lang === "ar" ? "ar-u-nu-latn" : "en-US";
}
