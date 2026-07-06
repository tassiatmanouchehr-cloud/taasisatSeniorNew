/**
 * Jalali (Shamsi/Solar Hijri) Date Display Utilities
 * Enterprise Service Marketplace Platform
 *
 * DISPLAY ONLY — backend stores UTC Gregorian (per ADR-001.20).
 * These utilities convert ISO-8601 dates to Jalali for Persian UI display.
 *
 * Features:
 * - Gregorian → Jalali conversion (pure JS, no dependencies)
 * - Persian digit display (۰۱۲۳۴۵۶۷۸۹)
 * - Relative time (لحظاتی پیش، ۵ دقیقه پیش، دیروز)
 * - Date formatting (۱۴۰۵/۰۴/۱۶)
 * - DateTime formatting (۱۴۰۵/۰۴/۱۶ ۱۴:۳۰)
 * - Month/weekday names in Persian
 * - Auto-conversion of [data-jalali] elements on page load
 * - HTMX afterSwap integration (re-converts after partial updates)
 *
 * Usage:
 *   Jalali.toJalali('2026-07-06T14:30:00Z')        → '۱۴۰۵/۰۴/۱۶'
 *   Jalali.toJalaliDateTime('2026-07-06T14:30:00Z') → '۱۴۰۵/۰۴/۱۶ ۱۴:۳۰'
 *   Jalali.relative('2026-07-06T14:30:00Z')         → '۵ دقیقه پیش'
 *   Jalali.toPersianDigits('1405/04/16')            → '۱۴۰۵/۰۴/۱۶'
 *
 * In templates:
 *   <time data-jalali="2026-07-06T14:30:00Z"></time>
 *   <time data-jalali-datetime="2026-07-06T14:30:00Z"></time>
 *   <span data-jalali-relative="2026-07-06T14:30:00Z"></span>
 */

