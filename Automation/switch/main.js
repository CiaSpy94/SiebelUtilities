import { database } from './firebase-config.js';
import { ref, onValue, set } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-database.js";

const container = document.getElementById('switchContainer');
const modal = document.getElementById('addModal');

function openAddModal() {
  modal.style.display = 'block';
}
function closeAddModal() {
  modal.style.display = 'none';
}

window.openAddModal = openAddModal;
window.closeAddModal = closeAddModal;

function renderSwitches(data) {
  container.innerHTML = '';
  for (const switchName in data) {
    const tile = document.createElement('div');
    tile.className = 'tile';
    tile.innerText = switchName;
    tile.onclick = () => {
      localStorage.setItem('selectedSwitch', switchName);
      window.location.href = 'switch-details.html';
    };
    container.appendChild(tile);
  }
}

function addSwitch() {
  const name = document.getElementById('newSwitch').value;
  const release = document.getElementById('newRelease').value;
  const mode = document.getElementById('newMode').value;
  const basedOn = document.getElementById('newBasedOn').value;
  const accessControl = document.getElementById('newAccessControl').value;

  const switchRef = ref(database, 'switches/' + name);
  onValue(switchRef, (snapshot) => {
    if (snapshot.exists()) {
      alert('Switch already exists!');
    } else {
      set(ref(database, 'switches/' + name + '/' + release), {
        mode,
        basedOn,
        accessControl
      });
      closeAddModal();
    }
  }, { onlyOnce: true });
}

window.addSwitch = addSwitch;

const switchesRef = ref(database, 'switches');
onValue(switchesRef, (snapshot) => {
  if (snapshot.exists()) {
    renderSwitches(snapshot.val());
  }
});