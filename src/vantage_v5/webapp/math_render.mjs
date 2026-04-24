function isEscaped(text, index) {
  let slashCount = 0;
  for (let cursor = index - 1; cursor >= 0 && text[cursor] === "\\"; cursor -= 1) {
    slashCount += 1;
  }
  return slashCount % 2 === 1;
}

function findClosingDelimiter(text, start, delimiter) {
  let index = start;
  while (index < text.length) {
    const next = text.indexOf(delimiter, index);
    if (next === -1) {
      return -1;
    }
    if (!isEscaped(text, next)) {
      return next;
    }
    index = next + delimiter.length;
  }
  return -1;
}

function pushTextToken(tokens, value) {
  if (!value) {
    return;
  }
  const last = tokens[tokens.length - 1];
  if (last?.type === "text") {
    last.value += value;
    return;
  }
  tokens.push({ type: "text", value });
}

function pushEscapedTextToken(tokens, source, cursor) {
  if (source[cursor] !== "\\" || !["$", "`"].includes(source[cursor + 1])) {
    return 0;
  }
  pushTextToken(tokens, source[cursor + 1]);
  return 2;
}

function countBackticks(text, start) {
  let count = 0;
  while (text[start + count] === "`") {
    count += 1;
  }
  return count;
}

function findClosingBacktickRun(text, start, length) {
  let index = start;
  while (index < text.length) {
    const next = text.indexOf("`", index);
    if (next === -1) {
      return -1;
    }
    if (!isEscaped(text, next) && countBackticks(text, next) === length) {
      return next;
    }
    index = next + 1;
  }
  return -1;
}

function normalizeInlineCodeValue(value) {
  const source = String(value || "");
  if (source.length > 1 && source.startsWith(" ") && source.endsWith(" ")) {
    return source.slice(1, -1);
  }
  return source;
}

function parseCodeFenceInfo(value) {
  const info = String(value || "").trim();
  if (!info) {
    return { language: "", meta: "" };
  }
  const [language, ...rest] = info.split(/\s+/);
  return {
    language: language || "",
    meta: rest.join(" ").trim(),
  };
}

function maybePushMathToken(tokens, type, value, raw) {
  if (!String(value || "").trim()) {
    pushTextToken(tokens, raw);
    return;
  }
  tokens.push({ type, value, raw });
}

function parseCodeFenceBody(value) {
  const normalized = String(value || "").replace(/^\n/, "");
  const firstNewline = normalized.indexOf("\n");
  if (firstNewline === -1) {
    const info = parseCodeFenceInfo(normalized);
    return { ...info, content: "" };
  }
  const info = parseCodeFenceInfo(normalized.slice(0, firstNewline));
  return {
    ...info,
    content: normalized.slice(firstNewline + 1),
  };
}

export function tokenizeMathText(text = "") {
  const source = String(text || "");
  const tokens = [];
  let cursor = 0;

  while (cursor < source.length) {
    const escapedLength = pushEscapedTextToken(tokens, source, cursor);
    if (escapedLength) {
      cursor += escapedLength;
      continue;
    }

    if (source.startsWith("```", cursor) && !isEscaped(source, cursor)) {
      const closing = source.indexOf("```", cursor + 3);
      if (closing !== -1) {
        const raw = source.slice(cursor, closing + 3);
        const body = source.slice(cursor + 3, closing);
        tokens.push({ type: "code_fence", ...parseCodeFenceBody(body), raw });
        cursor = closing + 3;
        continue;
      }
    }

    if (source[cursor] === "`" && !isEscaped(source, cursor)) {
      const tickCount = countBackticks(source, cursor);
      if (tickCount > 0 && tickCount < 3) {
        const closing = findClosingBacktickRun(source, cursor + tickCount, tickCount);
        if (closing !== -1) {
          const raw = source.slice(cursor, closing + tickCount);
          const value = normalizeInlineCodeValue(source.slice(cursor + tickCount, closing));
          if (value.length) {
            tokens.push({ type: "code_span", value, raw, ticks: tickCount });
          } else {
            pushTextToken(tokens, raw);
          }
          cursor = closing + tickCount;
          continue;
        }
      }
    }

    if (source.startsWith("$$", cursor) && !isEscaped(source, cursor)) {
      const closing = findClosingDelimiter(source, cursor + 2, "$$");
      if (closing !== -1) {
        const raw = source.slice(cursor, closing + 2);
        const value = source.slice(cursor + 2, closing);
        maybePushMathToken(tokens, "block_math", value, raw);
        cursor = closing + 2;
        continue;
      }
    }

    if (source.startsWith("\\[", cursor)) {
      const closing = findClosingDelimiter(source, cursor + 2, "\\]");
      if (closing !== -1) {
        const raw = source.slice(cursor, closing + 2);
        const value = source.slice(cursor + 2, closing);
        maybePushMathToken(tokens, "block_math", value, raw);
        cursor = closing + 2;
        continue;
      }
    }

    if (source.startsWith("\\(", cursor)) {
      const closing = findClosingDelimiter(source, cursor + 2, "\\)");
      if (closing !== -1) {
        const raw = source.slice(cursor, closing + 2);
        const value = source.slice(cursor + 2, closing);
        maybePushMathToken(tokens, "inline_math", value, raw);
        cursor = closing + 2;
        continue;
      }
    }

    if (source[cursor] === "$" && !isEscaped(source, cursor)) {
      const closing = findClosingDelimiter(source, cursor + 1, "$");
      if (closing !== -1) {
        const value = source.slice(cursor + 1, closing);
        const raw = source.slice(cursor, closing + 1);
        if (!value.includes("\n")) {
          maybePushMathToken(tokens, "inline_math", value, raw);
          cursor = closing + 1;
          continue;
        }
      }
    }

    pushTextToken(tokens, source[cursor]);
    cursor += 1;
  }

  return tokens;
}

