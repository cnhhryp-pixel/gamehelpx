(()=> {
  const base = location.pathname.startsWith("/gamehelpx/") || location.pathname === "/gamehelpx" ? "/gamehelpx" : "";
  const withBase = (p) => base + (p.startsWith("/") ? p : "/" + p);

  document.querySelectorAll("[data-release]").forEach(el => {
    const d = new Date(el.dataset.release + "T00:00:00");
    const n = new Date();
    const days = Math.ceil((d - n) / 86400000);
    el.textContent = days > 1 ? days + " days to launch" : days === 1 ? "Launches tomorrow" : days === 0 ? "Launch day" : "Released " + Math.abs(days) + " days ago";
  });

  const localSearch = document.querySelector("[data-search]");
  if (localSearch) {
    localSearch.addEventListener("input", e => {
      const q = e.target.value.toLowerCase();
      document.querySelectorAll("[data-game]").forEach(x => x.style.display = x.textContent.toLowerCase().includes(q) ? "" : "none");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".links").forEach(n => {
      if (!n.querySelector('[data-global-search-link]')) {
        const a = document.createElement("a");
        a.href = withBase("/search/");
        a.textContent = "Search";
        a.dataset.globalSearchLink = "1";
        n.appendChild(a);
      }
    });

    document.addEventListener("keydown", e => {
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        location.href = withBase("/search/");
      }
    });

    const path = location.pathname.replace(base, "") || "/";
    const parts = path.split("/").filter(Boolean);
    const isDetailGamePage = parts[0] === "games" && parts.length >= 3;
    if (!isDetailGamePage || document.querySelector("[data-related-generated]")) return;

    const script = document.createElement("script");
    script.src = withBase("/data/search-index.js");
    script.onload = () => {
      const all = window.GHX_SEARCH_INDEX || [];
      const gamePrefix = "/games/" + parts[1] + "/";
      const current = path.endsWith("/") ? path : path + "/";
      const related = all
        .filter(x => x.url.startsWith(gamePrefix) && x.url !== current && x.url !== gamePrefix)
        .slice(0, 6);
      if (!related.length) return;

      const section = document.createElement("section");
      section.className = "section related-section";
      section.dataset.relatedGenerated = "1";
      section.innerHTML = '<div class="wrap"><div class="head"><div><div class="eyebrow">Keep exploring</div><h2>Related content</h2></div><a class="link" href="' + withBase(gamePrefix) + '">Open game hub →</a></div><div class="related-grid">' +
        related.map(x => '<a class="related-card" href="' + withBase(x.url) + '"><b>' + x.title.replace(/^.*? · /, "") + '</b><span>' + x.url.replace(gamePrefix, "").replaceAll("/", " ").trim() + '</span></a>').join("") +
        '</div></div>';
      const main = document.querySelector("main");
      if (main) main.appendChild(section);
    };
    document.head.appendChild(script);
  });
})();