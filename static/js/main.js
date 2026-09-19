// Theme toggle (persisted)
const root = document.documentElement;
const saved = localStorage.getItem("theme");
if (saved) root.setAttribute("data-theme", saved);

const toggle = document.getElementById("theme-toggle");
toggle?.addEventListener("click", () => {
  const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
  root.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
});

// Typed "whoami" output
const typedEl = document.getElementById("typed");
const phrase = window.__WHOAMI__ || "Free Software enthusiast";
if (typedEl) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) {
    typedEl.textContent = phrase;
  } else {
    let i = 0;
    const tick = () => {
      typedEl.textContent = phrase.slice(0, i);
      if (i++ <= phrase.length) setTimeout(tick, 45);
    };
    setTimeout(tick, 500);
  }
}

// Scroll reveal + skill meter fill
const revealables = document.querySelectorAll(".reveal");
const io = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        io.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.15 }
);
revealables.forEach((el) => io.observe(el));

// Live clock from the backend (/api/now), then tick locally
const clockTime = document.getElementById("clock-time");
async function initClock() {
  if (!clockTime) return;
  try {
    const res = await fetch("/api/now");
    const data = await res.json();
    let base = new Date(data.iso);
    const render = () => {
      clockTime.textContent = base.toLocaleTimeString("en-GB", { hour12: false });
    };
    render();
    setInterval(() => {
      base = new Date(base.getTime() + 1000);
      render();
    }, 1000);
  } catch (e) {
    clockTime.textContent = new Date().toLocaleTimeString("en-GB", { hour12: false });
  }
}
initClock();
