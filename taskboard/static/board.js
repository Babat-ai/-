(() => {
  const boardEl = document.getElementById("board");
  const boardId = boardEl.dataset.boardId;
  const columnsEl = document.getElementById("columns");
  const addCategoryForm = document.getElementById("add-category-form");

  function api(path, options = {}) {
    return fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    }).then((res) => {
      if (!res.ok) throw new Error("request failed");
      return res.json();
    });
  }

  // --- share link copy ---
  const copyBtn = document.getElementById("copy-url-btn");
  copyBtn.addEventListener("click", async () => {
    const input = document.getElementById("share-url");
    input.select();
    try {
      await navigator.clipboard.writeText(input.value);
      const original = copyBtn.textContent;
      copyBtn.textContent = "コピーしました";
      setTimeout(() => (copyBtn.textContent = original), 1500);
    } catch (e) {
      document.execCommand("copy");
    }
  });

  // --- note element ---
  function createNoteEl(note) {
    const div = document.createElement("div");
    div.className = `note note-${note.color}`;
    div.draggable = true;
    div.dataset.noteId = note.id;

    const text = document.createElement("div");
    text.className = "note-text";
    text.contentEditable = "true";
    text.dataset.noteId = note.id;
    text.textContent = note.text;

    const footer = document.createElement("div");
    footer.className = "note-footer";

    const dots = document.createElement("div");
    dots.className = "color-dots";
    ["yellow", "pink", "blue", "green", "orange", "purple"].forEach((color) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = `dot dot-${color}${color === note.color ? " selected" : ""}`;
      dot.dataset.noteId = note.id;
      dot.dataset.color = color;
      dot.title = color;
      dots.appendChild(dot);
    });

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "icon-btn delete-note-btn";
    delBtn.dataset.noteId = note.id;
    delBtn.title = "付箋を削除";
    delBtn.innerHTML = "&times;";

    footer.appendChild(dots);
    footer.appendChild(delBtn);
    div.appendChild(text);
    div.appendChild(footer);
    wireNote(div);
    return div;
  }

  function wireNote(noteEl) {
    const noteId = noteEl.dataset.noteId;

    noteEl.querySelector(".note-text").addEventListener("blur", (e) => {
      api(`/api/notes/${noteId}`, {
        method: "PATCH",
        body: JSON.stringify({ text: e.target.textContent.trim() }),
      });
    });

    noteEl.querySelectorAll(".dot").forEach((dot) => {
      dot.addEventListener("click", async () => {
        const color = dot.dataset.color;
        await api(`/api/notes/${noteId}`, {
          method: "PATCH",
          body: JSON.stringify({ color }),
        });
        noteEl.className = `note note-${color}`;
        noteEl.querySelectorAll(".dot").forEach((d) => {
          d.classList.toggle("selected", d.dataset.color === color);
        });
      });
    });

    noteEl.querySelector(".delete-note-btn").addEventListener("click", async () => {
      await api(`/api/notes/${noteId}`, { method: "DELETE" });
      noteEl.remove();
    });

    noteEl.addEventListener("dragstart", () => {
      noteEl.classList.add("dragging");
    });
    noteEl.addEventListener("dragend", () => {
      noteEl.classList.remove("dragging");
      document.querySelectorAll(".note-list").forEach((list) => {
        list.classList.remove("drag-over");
      });
      persistOrder(noteEl.closest(".note-list"));
    });
  }

  function getDragAfterElement(list, y) {
    const items = [...list.querySelectorAll(".note:not(.dragging)")];
    return items.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: child };
        }
        return closest;
      },
      { offset: Number.NEGATIVE_INFINITY, element: null }
    ).element;
  }

  function persistOrder(list) {
    if (!list) return;
    const categoryId = list.dataset.categoryId;
    const order = [...list.querySelectorAll(".note")].map((n) => Number(n.dataset.noteId));
    api(`/api/categories/${categoryId}/reorder`, {
      method: "POST",
      body: JSON.stringify({ order }),
    });
  }

  function wireNoteList(listEl) {
    listEl.addEventListener("dragover", (e) => {
      e.preventDefault();
      listEl.classList.add("drag-over");
      const dragging = document.querySelector(".note.dragging");
      if (!dragging) return;
      const afterEl = getDragAfterElement(listEl, e.clientY);
      if (afterEl == null) {
        listEl.appendChild(dragging);
      } else {
        listEl.insertBefore(dragging, afterEl);
      }
    });
    listEl.addEventListener("dragleave", (e) => {
      if (e.target === listEl) listEl.classList.remove("drag-over");
    });
  }

  // --- add note form ---
  function wireAddNoteForm(form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const categoryId = form.dataset.categoryId;
      const input = form.querySelector(".add-note-input");
      const text = input.value.trim();
      if (!text) return;
      const colorInput = form.querySelector('input[type="radio"]:checked');
      const color = colorInput ? colorInput.value : "yellow";
      const note = await api(`/api/categories/${categoryId}/notes`, {
        method: "POST",
        body: JSON.stringify({ text, color }),
      });
      const list = form.closest(".column").querySelector(".note-list");
      list.appendChild(createNoteEl(note));
      input.value = "";
      input.focus();
    });
  }

  // --- category rename / delete ---
  function wireColumnTitle(titleEl) {
    titleEl.contentEditable = "true";
    titleEl.addEventListener("blur", () => {
      const name = titleEl.textContent.trim();
      const categoryId = titleEl.dataset.categoryId;
      if (!name) {
        titleEl.textContent = "無題";
        return;
      }
      api(`/api/categories/${categoryId}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
    });
  }

  function wireDeleteColumn(btn) {
    btn.addEventListener("click", async () => {
      const categoryId = btn.dataset.categoryId;
      if (!confirm("このカテゴリと中の付箋をすべて削除します。よろしいですか？")) return;
      await api(`/api/categories/${categoryId}`, { method: "DELETE" });
      btn.closest(".column").remove();
    });
  }

  // --- wire existing DOM on load ---
  document.querySelectorAll(".note").forEach(wireNote);
  document.querySelectorAll(".note-list").forEach(wireNoteList);
  document.querySelectorAll(".add-note-form").forEach(wireAddNoteForm);
  document.querySelectorAll(".column-title:not(.muted)").forEach(wireColumnTitle);
  document.querySelectorAll(".delete-column-btn").forEach(wireDeleteColumn);

  // --- add category ---
  addCategoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("new-category-name");
    const name = input.value.trim();
    if (!name) return;
    const category = await api(`/api/boards/${boardId}/categories`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });

    const column = document.createElement("div");
    column.className = "column";
    column.dataset.categoryId = category.id;
    column.innerHTML = `
      <div class="column-header">
        <h2 class="column-title" data-category-id="${category.id}"></h2>
        <button class="icon-btn delete-column-btn" data-category-id="${category.id}" title="カテゴリを削除" type="button">&times;</button>
      </div>
      <div class="note-list" data-category-id="${category.id}"></div>
      <form class="add-note-form" data-category-id="${category.id}">
        <input type="text" class="add-note-input" placeholder="付箋を書く…" required>
        <div class="color-picker">
          ${["yellow", "pink", "blue", "green", "orange", "purple"]
            .map(
              (c, i) => `
            <label class="color-radio">
              <input type="radio" name="color-${category.id}" value="${c}"${i === 0 ? " checked" : ""}>
              <span class="dot dot-${c}"></span>
            </label>`
            )
            .join("")}
        </div>
        <button type="submit" class="btn btn-small">付箋を追加</button>
      </form>
    `;
    column.querySelector(".column-title").textContent = category.name;

    columnsEl.insertBefore(column, columnsEl.querySelector(".add-column"));

    wireColumnTitle(column.querySelector(".column-title"));
    wireDeleteColumn(column.querySelector(".delete-column-btn"));
    wireNoteList(column.querySelector(".note-list"));
    wireAddNoteForm(column.querySelector(".add-note-form"));

    input.value = "";
  });
})();
