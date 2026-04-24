import test from "node:test";
import assert from "node:assert/strict";

import {
  deriveWhiteboardPreviewState,
  hasCodeSyntax,
  hasMathSyntax,
  renderRichText,
  tokenizeMathText,
} from "../src/vantage_v5/webapp/math_render.mjs";

class FakeClassList {
  constructor(owner) {
    this.owner = owner;
    this.values = new Set();
  }

  syncFromString(value) {
    this.values = new Set(String(value || "").split(/\s+/).filter(Boolean));
    this.owner._className = this.toString();
  }

  add(...tokens) {
    for (const token of tokens) {
      if (token) {
        this.values.add(token);
      }
    }
    this.owner._className = this.toString();
  }

  toggle(token, force) {
    if (force === true) {
      this.values.add(token);
    } else if (force === false) {
      this.values.delete(token);
    } else if (this.values.has(token)) {
      this.values.delete(token);
    } else {
      this.values.add(token);
    }
    this.owner._className = this.toString();
    return this.values.has(token);
  }

  contains(token) {
    return this.values.has(token);
  }

  toString() {
    return Array.from(this.values).join(" ");
  }
}

class FakeTextNode {
  constructor(value) {
    this.nodeType = "text";
    this.textContent = String(value || "");
  }
}

class FakeDocumentFragment {
  constructor() {
    this.nodeType = "fragment";
    this.childNodes = [];
  }

  append(...nodes) {
    for (const node of nodes) {
      this.childNodes.push(node);
    }
  }
}

class FakeElement {
  constructor(tagName) {
    this.nodeType = "element";
    this.tagName = String(tagName || "").toUpperCase();
    this.childNodes = [];
    this.dataset = {};
    this._innerHTML = "";
    this._textContent = "";
    this._className = "";
    this.classList = new FakeClassList(this);
  }

  get children() {
    return this.childNodes.filter((node) => node?.nodeType === "element");
  }

  get className() {
    return this._className;
  }