const Jalali = (() => {
  'use strict';

  // Persian digits mapping
  const PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

  // Persian month names
  const MONTH_NAMES = [
    'فروردین', 'اردیبهشت', 'خرداد',
    'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر',
    'دی', 'بهمن', 'اسفند'
  ];

  // Persian weekday names (Saturday = 0 in Iranian week)
  const WEEKDAY_NAMES = [
    'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه',
    'چهارشنبه', 'پنجشنبه', 'جمعه'
  ];

  // Relative time labels
  const RELATIVE = {
    now: 'لحظاتی پیش',
    seconds: 'ثانیه پیش',
    minute: 'یک دقیقه پیش',
    minutes: 'دقیقه پیش',
    hour: 'یک ساعت پیش',
    hours: 'ساعت پیش',
    day: 'دیروز',
    days: 'روز پیش',
    week: 'هفته پیش',
    weeks: 'هفته پیش',
    month: 'ماه پیش',
    months: 'ماه پیش',
    year: 'سال پیش',
    years: 'سال پیش',
    future: 'در آینده',
  };

  /**
   * Convert a number string to Persian digits.
   * @param {string|number} str
   * @returns {string}
   */
  function toPersianDigits(str) {
    return String(str).replace(/[0-9]/g, (d) => PERSIAN_DIGITS[parseInt(d)]);
  }

  /**
   * Convert Gregorian date to Jalali (Solar Hijri).
   * Algorithm based on the widely-used jalaali-js implementation.
   * @param {number} gy - Gregorian year
   * @param {number} gm - Gregorian month (1-12)
   * @param {number} gd - Gregorian day
   * @returns {{jy: number, jm: number, jd: number}}
   */
  function gregorianToJalali(gy, gm, gd) {
    const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    let jy, jm, jd;

    let gy2 = (gm > 2) ? (gy + 1) : gy;
    let days = 355666 + (365 * gy) + Math.floor((gy2 + 3) / 4) - Math.floor((gy2 + 99) / 100)
      + Math.floor((gy2 + 399) / 400) + gd + g_d_m[gm - 1];

    jy = -1595 + (33 * Math.floor(days / 12053));
    days %= 12053;

    jy += 4 * Math.floor(days / 1461);
    days %= 1461;

    if (days > 365) {
      jy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }

    if (days < 186) {
      jm = 1 + Math.floor(days / 31);
      jd = 1 + (days % 31);
    } else {
      jm = 7 + Math.floor((days - 186) / 30);
      jd = 1 + ((days - 186) % 30);
    }

    return { jy, jm, jd };
  }

  /**
   * Parse an ISO-8601 string to Date object.
   * @param {string} isoString
   * @returns {Date}
   */
  function parseISO(isoString) {
    return new Date(isoString);
  }

  /**
   * Format a Jalali date as YYYY/MM/DD with Persian digits.
   * @param {string} isoString - ISO-8601 date string
   * @returns {string} e.g., '۱۴۰۵/۰۴/۱۶'
   */
  function toJalali(isoString) {
    if (!isoString) return '';
    const d = parseISO(isoString);
    if (isNaN(d.getTime())) return '';

    const { jy, jm, jd } = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
    const formatted = `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`;
    return toPersianDigits(formatted);
  }

  /**
   * Format a Jalali date+time as YYYY/MM/DD HH:MM with Persian digits.
   * @param {string} isoString
   * @returns {string} e.g., '۱۴۰۵/۰۴/۱۶ ۱۴:۳۰'
   */
  function toJalaliDateTime(isoString) {
    if (!isoString) return '';
    const d = parseISO(isoString);
    if (isNaN(d.getTime())) return '';

    const { jy, jm, jd } = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const formatted = `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')} ${hours}:${minutes}`;
    return toPersianDigits(formatted);
  }

  /**
   * Format a Jalali date with month name.
   * @param {string} isoString
   * @returns {string} e.g., '۱۶ تیر ۱۴۰۵'
   */
  function toJalaliLong(isoString) {
    if (!isoString) return '';
    const d = parseISO(isoString);
    if (isNaN(d.getTime())) return '';

    const { jy, jm, jd } = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
    return `${toPersianDigits(jd)} ${MONTH_NAMES[jm - 1]} ${toPersianDigits(jy)}`;
  }

  /**
   * Get relative time string (e.g., "۵ دقیقه پیش").
   * @param {string} isoString
   * @returns {string}
   */
  function relative(isoString) {
    if (!isoString) return '';
    const d = parseISO(isoString);
    if (isNaN(d.getTime())) return '';

    const now = new Date();
    const diff = now - d;

    // Future dates
    if (diff < 0) return RELATIVE.future;

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const weeks = Math.floor(days / 7);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);

    if (seconds < 30) return RELATIVE.now;
    if (seconds < 60) return toPersianDigits(seconds) + ' ' + RELATIVE.seconds;
    if (minutes === 1) return RELATIVE.minute;
    if (minutes < 60) return toPersianDigits(minutes) + ' ' + RELATIVE.minutes;
    if (hours === 1) return RELATIVE.hour;
    if (hours < 24) return toPersianDigits(hours) + ' ' + RELATIVE.hours;
    if (days === 1) return RELATIVE.day;
    if (days < 7) return toPersianDigits(days) + ' ' + RELATIVE.days;
    if (weeks === 1) return '۱ ' + RELATIVE.week;
    if (weeks < 4) return toPersianDigits(weeks) + ' ' + RELATIVE.weeks;
    if (months === 1) return '۱ ' + RELATIVE.month;
    if (months < 12) return toPersianDigits(months) + ' ' + RELATIVE.months;
    if (years === 1) return '۱ ' + RELATIVE.year;
    return toPersianDigits(years) + ' ' + RELATIVE.years;
  }

  /**
   * Get the Persian weekday name for a date.
   * @param {string} isoString
   * @returns {string}
   */
  function weekday(isoString) {
    if (!isoString) return '';
    const d = parseISO(isoString);
    if (isNaN(d.getTime())) return '';
    // JS: Sunday=0 → need to map to Iranian week (Saturday=0)
    const day = d.getDay();
    const iranianDay = (day + 1) % 7; // Sat=0, Sun=1, ..., Fri=6
    return WEEKDAY_NAMES[iranianDay];
  }

  /**
   * Auto-convert all elements with data-jalali attributes.
   * Call on DOMContentLoaded and after HTMX swaps.
   */
  function convertAll() {
    // data-jalali → date only
    document.querySelectorAll('[data-jalali]').forEach((el) => {
      const iso = el.getAttribute('data-jalali');
      if (iso) el.textContent = toJalali(iso);
    });

    // data-jalali-datetime → date + time
    document.querySelectorAll('[data-jalali-datetime]').forEach((el) => {
      const iso = el.getAttribute('data-jalali-datetime');
      if (iso) el.textContent = toJalaliDateTime(iso);
    });

    // data-jalali-long → "۱۶ تیر ۱۴۰۵"
    document.querySelectorAll('[data-jalali-long]').forEach((el) => {
      const iso = el.getAttribute('data-jalali-long');
      if (iso) el.textContent = toJalaliLong(iso);
    });

    // data-jalali-relative → "۵ دقیقه پیش"
    document.querySelectorAll('[data-jalali-relative]').forEach((el) => {
      const iso = el.getAttribute('data-jalali-relative');
      if (iso) el.textContent = relative(iso);
    });

    // data-persian-digits → convert content to Persian digits
    document.querySelectorAll('[data-persian-digits]').forEach((el) => {
      el.textContent = toPersianDigits(el.textContent);
    });
  }

  // Auto-initialize on DOM ready
  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', convertAll);

    // Re-convert after HTMX partial page updates
    document.addEventListener('htmx:afterSwap', convertAll);
    document.addEventListener('htmx:afterSettle', convertAll);
  }

  // Public API
  return {
    toJalali,
    toJalaliDateTime,
    toJalaliLong,
    relative,
    weekday,
    toPersianDigits,
    convertAll,
    MONTH_NAMES,
    WEEKDAY_NAMES,
    gregorianToJalali,
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Jalali;
}
