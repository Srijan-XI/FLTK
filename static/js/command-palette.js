/**
 * Command Palette (Ctrl+K or ⌘+K)
 * Pure vanilla JavaScript. No backend dependencies.
 */

const PALETTE_COMMANDS = [
  { label: "Home", url: "/", icon: "🏠" },
  { label: "Deadline Predictor", url: "/drp/", icon: "⏰" },
  { label: "DRP History", url: "/drp/history", icon: "📚" },
  { label: "New Invoice", url: "/wft/invoices/new", icon: "🧾" },
  { label: "New Quote", url: "/wft/quotes/new", icon: "💼" },
  { label: "New Contract", url: "/wft/contracts/new", icon: "📝" },
  { label: "Clients", url: "/wft/clients", icon: "👤" },
  { label: "Log Hours", url: "/wft/hours", icon: "⏱" },
  { label: "Start Timer", url: "/wft/timer", icon: "⏱" },
  { label: "Add Expense", url: "/wft/expenses", icon: "💸" },
  { label: "View Invoices", url: "/wft/invoices", icon: "🧾" },
  { label: "Recurring Invoices", url: "/wft/invoices/recurring", icon: "🔁" },
  { label: "View Quotes", url: "/wft/quotes", icon: "💼" },
  { label: "View Contracts", url: "/wft/contracts", icon: "📝" },
  { label: "View Projects", url: "/wft/sdlc/projects", icon: "🗂" },
  { label: "SDLC Templates", url: "/wft/sdlc/templates", icon: "🧩" },
  { label: "View Reports", url: "/wft/reports", icon: "📈" },
  { label: "Financial Snapshot", url: "/wft/finance/snapshot", icon: "💰" },
  { label: "View Calendar", url: "/wft/calendar", icon: "📅" },
  { label: "A/R Ageing Report", url: "/wft/invoices/ageing", icon: "📊" },
  { label: "Overdue Invoices", url: "/wft/invoices/overdue", icon: "⚠" },
  { label: "Weekly Reviews", url: "/wft/reviews", icon: "📝" },
  { label: "Settings", url: "/wft/settings", icon: "⚙" },
  { label: "Sitemap", url: "/wft/sitemap", icon: "🗺" },
  { label: "Backup Data", url: "/wft/backup", icon: "💾" },
  { label: "Search", url: "/wft/search", icon: "🔍" },
];

function initCommandPalette() {
  // Create modal HTML
  const modal = document.createElement("div");
  modal.id = "command-palette-modal";
  modal.style.display = "none";
  modal.style.position = "fixed";
  modal.style.top = "0";
  modal.style.left = "0";
  modal.style.width = "100%";
  modal.style.height = "100%";
  modal.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
  modal.style.zIndex = "9999";
  modal.style.backdropFilter = "blur(2px)";
  modal.addEventListener("click", closeCommandPalette);

  const container = document.createElement("div");
  container.style.position = "absolute";
  container.style.top = "50%";
  container.style.left = "50%";
  container.style.transform = "translate(-50%, -50%)";
  container.style.backgroundColor = "white";
  container.style.borderRadius = "8px";
  container.style.width = "90%";
  container.style.maxWidth = "500px";
  container.style.maxHeight = "70vh";
  container.style.overflow = "hidden";
  container.style.display = "flex";
  container.style.flexDirection = "column";
  container.style.boxShadow = "0 20px 25px rgba(0, 0, 0, 0.15)";
  container.addEventListener("click", (e) => e.stopPropagation());

  const searchInput = document.createElement("input");
  searchInput.id = "command-palette-search";
  searchInput.placeholder = "Search commands...";
  searchInput.type = "text";
  searchInput.style.padding = "12px 16px";
  searchInput.style.fontSize = "14px";
  searchInput.style.border = "none";
  searchInput.style.borderBottom = "1px solid #ecf0f1";
  searchInput.style.outline = "none";
  searchInput.autoComplete = "off";
  searchInput.addEventListener("input", filterCommandPalette);
  searchInput.addEventListener("keydown", handleCommandPaletteKeydown);

  const resultsList = document.createElement("ul");
  resultsList.id = "command-palette-results";
  resultsList.style.listStyle = "none";
  resultsList.style.margin = "0";
  resultsList.style.padding = "0";
  resultsList.style.overflowY = "auto";
  resultsList.style.flex = "1";

  container.appendChild(searchInput);
  container.appendChild(resultsList);
  modal.appendChild(container);
  document.body.appendChild(modal);

  // Render initial command list
  renderCommandPaletteResults(PALETTE_COMMANDS);

  // Keyboard shortcut
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      openCommandPalette();
    }
    if (e.key === "Escape") {
      closeCommandPalette();
    }
  });
}

