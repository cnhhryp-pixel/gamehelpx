(()=> {
  const base = location.pathname.startsWith("/gamehelpx/") || location.pathname === "/gamehelpx" ? "/gamehelpx" : "";
  const withBase = (p) => base + (p.startsWith("/") ? p : "/" + p);
  const prodPath = (location.pathname.replace(base, "") || "/").replace(/\/+/g, "/");
  const prodUrl = "https://gamehelpx.com" + prodPath;

  const ensureMeta = (attr, key, value) => {
    if (!value) return;
    let el = document.head.querySelector('meta[' + attr + '="' + key + '"]');
    if (!el) {
      el = document.createElement("meta");
      el.setAttribute(attr, key);
      document.head.appendChild(el);
    }
    if (!el.getAttribute("content")) el.setAttribute("content", value);
  };
  const addJsonLd = (data, id) => {
    if (!data || document.head.querySelector('script[data-ghx-schema="' + id + '"]')) return;
    const s = document.createElement("script");
    s.type = "application/ld+json";
    s.dataset.ghxSchema = id;
    s.textContent = JSON.stringify(data);
    document.head.appendChild(s);
  };

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
    const title = document.title || "GameHelpX";
    const h1 = document.querySelector("h1");
    const descriptionEl = document.querySelector('meta[name="description"]');
    const description = descriptionEl?.content || document.querySelector(".lede")?.textContent?.trim() || "GameHelpX guides, wiki pages, builds, databases and tools.";

    if (!document.querySelector('link[rel="canonical"]')) {
      const c = document.createElement("link");
      c.rel = "canonical";
      c.href = prodUrl;
      document.head.appendChild(c);
    }
    if (!document.querySelector('meta[name="robots"]')) ensureMeta("name", "robots", "index,follow");

    ensureMeta("property", "og:title", title);
    ensureMeta("property", "og:description", description);
    ensureMeta("property", "og:url", prodUrl);
    ensureMeta("property", "og:type", prodPath.startsWith("/games/") && prodPath.split("/").filter(Boolean).length >= 3 ? "article" : "website");
    ensureMeta("property", "og:site_name", "GameHelpX");
    ensureMeta("name", "twitter:card", "summary");
    ensureMeta("name", "twitter:title", title);
    ensureMeta("name", "twitter:description", description);

    addJsonLd({
      "@context":"https://schema.org",
      "@type":"WebPage",
      "name": h1?.textContent?.trim() || title.replace(/\s*\|\s*GameHelpX.*$/,""),
      "url": prodUrl,
      "description": description,
      "isPartOf":{"@type":"WebSite","name":"GameHelpX","url":"https://gamehelpx.com/"}
    }, "webpage");

    if (prodPath === "/") {
      addJsonLd({
        "@context":"https://schema.org",
        "@type":"WebSite",
        "name":"GameHelpX",
        "url":"https://gamehelpx.com/",
        "potentialAction":{
          "@type":"SearchAction",
          "target":{"@type":"EntryPoint","urlTemplate":"https://gamehelpx.com/search/?q={search_term_string}"},
          "query-input":"required name=search_term_string"
        }
      }, "website");
    }

    const crumbs = document.querySelector(".crumbs");
    if (crumbs) {
      const items = [...crumbs.querySelectorAll("a")].map((a,i)=>({
        "@type":"ListItem",
        "position":i+1,
        "name":a.textContent.trim(),
        "item":"https://gamehelpx.com" + (a.getAttribute("href") || "/")
      }));
      items.push({"@type":"ListItem","position":items.length+1,"name":h1?.textContent?.trim() || title,"item":prodUrl});
      addJsonLd({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":items},"breadcrumbs");
    }

    const faqDetails = [...document.querySelectorAll(".faq details")];
    if (faqDetails.length) {
      addJsonLd({
        "@context":"https://schema.org",
        "@type":"FAQPage",
        "mainEntity":faqDetails.map(d=>({
          "@type":"Question",
          "name":d.querySelector("summary")?.textContent?.trim() || "",
          "acceptedAnswer":{"@type":"Answer","text":d.querySelector("p")?.textContent?.trim() || ""}
        })).filter(x=>x.name && x.acceptedAnswer.text)
      }, "faq");
    }

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

    const parts = prodPath.split("/").filter(Boolean);
    const isDetailGamePage = parts[0] === "games" && parts.length >= 3;
    if (!isDetailGamePage || document.querySelector("[data-related-generated]")) return;

    const script = document.createElement("script");
    script.src = withBase("/data/search-index.js");
    script.onload = () => {
      const all = window.GHX_SEARCH_INDEX || [];
      const gamePrefix = "/games/" + parts[1] + "/";
      const current = prodPath.endsWith("/") ? prodPath : prodPath + "/";
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