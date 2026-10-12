const paths = {
  plus: "M12 5v14M5 12h14",
  send: "M12 19V5m-6 6 6-6 6 6",
  pause: "M8 5v14M16 5v14",
  edit: "m15 5 4 4M4 20l4-1L20 7a2 2 0 0 0-4-4L5 15z",
  folder: "M3 7V5h6l2 2h10v13H3z",
  search: "m21 21-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  settings:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1z",
  trash: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  sidebar: "M3 4h18v16H3zM9 4v16",
  chat: "M4 4h16v13H9l-5 4z",
  research: "M5 3h14v18H5zM8 7h8M8 11h8M8 15h5",
  code: "m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 16",
  download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
  history: "M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l3 2",
  check: "m5 12 4 4L19 6",
  model: "m12 3 9 5v8l-9 5-9-5V8zM3 8l9 5 9-5M12 13v8",
  arrow: "M4 12h16m-6-6 6 6-6 6",
  close: "m6 6 12 12M6 18 18 6",
  tool: "m14 5 5 5M4 20l7-7M14 3a6 6 0 0 0-7 8L3 15v5h5l5-5a6 6 0 0 0 8-7l-5 3-3-3z",
};
export function icon(name) {
  return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.code}"/></svg>`;
}