function openCommandPalette() {
  const modal = document.getElementById("command-palette-modal");
  const searchInput = document.getElementById("command-palette-search");
  modal.style.display = "block";
  searchInput.value = "";
  searchInput.focus();
  renderCommandPaletteResults(PALETTE_COMMANDS);
}

function closeCommandPalette() {
  const modal = document.getElementById("command-palette-modal");
  modal.style.display = "none";
}

function filterCommandPalette() {
  const query = document.getElementById("command-palette-search").value.toLowerCase();
  const filtered = PALETTE_COMMANDS.filter((cmd) =>
    cmd.label.toLowerCase().includes(query)
  );
  renderCommandPaletteResults(filtered);
}

function renderCommandPaletteResults(commands) {
  const resultsList = document.getElementById("command-palette-results");
  resultsList.innerHTML = "";

  if (commands.length === 0) {
    const item = document.createElement("li");
    item.style.padding = "12px 16px";
    item.style.color = "#7f8c8d";
    item.textContent = "No commands found.";
    resultsList.appendChild(item);
    return;
  }

  commands.forEach((cmd, idx) => {
    const item = document.createElement("li");
    item.style.padding = "12px 16px";
    item.style.cursor = "pointer";
    item.style.borderBottom = "1px solid #ecf0f1";
    item.style.display = "flex";
    item.style.alignItems = "center";
    item.style.gap = "12px";
    item.style.backgroundColor = idx === 0 ? "#f8f9fa" : "transparent";
    item.onmouseover = () => {
      item.style.backgroundColor = "#f8f9fa";
      // Highlight this and deselect others
      document.querySelectorAll("#command-palette-results li").forEach((li) => {
        li.style.backgroundColor = li === item ? "#f8f9fa" : "transparent";
      });
    };
    item.onclick = () => {
      window.location.href = cmd.url;
    };

    const icon = document.createElement("span");
    icon.textContent = cmd.icon;
    icon.style.fontSize = "16px";

    const label = document.createElement("span");
    label.textContent = cmd.label;
    label.style.color = "#34495e";
    label.style.fontWeight = "500";
    label.style.flex = "1";

    item.appendChild(icon);
    item.appendChild(label);
    resultsList.appendChild(item);
  });
}

function handleCommandPaletteKeydown(e) {
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const items = document.querySelectorAll("#command-palette-results li");
    let activeIndex = 0;
    for (let i = 0; i < items.length; i++) {
      if (items[i].style.backgroundColor === "rgb(248, 249, 250)") {
        activeIndex = i;
        break;
      }
    }

    if (e.key === "ArrowDown" && activeIndex < items.length - 1) {
      activeIndex += 1;
    } else if (e.key === "ArrowUp" && activeIndex > 0) {
      activeIndex -= 1;
    }

    items.forEach((item, idx) => {
      item.style.backgroundColor = idx === activeIndex ? "#f8f9fa" : "transparent";
    });
  } else if (e.key === "Enter") {
    e.preventDefault();
    const activeItem = document.querySelector(
      "#command-palette-results li[style*='rgb(248, 249, 250)']"
    );
    if (activeItem) {
      activeItem.click();
    }
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initCommandPalette);