export function hasMathSyntax(text = "") {
  return tokenizeMathText(text).some((token) => token.type === "inline_math" || token.type === "block_math");
}

export function hasCodeSyntax(text = "") {
  return tokenizeMathText(text).some((token) => token.type === "code_span" || token.type === "code_fence");
}

export function deriveWhiteboardPreviewState(text = "") {
  const content = String(text || "");
  const hasContent = Boolean(content.trim());
  const hasMath = hasContent && hasMathSyntax(content);
  const hasCode = hasContent && hasCodeSyntax(content);
  return {
    visible: hasMath || hasCode,
    hasMath,
    hasCode,
  };
}

function createMathNode(expression, { displayMode, raw }) {
  const node = document.createElement("span");
  node.className = displayMode ? "math-render math-render--block" : "math-render math-render--inline";

  const katex = globalThis.katex;
  if (katex && typeof katex.renderToString === "function") {
    try {
      node.innerHTML = katex.renderToString(expression, {
        displayMode,
        output: "mathml",
        throwOnError: false,
        strict: "ignore",
      });
      return node;
    } catch {
      // Fall through to plain text.
    }
  }

  node.classList.add("math-render--fallback");
  node.textContent = raw;
  return node;
}

function createCodeSpanNode(value) {
  const node = document.createElement("code");
  node.className = "rich-text-inline-code";
  node.textContent = value;
  return node;
}

function createCodeFenceNode(token) {
  const wrapper = document.createElement("div");
  wrapper.className = "rich-text-code-block";
  if (token.language) {
    wrapper.dataset.language = token.language;
  }
  if (token.meta) {
    wrapper.dataset.info = token.meta;
  }

  if (token.language || token.meta) {
    const header = document.createElement("div");
    header.className = "rich-text-code__header";
    if (token.language) {
      const language = document.createElement("span");
      language.className = "rich-text-code__language";
      language.textContent = token.language;
      header.append(language);
    }
    if (token.meta) {
      const meta = document.createElement("span");
      meta.className = "rich-text-code__meta";
      meta.textContent = token.meta;
      header.append(meta);
    }
    wrapper.append(header);
  }

  const pre = document.createElement("pre");
  pre.className = "rich-text-code";
  const code = document.createElement("code");
  code.className = "rich-text-code__body hljs";
  const hljs = globalThis.hljs;
  const language = String(token.language || "").trim().toLowerCase();
  let highlighted = "";
  if (hljs && typeof hljs.highlight === "function" && typeof hljs.getLanguage === "function") {
    try {
      if (language && hljs.getLanguage(language)) {
        highlighted = hljs.highlight(token.content || "", {
          language,
          ignoreIllegals: true,
        }).value;
      } else if (!language && typeof hljs.highlightAuto === "function") {
        highlighted = hljs.highlightAuto(token.content || "").value;
      }
    } catch {
      highlighted = "";
    }
  }
  if (highlighted) {
    code.innerHTML = highlighted;
  } else {
    code.textContent = token.content || "";
  }
  if (token.language) {
    code.dataset.language = token.language;
  }
  pre.append(code);
  wrapper.append(pre);
  return wrapper;
}

function appendTextNode(fragment, value) {
  if (!value) {
    return;
  }
  fragment.append(document.createTextNode(value));
}

export function renderRichText(container, text = "", { compact = false, emptyText = "" } = {}) {
  if (!container) {
    return;
  }

  const source = String(text || "");
  container.innerHTML = "";
  container.classList.add("rich-text");
  container.classList.toggle("rich-text--compact", compact);

  if (!source.trim()) {
    if (emptyText) {
      container.textContent = emptyText;
    }
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const token of tokenizeMathText(source)) {
    if (token.type === "text") {
      appendTextNode(fragment, token.value);
      continue;
    }
    if (token.type === "code_span") {
      fragment.append(createCodeSpanNode(token.value));
      continue;
    }
    if (token.type === "code_fence") {
      fragment.append(createCodeFenceNode(token));
      continue;
    }
    fragment.append(createMathNode(token.value, {
      displayMode: token.type === "block_math",
      raw: token.raw,
    }));
  }

  container.append(fragment);
}
