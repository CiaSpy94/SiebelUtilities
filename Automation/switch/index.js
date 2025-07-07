import { db } from './firebase-config.js';
import {
  ref,
  get,
  set,
  child
} from "https://www.gstatic.com/firebasejs/9.6.1/firebase-database.js";

document.addEventListener("DOMContentLoaded", () => {
  const switchContainer = document.getElementById("switchContainer");
  const addSwitchBtn = document.getElementById("addSwitchBtn");
  const popup = document.getElementById("switchPopup");
  const confirmAdd = document.getElementById("confirmAddSwitch");
  const cancelAdd = document.getElementById("cancelAddSwitch");

  addSwitchBtn.onclick = () => popup.classList.remove("hidden");
  cancelAdd.onclick = () => popup.classList.add("hidden");

  confirmAdd.onclick = async () => {
    const switchName = document.getElementById("switchName").value.trim();
    const release = document.getElementById("release").value.trim().replace('.', '_');
    const mode = document.getElementById("mode").value;
    const basedOn = document.getElementById("basedOn").value;
    const accessControl = document.getElementById("accessControl").value;

    if (!switchName || !release) {
      alert("Switch name and release are required.");
      return;
    }

    const switchRef = ref(db, `switches/${switchName}/${release}`);
    const snapshot = await get(switchRef);

    if (snapshot.exists()) {
      alert("This switch and release already exists.");
      return;
    }

    await set(switchRef, {
      mode,
      basedOn,
      accessControl
    });

    popup.classList.add("hidden");
    loadSwitches();
  };

  async function loadSwitches() {
    switchContainer.innerHTML = "";
    const snapshot = await get(ref(db, "switches"));
    if (snapshot.exists()) {
      const data = snapshot.val();
      Object.keys(data).forEach(switchName => {
        const tile = document.createElement("div");
        tile.className = "switch-tile";
        tile.textContent = switchName;
        tile.onclick = () => {
          window.location.href = `switch-details.html?name=\${encodeURIComponent(switchName)}`;
        };
        switchContainer.appendChild(tile);
      });
    }
  }

  loadSwitches();
});
