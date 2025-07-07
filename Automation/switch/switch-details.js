import { db } from './firebase-config.js';
import {
  ref,
  get,
  set
} from "https://www.gstatic.com/firebasejs/9.6.1/firebase-database.js";

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const switchName = urlParams.get("name");
  document.getElementById("switchHeader").textContent = `${switchName} Details`;

  const addBtn = document.getElementById("addBtn");
  const popup = document.getElementById("popup");
  const confirmAdd = document.getElementById("confirmAdd");
  const cancelAdd = document.getElementById("cancelAdd");

  addBtn.onclick = () => popup.classList.remove("hidden");
  cancelAdd.onclick = () => popup.classList.add("hidden");

  confirmAdd.onclick = async () => {
    const mode = document.getElementById("mode").value;
    const basedOn = document.getElementById("basedOn").value;
    const accessControl = document.getElementById("accessControl").value;

    const data = {
      mode,
      basedOn,
      accessControl
    };

    await set(ref(db, `switches/${switchName}`), data);
    popup.classList.add("hidden");
    loadExistingData();
  };

  async function loadExistingData() {
    const snapshot = await get(ref(db, `switches/${switchName}`));
    if (snapshot.exists()) {
      const data = snapshot.val();
      const container = document.getElementById("existingData");
      container.innerHTML = `<h3>Existing Data:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
    }
  }

  loadExistingData();
});
