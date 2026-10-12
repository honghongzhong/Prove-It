"use strict";

function renderMath(node, tex, displayMode) {
  if (window.katex)
    window.katex.render(tex, node, {
      displayMode,
      throwOnError: false,
      trust: false,
      strict: "ignore",
      maxExpand: 1000,
      output: "htmlAndMathml",
      errorColor: "var(--danger)",
    });
  else node.textContent = tex;
}

function appendInline(parent, source) {
  const token =
    /(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|(?<![\w])_[^_\n]+_(?![\w])|\$[^$\n]+\$|\\\([^\n]+?\\\)|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g;
  let cursor = 0;
  for (const match of source.matchAll(token)) {
    if (match.index > cursor)
      parent.append(document.createTextNode(source.slice(cursor, match.index)));
    const value = match[0];
    let node;
    if (value.startsWith("`")) {
      node = document.createElement("code");
      node.textContent = value.slice(1, -1);
    } else if (value.startsWith("**") || value.startsWith("__")) {
      node = document.createElement("strong");
      node.textContent = value.slice(2, -2);
    } else if (value.startsWith("*") || value.startsWith("_")) {
      node = document.createElement("em");
      node.textContent = value.slice(1, -1);
    } else if (value.startsWith("$") || value.startsWith("\\(")) {
      node = document.createElement("span");
      node.className = "math-inline";
      renderMath(
        node,
        value.startsWith("$") ? value.slice(1, -1) : value.slice(2, -2),
        false,
      );
    } else {
      const link = value.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
      if (link) {
        node = document.createElement("a");
        node.textContent = link[1];
        node.href = link[2];
        node.target = "_blank";
        node.rel = "noopener noreferrer";
      }
    }
    if (node) parent.append(node);
    cursor = match.index + value.length;
  }
  if (cursor < source.length)
    parent.append(document.createTextNode(source.slice(cursor)));
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function renderMarkdown(target, markdown) {
  const lines = String(markdown || "")
    .replace(/\r\n?/g, "\n")
    .split("\n");
  const fragment = document.createDocumentFragment();
  let paragraph = [];
  let list = null;
  let code = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const p = document.createElement("p");
    paragraph.forEach((line, index) => {
      if (index) p.append(document.createElement("br"));
      appendInline(p, line);
    });
    fragment.append(p);
    paragraph = [];
  };
  const closeList = () => {
    list = null;
  };
  const flushParagraphAndList = () => {
    flushParagraph();
    closeList();
  };
  const renderTable = (rows) => {
    const table = document.createElement("table");
    table.className = "markdown-table";
    rows.forEach((row, rowIndex) => {
      const tr = document.createElement("tr");
      row
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .forEach((cell) => {
          const tag = rowIndex === 0 ? "th" : "td";
          const cellNode = document.createElement(tag);
          appendInline(cellNode, cell.trim());
          tr.append(cellNode);
        });
      table.append(tr);
    });
    fragment.append(table);
  };

  const mergeAdjacentLists = () => {
    let node = fragment.firstChild;
    while (node) {
      const next = node.nextSibling;
      if (
        node.nodeType === Node.ELEMENT_NODE &&
        /^(OL|UL)$/.test(node.tagName)
      ) {
        let following = node.nextSibling;
        while (
          following &&
          following.nodeType === Node.ELEMENT_NODE &&
          following.tagName === node.tagName
        ) {
          while (following.firstChild) node.append(following.firstChild);
          const remove = following;
          following = following.nextSibling;
          remove.remove();
        }
      }
      node = next;
    }
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (code) {
      if (/^\s*```/.test(line)) {
        const pre = document.createElement("pre");
        const codeNode = document.createElement("code");
        codeNode.textContent = code.lines.join("\n");
        pre.append(codeNode);
        fragment.append(pre);
        code = null;
      } else code.lines.push(line);
      continue;
    }
    const fence = line.match(/^\s*```([\w+-]*)\s*$/);
    if (fence) {
      flushParagraphAndList();
      code = { lines: [], language: fence[1] };
      continue;
    }
    if (
      index + 1 < lines.length &&
      line.includes("|") &&
      isTableSeparator(lines[index + 1])
    ) {
      flushParagraphAndList();
      const rows = [line];
      index += 2;
      while (
        index < lines.length &&
        lines[index].includes("|") &&
        lines[index].trim()
      )
        rows.push(lines[index++]);
      index -= 1;
      renderTable(rows);
      continue;
    }
    if (/^\s*$/.test(line)) {
      flushParagraph();
      const nextItem = lines[index + 1]?.match(
        /^\s*(?:([-+*])|(\d+)[.)])\s+(.+)$/,
      );
      const nextTag = nextItem ? (nextItem[2] ? "ol" : "ul") : null;
      if (!list || list.tagName.toLowerCase() !== nextTag) closeList();
      continue;
    }
    if (/^\s*(?:\$\$|\\\[)/.test(line)) {
      flushParagraphAndList();
      const delimiter = line.trim().startsWith("$$") ? "$$" : "\\]";
      const firstLine = line.trim().slice(2);
      const mathLines = [];
      if (firstLine.includes(delimiter))
        mathLines.push(firstLine.slice(0, firstLine.indexOf(delimiter)));
      else {
        if (firstLine.trim()) mathLines.push(firstLine);
        while (
          index + 1 < lines.length &&
          !lines[index + 1].includes(delimiter)
        )
          mathLines.push(lines[++index]);
        if (index + 1 < lines.length) {
          const closingLine = lines[++index];
          const closeAt = closingLine.indexOf(delimiter);
          if (closeAt > 0) mathLines.push(closingLine.slice(0, closeAt));
        }
      }
      const math = document.createElement("div");
      math.className = "math-display";
      renderMath(math, mathLines.join("\n"), true);
      fragment.append(math);
      continue;
    }
    const heading = line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      flushParagraphAndList();
      const h = document.createElement(`h${heading[1].length}`);
      appendInline(h, heading[2]);
      fragment.append(h);
      continue;
    }
    if (/^\s*(---+|\*\*\*+|___+)\s*$/.test(line)) {
      flushParagraphAndList();
      fragment.append(document.createElement("hr"));
      continue;
    }
    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) {
      flushParagraphAndList();
      const blockquote = document.createElement("blockquote");
      appendInline(blockquote, quote[1]);
      fragment.append(blockquote);
      continue;
    }
    const item = line.match(/^\s*(?:([-+*])|(\d+)[.)])\s+(.+)$/);
    if (item) {
      flushParagraph();
      const tag = item[2] ? "ol" : "ul";
      if (!list || list.tagName.toLowerCase() !== tag) {
        list = document.createElement(tag);
        fragment.append(list);
      }
      const li = document.createElement("li");
      appendInline(li, item[3]);
      list.append(li);
      continue;
    }
    closeList();
    paragraph.push(line);
  }
  if (code) {
    const pre = document.createElement("pre");
    const codeNode = document.createElement("code");
    codeNode.textContent = code.lines.join("\n");
    pre.append(codeNode);
    fragment.append(pre);
  }
  flushParagraph();
  mergeAdjacentLists();
  target.replaceChildren(fragment);
}

window.ProveItMarkdown = { render: renderMarkdown };