  set className(value) {
    this.classList.syncFromString(value);
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set innerHTML(value) {
    this._innerHTML = String(value || "");
    this.childNodes = [];
    this._textContent = "";
  }

  get textContent() {
    if (this.childNodes.length) {
      return this.childNodes.map((node) => node.textContent || "").join("");
    }
    return this._textContent;
  }

  set textContent(value) {
    this._textContent = String(value || "");
    this._innerHTML = "";
    this.childNodes = [];
  }

  append(...nodes) {
    for (const node of nodes) {
      if (node?.nodeType === "fragment") {
        this.childNodes.push(...node.childNodes);
        continue;
      }
      this.childNodes.push(node);
    }
  }

  appendChild(node) {
    this.append(node);
    return node;
  }
}

function withFakeDom(run) {
  const previousDocument = globalThis.document;
  const previousKatex = globalThis.katex;
  globalThis.document = {
    createElement(tagName) {
      return new FakeElement(tagName);
    },
    createTextNode(value) {
      return new FakeTextNode(value);
    },
    createDocumentFragment() {
      return new FakeDocumentFragment();
    },
  };

  try {
    return run();
  } finally {
    if (previousDocument === undefined) {
      delete globalThis.document;
    } else {
      globalThis.document = previousDocument;
    }
    if (previousKatex === undefined) {
      delete globalThis.katex;
    } else {
      globalThis.katex = previousKatex;
    }
  }
}

test("tokenizeMathText splits prose and inline dollar math", () => {
  assert.deepEqual(
    tokenizeMathText("Energy $E=mc^2$ matters."),
    [
      { type: "text", value: "Energy " },
      { type: "inline_math", value: "E=mc^2", raw: "$E=mc^2$" },
      { type: "text", value: " matters." },
    ],
  );
});

test("tokenizeMathText supports block math with $$ delimiters", () => {
  assert.deepEqual(
    tokenizeMathText("Before\n$$\\int_0^1 x^2 dx$$\nAfter"),
    [
      { type: "text", value: "Before\n" },
      { type: "block_math", value: "\\int_0^1 x^2 dx", raw: "$$\\int_0^1 x^2 dx$$" },
      { type: "text", value: "\nAfter" },
    ],
  );
});

test("tokenizeMathText supports bracket-style latex delimiters", () => {
  assert.deepEqual(
    tokenizeMathText("Inline \\(a+b\\) and block:\\n\\[x^2+y^2=z^2\\]"),
    [
      { type: "text", value: "Inline " },
      { type: "inline_math", value: "a+b", raw: "\\(a+b\\)" },
      { type: "text", value: " and block:\\n" },
      { type: "block_math", value: "x^2+y^2=z^2", raw: "\\[x^2+y^2=z^2\\]" },
    ],
  );
});

test("tokenizeMathText leaves escaped dollar signs as text", () => {
  assert.deepEqual(
    tokenizeMathText("Price is \\$5 and math is $x$."),
    [
      { type: "text", value: "Price is $5 and math is " },
      { type: "inline_math", value: "x", raw: "$x$" },
      { type: "text", value: "." },
    ],
  );
});

test("tokenizeMathText parses inline backtick code without touching math", () => {
  assert.deepEqual(
    tokenizeMathText("Use `sum(items)` with $x^2$."),
    [
      { type: "text", value: "Use " },
      { type: "code_span", value: "sum(items)", raw: "`sum(items)`", ticks: 1 },
      { type: "text", value: " with " },
      { type: "inline_math", value: "x^2", raw: "$x^2$" },
      { type: "text", value: "." },
    ],
  );
});

test("tokenizeMathText does not parse math inside fenced code blocks", () => {
  assert.deepEqual(
    tokenizeMathText("```python\nvalue = '$not_math$'\n```\nThen $y$."),
    [
      { type: "code_fence", language: "python", meta: "", content: "value = '$not_math$'\n", raw: "```python\nvalue = '$not_math$'\n```" },
      { type: "text", value: "\nThen " },
      { type: "inline_math", value: "y", raw: "$y$" },
      { type: "text", value: "." },
    ],
  );
});

test("tokenizeMathText parses fenced code info strings into language and meta cues", () => {
  assert.deepEqual(
    tokenizeMathText("```ts readonly\nconst total = 2;\n```"),
    [
      { type: "code_fence", language: "ts", meta: "readonly", content: "const total = 2;\n", raw: "```ts readonly\nconst total = 2;\n```" },
    ],
  );
});

test("hasMathSyntax only reports true when math tokens are present", () => {
  assert.equal(hasMathSyntax("plain text only"), false);
  assert.equal(hasMathSyntax("Uses $x$ inline"), true);
  assert.equal(hasMathSyntax("```js\nconst total = '$5';\n```"), false);
});

test("hasCodeSyntax reports inline and fenced code while ignoring prose", () => {
  assert.equal(hasCodeSyntax("plain prose"), false);
  assert.equal(hasCodeSyntax("Use `count += 1`"), true);
  assert.equal(hasCodeSyntax("```js\nconst total = 5;\n```"), true);
});

test("deriveWhiteboardPreviewState only reveals preview for math and code content", () => {
  assert.deepEqual(deriveWhiteboardPreviewState("plain prose only"), {
    visible: false,
    hasMath: false,
    hasCode: false,
  });
  assert.deepEqual(deriveWhiteboardPreviewState("Use $x^2$ here."), {
    visible: true,
    hasMath: true,
    hasCode: false,
  });
  assert.deepEqual(deriveWhiteboardPreviewState("```js\nconst total = 5;\n```"), {
    visible: true,
    hasMath: false,
    hasCode: true,
  });
  assert.deepEqual(deriveWhiteboardPreviewState("Solve $x$ with `sum()`."), {
    visible: true,
    hasMath: true,
    hasCode: true,
  });
});

test("renderRichText renders prose, math, and code fences through the shared DOM path", () => {
  withFakeDom(() => {
    globalThis.katex = {
      renderToString(expression, { displayMode }) {
        return `<math data-display="${displayMode ? "block" : "inline"}">${expression}</math>`;
      },
    };
    globalThis.hljs = {
      getLanguage(language) {
        return language === "python";
      },
      highlight(code, { language }) {
        return { value: `<span class="token ${language}">${code}</span>` };
      },
    };

    const container = document.createElement("div");
    renderRichText(
      container,
      "Area $A=\\pi r^2$ with `radius = 3`.\n```python\nvalue = 7\n```",
      { compact: true },
    );

    assert.equal(container.classList.contains("rich-text"), true);
    assert.equal(container.classList.contains("rich-text--compact"), true);
    assert.equal(container.childNodes.length, 6);
    assert.equal(container.childNodes[0].textContent, "Area ");
    assert.equal(container.childNodes[1].classList.contains("math-render--inline"), true);
    assert.equal(
      container.childNodes[1].innerHTML,
      '<math data-display="inline">A=\\pi r^2</math>',
    );
    assert.equal(container.childNodes[2].textContent, " with ");
    assert.equal(container.childNodes[3].tagName, "CODE");
    assert.equal(container.childNodes[3].classList.contains("rich-text-inline-code"), true);
    assert.equal(container.childNodes[3].textContent, "radius = 3");
    assert.equal(container.childNodes[4].textContent, ".\n");
    assert.equal(container.childNodes[5].tagName, "DIV");
    assert.equal(container.childNodes[5].classList.contains("rich-text-code-block"), true);
    assert.equal(container.childNodes[5].dataset.language, "python");
    assert.equal(container.childNodes[5].children[0].tagName, "DIV");
    assert.equal(container.childNodes[5].children[0].classList.contains("rich-text-code__header"), true);
    assert.equal(container.childNodes[5].children[0].children[0].textContent, "python");
    assert.equal(container.childNodes[5].children[1].tagName, "PRE");
    assert.equal(container.childNodes[5].children[1].classList.contains("rich-text-code"), true);
    assert.equal(container.childNodes[5].children[1].children[0].tagName, "CODE");
    assert.equal(container.childNodes[5].children[1].children[0].dataset.language, "python");
    assert.equal(container.childNodes[5].children[1].children[0].classList.contains("hljs"), true);
    assert.equal(
      container.childNodes[5].children[1].children[0].innerHTML,
      '<span class="token python">value = 7\n</span>',
    );
  });
});

test("renderRichText uses local highlight.js markup when available", () => {
  withFakeDom(() => {
    globalThis.hljs = {
      getLanguage(language) {
        return language === "python";
      },
      highlight(source, { language }) {
        return { value: `<span class="hljs-keyword">${language}</span>: ${source}` };
      },
    };

    const container = document.createElement("div");
    renderRichText(container, "```python\nprint('hi')\n```");

    assert.equal(container.childNodes.length, 1);
    assert.equal(container.childNodes[0].classList.contains("rich-text-code-block"), true);
    assert.equal(container.childNodes[0].children[1].children[0].classList.contains("hljs"), true);
    assert.equal(
      container.childNodes[0].children[1].children[0].innerHTML,
      '<span class="hljs-keyword">python</span>: print(\'hi\')\n',
    );
  });
});
