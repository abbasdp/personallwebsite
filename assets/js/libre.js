/**
 * Libre UI — abbasdp.ir
 * Reading site: Jalali dates + minimal progressive enhancement
 */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Digits ---------- */
  var FA = '۰۱۲۳۴۵۶۷۸۹';
  var FA_RE = /[۰-۹]/g;
  var AR_RE = /[٠-٩]/g;

  function toLatinDigits(str) {
    return String(str)
      .replace(FA_RE, function (d) { return FA.indexOf(d); })
      .replace(AR_RE, function (d) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(d); });
  }

  function toPersianDigits(str) {
    return String(str).replace(/\d/g, function (d) { return FA[d]; });
  }

  /* ---------- Gregorian → Jalali ---------- */
  function gregorianToJalali(gy, gm, gd) {
    var g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    var gy2 = (gm > 2) ? (gy + 1) : gy;
    var days =
      355666 +
      (365 * gy) +
      Math.floor((gy2 + 3) / 4) -
      Math.floor((gy2 + 99) / 100) +
      Math.floor((gy2 + 399) / 400) +
      gd +
      g_d_m[gm - 1];
    var jy = -1595 + 33 * Math.floor(days / 12053);
    days %= 12053;
    jy += 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days > 365) {
      jy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }
    var jm, jd;
    if (days < 186) {
      jm = 1 + Math.floor(days / 31);
      jd = 1 + (days % 31);
    } else {
      jm = 7 + Math.floor((days - 186) / 30);
      jd = 1 + ((days - 186) % 30);
    }
    return [jy, jm, jd];
  }

  var J_MONTHS = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
  ];

  function pad2(n) {
    return n < 10 ? '0' + n : String(n);
  }

  function formatJalali(jy, jm, jd, style) {
    if (style === 'long') {
      return toPersianDigits(jd + ' ' + J_MONTHS[jm - 1] + ' ' + jy);
    }
    return toPersianDigits(jy + '/' + pad2(jm) + '/' + pad2(jd));
  }

  function parseDateTimeAttr(value) {
    if (!value) return null;
    var raw = toLatinDigits(value).trim();
    var m = raw.match(
      /^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?/
    );
    if (!m) return null;
    var y = +m[1], mo = +m[2], d = +m[3];
    var h = m[4] != null ? +m[4] : 0;
    var mi = m[5] != null ? +m[5] : 0;
    return {
      y: y,
      m: mo,
      d: d,
      h: h,
      mi: mi,
      isoDate: m[1] + '-' + pad2(mo) + '-' + pad2(d)
    };
  }

  function initJalaliDates() {
    var nodes = document.querySelectorAll('time[datetime]');
    if (!nodes.length) return;

    var preferLong =
      document.body.classList.contains('post-template') ||
      document.body.classList.contains('page-template');

    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.getAttribute('data-jalali') === '1') continue;

      var parsed = parseDateTimeAttr(el.getAttribute('datetime'));
      if (!parsed) continue;

      var j = gregorianToJalali(parsed.y, parsed.m, parsed.d);
      var isFeatured = el.classList.contains('featured__meta');
      var style = preferLong && !isFeatured ? 'long' : 'short';

      var iso = parsed.isoDate;
      if (parsed.h || parsed.mi) {
        iso += 'T' + pad2(parsed.h) + ':' + pad2(parsed.mi);
      }
      el.setAttribute('datetime', iso);
      el.textContent = formatJalali(j[0], j[1], j[2], style);
      el.setAttribute('data-jalali', '1');
      el.setAttribute('title', formatJalali(j[0], j[1], j[2], 'long'));
    }
  }

  function initProgress() {
    if (!document.body.classList.contains('post-template') &&
        !document.body.classList.contains('page-template')) {
      return;
    }
    var bar = document.createElement('div');
    bar.className = 'libre-progress';
    bar.setAttribute('aria-hidden', 'true');
    document.body.appendChild(bar);

    var article = document.querySelector('.content__entry') || document.querySelector('.main');
    if (!article) return;

    function update() {
      var rect = article.getBoundingClientRect();
      var total = article.offsetHeight - window.innerHeight;
      if (total <= 0) {
        bar.style.width = '0%';
        return;
      }
      var scrolled = Math.min(Math.max(-rect.top, 0), total);
      bar.style.width = ((scrolled / total) * 100).toFixed(2) + '%';
    }

    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    update();
  }

  function initTop() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'libre-top';
    btn.setAttribute('aria-label', 'بازگشت به بالا');
    btn.innerHTML = '↑';
    document.body.appendChild(btn);

    function onScroll() {
      if (window.scrollY > 480) btn.classList.add('is-visible');
      else btn.classList.remove('is-visible');
    }

    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  function revealLazyImages() {
    var images = document.querySelectorAll('img[loading]');
    for (var i = 0; i < images.length; i++) {
      (function (img) {
        function show() { img.classList.add('is-loaded'); }
        if (img.complete) {
          show();
        } else {
          img.addEventListener('load', show);
          img.addEventListener('error', show);
        }
      })(images[i]);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    initJalaliDates();
    initProgress();
    initTop();
    revealLazyImages();
  });
})();
