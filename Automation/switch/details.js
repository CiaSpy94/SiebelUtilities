import { database } from './firebase-config.js';
import { ref, onValue, update } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-database.js";

const switchName = localStorage.getItem('selectedSwitch');
document.getElementById('switchHeader').innerText = switchName + ' details';

const container = document.getElementById('releaseContainer');
const modal = document.getElementById('editModal');
let currentRelease = '';

function openEditModal(release, data) {
  currentRelease = release;
  document.getElementById('editMode').value = data.mode;
  document.getElementById('editBasedOn').value = data.basedOn;
  document.getElementById('editAccessControl').value = data.accessControl;
  modal.style.display = 'block';
}
function closeEditModal() {
  modal.style.display = 'none';
}
window.closeEditModal = closeEditModal;

function saveEdit() {
  const mode = document.getElementById('editMode').value;
  const basedOn = document.getElementById('editBasedOn').value;
  const accessControl = document.getElementById('editAccessControl').value;

  update(ref(database, 'switches/' + switchName + '/' + currentRelease), {
    mode,
    basedOn,
    accessControl
  });
  closeEditModal();
}
window.saveEdit = saveEdit;

const switchRef = ref(database, 'switches/' + switchName);
onValue(switchRef, (snapshot) => {
  if (snapshot.exists()) {
    const data = snapshot.val();
    container.innerHTML = '';
    for (const release in data) {
      const div = document.createElement('div');
      div.className = 'tile';
      div.innerHTML = `<strong>${release}</strong><br>
        Mode: ${data[release].mode}<br>
        Based On: ${data[release].basedOn}<br>
        Access Control: ${data[release].accessControl}<br>
        <button onclick='openEditModal("${release}", ${JSON.stringify(data[release]).replace(/"/g, '&quot;')})'>Edit</button>`;
      container.appendChild(div);
    }
  }
});
window.openEditModal = openEditModal;