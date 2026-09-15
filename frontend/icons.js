const ICONS = {
  scan: `
    <path d="M3 7V5a2 2 0 0 1 2-2h2"/>
    <path d="M17 3h2a2 2 0 0 1 2 2v2"/>
    <path d="M21 17v2a2 2 0 0 1-2 2h-2"/>
    <path d="M7 21H5a2 2 0 0 1-2-2v-2"/>
    <circle cx="11" cy="11" r="4"/>
    <path d="m14 14 3 3"/>`,
  refresh: `
    <path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5"/>
    <path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"/>`,
  folder: `
    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>`,
  download: `
    <path d="M12 3v12"/>
    <path d="m7 10 5 5 5-5"/>
    <path d="M5 21h14"/>`,
  search: `
    <circle cx="11" cy="11" r="7"/>
    <path d="m20 20-4-4"/>`,
  grid: `
    <rect x="3" y="3" width="7" height="7" rx="1"/>
    <rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="3" y="14" width="7" height="7" rx="1"/>
    <rect x="14" y="14" width="7" height="7" rx="1"/>`,
  list: `
    <path d="M8 6h13M8 12h13M8 18h13"/>
    <path d="M3 6h.01M3 12h.01M3 18h.01"/>`,
  heart: `
    <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/>`,
  check: `
    <path d="m5 12 4 4L19 6"/>`,
  x: `
    <path d="M18 6 6 18M6 6l12 12"/>`,
  menu: `
    <path d="M4 6h16M4 12h16M4 18h16"/>`,
  sun: `
    <circle cx="12" cy="12" r="4"/>
    <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"/>`,
  moon: `
    <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/>`,
  image: `
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <circle cx="9" cy="9" r="2"/>
    <path d="m21 15-5-5L5 21"/>`,
  film: `
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <path d="M7 3v18M17 3v18M3 7h4M17 7h4M3 12h18M3 17h4M17 17h4"/>`,
  archive: `
    <path d="M21 8v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8"/>
    <path d="M3 4h18v4H3zM10 12h4"/>`,
  gauge: `
    <path d="m12 14 4-4"/>
    <path d="M3.3 19a10 10 0 1 1 17.4 0"/>
    <circle cx="12" cy="14" r="1"/>`,
  database: `
    <ellipse cx="12" cy="5" rx="8" ry="3"/>
    <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>
    <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>`,
  sliders: `
    <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/>
    <path d="M1 14h6M9 8h6M17 16h6"/>`,
  eye: `
    <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/>
    <circle cx="12" cy="12" r="2.5"/>`,
  play: `
    <path d="m8 5 11 7-11 7Z"/>`,
  sparkles: `
    <path d="m12 3-1.2 3.2L8 7.5l2.8 1.3L12 12l1.2-3.2L16 7.5l-2.8-1.3Z"/>
    <path d="m19 14-.8 2.2L16 17l2.2.8L19 20l.8-2.2L22 17l-2.2-.8Z"/>
    <path d="m5 13-.8 2.2L2 16l2.2.8L5 19l.8-2.2L8 16l-2.2-.8Z"/>`,
  chevron: `
    <path d="m9 18 6-6-6-6"/>`,
  info: `
    <circle cx="12" cy="12" r="9"/>
    <path d="M12 11v5M12 8h.01"/>`,
  trash: `
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6"/>
    <path d="M10 11v6M14 11v6"/>`,
};

export function icon(name, className = "") {
  const body = ICONS[name] || ICONS.info;
  return `<svg class="svg-icon ${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

export function mountIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((node) => {
    node.innerHTML = icon(node.dataset.icon);
  });
}

