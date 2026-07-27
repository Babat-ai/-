(() => {
  const COLORS = ["yellow", "pink", "blue", "green", "orange", "purple"];

  const boardEl = document.getElementById("board");
  const boardId = boardEl.dataset.boardId;
  const canvas = document.getElementById("canvas");
  const canvasWrapper = document.getElementById("canvas-wrapper");
  const svg = document.getElementById("connectors");
  const template = document.getElementById("note-template");
  const initialNotes = JSON.parse(document.getElementById("initial-notes").textContent);
  const addRootBtn = document.getElementById("add-root-note-btn");

  const notesData = new Map(); // id -> { id, parent_id, text, color, x, y, el }

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

  // --- connectors ---
  function drawConnectors() {
    svg.innerHTML = "";
    notesData.forEach((note) => {
      if (note.parent_id == null) return;
      const parent = notesData.get(note.parent_id);
      if (!parent) return;
      const x1 = parent.el.offsetLeft + parent.el.offsetWidth / 2;
      const y1 = parent.el.offsetTop + parent.el.offsetHeight;
      const x2 = note.el.offsetLeft + note.el.offsetWidth / 2;
      const y2 = note.el.offsetTop;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
      svg.appendChild(line);
    });
  }

  // --- note element ---
  function createNoteEl(note) {
    const frag = template.content.cloneNode(true);
    const el = frag.querySelector(".note");
    el.dataset.noteId = note.id;
    el.classList.add(`note-${note.color}`);
    el.style.left = `${note.x}px`;
    el.style.top = `${note.y}px`;
    el.querySelector(".note-text").textContent = note.text;
    el.querySelectorAll(".dot").forEach((dot) => {
      dot.classList.toggle("selected", dot.dataset.color === note.color);
    });
    canvas.appendChild(el);
    notesData.set(note.id, { ...note, el });
    wireNote(el, note.id);
    return el;
  }

  function collectDescendants(id) {
    const result = [];
    const queue = [id];
    while (queue.length) {
      const current = queue.shift();
      notesData.forEach((note) => {
        if (note.parent_id === current) {
          result.push(note.id);
          queue.push(note.id);
        }
      });
    }
    return result;
  }

  function removeNoteLocally(id) {
    const note = notesData.get(id);
    if (!note) return;
    note.el.remove();
    notesData.delete(id);
  }

  function wireNote(el, noteId) {
    const textEl = el.querySelector(".note-text");

    textEl.addEventListener("blur", () => {
      const text = textEl.textContent.trim();
      notesData.get(noteId).text = text;
      api(`/api/notes/${noteId}`, {
        method: "PATCH",
        body: JSON.stringify({ text }),
      });
    });

    el.querySelectorAll(".dot").forEach((dot) => {
      dot.addEventListener("click", async () => {
        const color = dot.dataset.color;
        await api(`/api/notes/${noteId}`, {
          method: "PATCH",
          body: JSON.stringify({ color }),
        });
        COLORS.forEach((c) => el.classList.remove(`note-${c}`));
        el.classList.add(`note-${color}`);
        el.querySelectorAll(".dot").forEach((d) => {
          d.classList.toggle("selected", d.dataset.color === color);
        });
        notesData.get(noteId).color = color;
      });
    });

    el.querySelector(".delete-note-btn").addEventListener("click", async () => {
      const descendants = collectDescendants(noteId);
      if (descendants.length > 0) {
        if (!confirm("このタスクとぶら下がっているサブタスクをすべて削除します。よろしいですか？")) {
          return;
        }
      }
      await api(`/api/notes/${noteId}`, { method: "DELETE" });
      descendants.forEach(removeNoteLocally);
      removeNoteLocally(noteId);
      drawConnectors();
    });

    el.querySelector(".add-child-btn").addEventListener("click", async () => {
      const parent = notesData.get(noteId);
      const childCount = [...notesData.values()].filter((n) => n.parent_id === noteId).length;
      const x = parent.x + 220;
      const y = parent.y + childCount * 110;
      const note = await api(`/api/boards/${boardId}/notes`, {
        method: "POST",
        body: JSON.stringify({ text: "", color: parent.color, x, y, parent_id: noteId }),
      });
      createNoteEl(note);
      drawConnectors();
      const newEl = notesData.get(note.id).el;
      newEl.querySelector(".note-text").focus();
    });

    // --- drag to reposition ---
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let origX = 0;
    let origY = 0;

    el.addEventListener("pointerdown", (e) => {
      if (e.target.closest("button, .note-text")) return;
      dragging = true;
      el.setPointerCapture(e.pointerId);
      el.classList.add("dragging");
      startX = e.clientX;
      startY = e.clientY;
      const note = notesData.get(noteId);
      origX = note.x;
      origY = note.y;
    });

    el.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const newX = Math.max(0, origX + dx);
      const newY = Math.max(0, origY + dy);
      el.style.left = `${newX}px`;
      el.style.top = `${newY}px`;
      const note = notesData.get(noteId);
      note.x = newX;
      note.y = newY;
      drawConnectors();
    });

    function endDrag(e) {
      if (!dragging) return;
      dragging = false;
      el.classList.remove("dragging");
      const note = notesData.get(noteId);
      api(`/api/notes/${noteId}`, {
        method: "PATCH",
        body: JSON.stringify({ x: note.x, y: note.y }),
      });
    }

    el.addEventListener("pointerup", endDrag);
    el.addEventListener("pointercancel", endDrag);
  }

  // --- add root-level note ---
  addRootBtn.addEventListener("click", async () => {
    const x = canvasWrapper.scrollLeft + canvasWrapper.clientWidth / 2 - 95;
    const y = canvasWrapper.scrollTop + canvasWrapper.clientHeight / 2 - 40;
    const note = await api(`/api/boards/${boardId}/notes`, {
      method: "POST",
      body: JSON.stringify({ text: "", color: "yellow", x, y, parent_id: null }),
    });
    createNoteEl(note);
    drawConnectors();
    notesData.get(note.id).el.querySelector(".note-text").focus();
  });

  // --- initial render ---
  initialNotes.forEach(createNoteEl);
  drawConnectors();
})();
