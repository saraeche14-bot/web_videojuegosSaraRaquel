<script setup>
import { ref, computed, onMounted } from 'vue';
import { BASE, meApi, loginApi, logoutApi, listGames, createGame, updateGame, deleteGame, uploadImage } from './api';

// ---------- Estado global UI ----------
const games = ref([]);          // listado desde backend
const loading = ref(false);
const errorMsg = ref('');

// búsqueda y orden
const search = ref('');
const sortAsc = ref(true);

// auth
const me = ref({ authenticated: false, is_admin: false });
const showLogin = ref(false);
const loginForm = ref({ username: '', password: '' });
const loggingIn = ref(false);

// CRUD modal/simple form
const showForm = ref(false);
const editingId = ref(null);
const form = ref({ name: '', description: '', year: String(new Date().getFullYear()), url: '', image_path: null });
const yearError = ref(false);
const selectedFile = ref(null); // archivo de imagen a subir opcional

// ---------- Ayudas ----------
const imageSrc = (g) => {
  return g.image_path ? `${BASE}${g.image_path}` : 'https://via.placeholder.com/220x220?text=Sin+imagen';
};


// filtrar y ordenar
const filteredGames = computed(() => {
  let result = games.value;
  if (search.value) {
    const term = search.value.toLowerCase();
    result = result.filter(g =>
      g.name?.toLowerCase().includes(term) ||
      g.description?.toLowerCase().includes(term)
    );
  }
  result = [...result].sort((a, b) => sortAsc.value ? a.year - b.year : b.year - a.year);
  return result;
});
function toggleSort() { sortAsc.value = !sortAsc.value; }

// keywords 
const keywords = computed(() => {
  const all = filteredGames.value.map(g => g.description || '').join(' ');
  const words = all.toLowerCase().replace(/[^a-záéíóúüñ0-9 ]/gi, '').split(/\s+/).filter(w => w.length > 3);
  const count = {};
  words.forEach(w => { count[w] = (count[w] || 0) + 1; });
  return Object.entries(count).filter(([w, c]) => c > 1).sort((a, b) => b[1] - a[1]).map(([w]) => w);
});

// ---------- Carga inicial ----------
async function loadMe() {
  const { data } = await meApi();
  me.value = data;
}
async function loadGames() {
  loading.value = true;
  try {
    const { data } = await listGames();
    games.value = data;
  } catch (e) {
    errorMsg.value = 'No se pudo cargar la lista de juegos';
  } finally {
    loading.value = false;
  }
}
onMounted(async () => {
  await loadMe();
  await loadGames();
});

// ---------- Auth ----------
async function doLogin() {
  loggingIn.value = true;
  errorMsg.value = '';
  try {
    await loginApi(loginForm.value.username, loginForm.value.password);
    await loadMe();
    showLogin.value = false;
  } catch {
    errorMsg.value = 'Credenciales inválidas';
  } finally {
    loggingIn.value = false;
  }
}
async function doLogout() {
  await logoutApi();
  await loadMe();
}

// ---------- CRUD ----------
function openCreate() {
  editingId.value = null;
  form.value = { name: '', description: '', year: new Date().getFullYear(), url: '', image_path: null };
  selectedFile.value = null;
  showForm.value = true;
}
function openEdit(g) {
  editingId.value = g.id;
  form.value = { name: g.name, description: g.description, year: g.year, url: g.url || '', image_path: g.image_path || null };
  selectedFile.value = null;
  showForm.value = true;
}
function onFileChange(e) {
  const f = e.target.files?.[0];
  selectedFile.value = f || null;
}

async function saveForm() {
  try {
    // Validación del año: debe ser AAAA y ≤ 2025
   const y = String(form.value.year || '').trim();
   yearError.value = !( /^\d{4}$/.test(y) && Number(y) <= 2025 );
   if (yearError.value) {
     errorMsg.value = 'Año inválido';
     return;
   }
    // si hay archivo, súbelo primero
    if (selectedFile.value) {
      const up = await uploadImage(selectedFile.value);
      form.value.image_path = up.image_path; // '/static/uploads/...'
    } else if (!editingId.value) {
      // SOLO en creación, poner la imagen por defecto
      form.value.image_path = '/static/uploads/defecto.jpg';
    } else {
      // En edición, si no se sube archivo, NO tocar image_path
    }

    if (!form.value.name || !form.value.description || !form.value.year) {
      errorMsg.value = 'Faltan campos obligatorios (nombre, descripción, año).';
      return;
    }
    const payload = {
      name: form.value.name,
      description: form.value.description,
      year: parseInt(y, 10),
      url: form.value.url || null,
    };
    if (form.value.image_path !== undefined && form.value.image_path !== null) {
      payload.image_path = form.value.image_path;
    }
    if (editingId.value) {
      await updateGame(editingId.value, payload);
    } else {
      await createGame(payload);
    }
    showForm.value = false;
    await loadGames();
  } catch (e) {
    errorMsg.value = 'No se pudo guardar el juego (¿eres admin logueado?).';
  }
}

async function removeGame(id) {
  if (!confirm('¿Seguro que quieres borrar este juego?')) return;
  try {
    await deleteGame(id);
    await loadGames();
  } catch {
    errorMsg.value = 'No se pudo borrar el juego (¿eres admin logueado?).';
  }
}
</script>

<template>
  <header class="main-header">
    <h1>JUEGOS DE SARA Y RAQUEL</h1>
  </header>

  <!-- Botonera esquina superior derecha -->
  <div class="top-right">
    <!-- Autenticada -->
    <template v-if="me.authenticated">
      <span class="badge">Conectada</span>
      <span v-if="me.is_admin" class="badge admin">Admin</span>
      <button class="btn" @click="doLogout">Cerrar sesión</button>
      <button v-if="me.is_admin" class="btn primary" @click="openCreate">Añadir juego</button>
    </template>

    <!-- Anónima -->
    <template v-else>
      <button class="btn subtle" @click="showLogin = !showLogin">Inicio sesión</button>

      <!-- Popover de login -->
      <div v-if="showLogin" class="login-popover" @click.stop>
        <div class="login-title">Inicio de sesión</div>
        <input v-model="loginForm.username"
              placeholder="Usuario"
              class="input small"
              name="username"
              autocomplete="off" />
        <input v-model="loginForm.password"
              type="password"
              placeholder="Contraseña"
              class="input small"
              name="current-password"
              autocomplete="new-password" />
        <div class="row">
          <button class="btn" @click="showLogin=false">Cancelar</button>
          <button class="btn primary" :disabled="loggingIn" @click="doLogin">Iniciar sesión</button>
        </div>
        <div v-if="errorMsg" class="error small">{{ errorMsg }}</div>
      </div>
    </template>
  </div>


  <div v-if="errorMsg" class="error">{{ errorMsg }}</div>

  <!-- Controles -->
  <input
    v-model="search"
    type="text"
    placeholder="Buscar juegos por nombre o descripción..."
    class="search-input"
  />
  <button @click="toggleSort" class="sort-btn">
    Ordenar por año {{ sortAsc ? '(ascendente)' : '(descendente)' }}
  </button>

  <!-- Lista -->
  <div class="games-panel">
    <div v-if="loading">Cargando juegos...</div>
    <div v-else-if="!filteredGames.length"><em>No hay juegos que coincidan.</em></div>

    <div v-for="game in filteredGames" :key="game.id" class="game-card">
      <img :src="imageSrc(game)" :alt="game.name" class="game-image" />
      <h2>{{ game.name }}</h2>
      <p>{{ game.description }}</p>
      <p><strong>Año:</strong> {{ game.year }}</p>
      <a v-if="game.url" :href="game.url" target="_blank" rel="noopener">Página oficial</a>

      <div v-if="me.is_admin" class="crud-row">
        <button class="btn" @click="openEdit(game)">Editar</button>
        <button class="btn danger" @click="removeGame(game.id)">Borrar</button>
      </div>
    </div>
  </div>

  <!-- Formulario Crear/Editar -->
  <div v-if="showForm" class="modal">
    <div class="modal-card">
      <h3>{{ editingId ? 'Editar juego' : 'Añadir juego' }}</h3>
      <div class="form-grid">
        <label>Nombre<input v-model="form.name" class="input" /></label>
        <label>Descripción<textarea v-model="form.description" class="input"></textarea></label>
        <label>Año
          <input
            v-model="form.year"
            type="text"
            class="input"
            inputmode="numeric"
            pattern="\\d{4}"
            placeholder="AAAA"
            title="Introduce un año de 4 dígitos"
          />
        </label>
        <small v-if="yearError" style="color:#ff8585">Año inválido</small>

        <label>URL<input v-model="form.url" class="input" placeholder="https://..." /></label>
        <label>Imagen (archivo)
          <input type="file" @change="onFileChange" accept="image/*" class="input" />
        </label>
        <div v-if="form.image_path" class="preview">
          <small>Imagen actual:</small>
          <img :src="imageSrc(form)" alt="preview" />
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn" @click="showForm=false">Cancelar</button>
        <button class="btn primary" @click="saveForm">Guardar</button>
      </div>
    </div>
  </div>

  <!-- Keywords -->
  <footer class="keywords-footer">
    <h3>Keywords en las descripciones mostradas:</h3>
    <div v-if="keywords.length">
      <span v-for="word in keywords" :key="word" class="keyword">{{ word }}</span>
    </div>
    <div v-else>
      <em>No hay keywords repetidas.</em>
    </div>
  </footer>
</template>

<style scoped>
:global(body) {
  background: #000000;
  color: #ffffff;
}

/* barra de auth */
.auth-bar{
  display:flex; gap:8px; align-items:center; justify-content:center; margin:12px 0 8px;
}
.badge{
  background:#2a2a2a; border:1px solid #555; padding:4px 8px; border-radius:8px;
}
.badge.admin{ background:#1f3b1f; border-color:#3a6a3a; }
.input{ padding:8px 10px; border-radius:6px; border:1px solid #555; background:#111; color:#fff; width:100%; }
.input.small{ width:140px; }
.btn{ padding:8px 12px; border:none; border-radius:6px; background:#333; color:#fff; cursor:pointer; }
.btn:hover{ background:#444; }
.btn.primary{ background:#ffc814; color:#000; }
.btn.danger{ background:#8b1a1a; }
.error{ color:#ff8585; text-align:center; margin-bottom:8px; }

.games-panel {
  background: #000000; color: #ffffff;
  display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;
}
.game-card {
  background: #312e2e; border: 1px solid #8a8787; border-radius: 8px; padding: 16px; text-align: center;
  width: 250px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); display: flex; flex-direction: column; align-items: center;
}
.crud-row{ display:flex; gap:8px; margin-top:8px; }
.game-image { width: 220px; height: 220px; object-fit: contain; margin-bottom: 5px; }
h2 { color: #ffffff; margin: 8px 0 4px 0; font-size: 1.8em; text-align: center; }
.main-header { background: #000; padding: 24px 0 12px 0; text-align: center; }
.main-header h1 { color:#fff; margin:0; font-size: 2.5em; text-align:center; }
a { color: #ffc400; text-decoration: none; margin-top: 8px; }
a:hover { text-decoration: underline; }
.search-input { display: block; margin: 20px auto 30px auto; padding: 8px 12px; width: 320px; font-size: 1em; border: 1px solid #ccc; border-radius: 6px; }
.sort-btn { display: block; margin: 0 auto 20px auto; padding: 8px 16px; font-size: 1em; background:#1a1a1a; color:#fff; border: none; border-radius: 6px; cursor: pointer; }
.sort-btn:hover { background:#ffc814; color:#000; }
.keywords-footer { margin-top: 40px; padding: 20px 0; background:#000; color:#fff; text-align:center; border-top:1px solid #222; }
.keyword { display:inline-block; background:#ffc814; color:#000; padding:4px 10px; margin:4px; border-radius:12px; font-size:1em; }

/* modal simple */
.modal{ position:fixed; inset:0; background:rgba(0,0,0,.6); display:flex; align-items:center; justify-content:center; }
.modal-card{ width:min(720px, 92vw); background:#1a1a1a; border:1px solid #444; border-radius:12px; padding:16px; }
.form-grid{ display:grid; grid-template-columns: 1fr 1fr; gap:12px; }
.form-grid label{ display:flex; flex-direction:column; gap:6px; color:#ddd; }
.preview img{ width:180px; height:180px; object-fit:contain; border:1px solid #333; border-radius:8px; margin-top:6px; background:#111; }
.modal-actions{ display:flex; justify-content:flex-end; gap:8px; margin-top:12px; }
.main-header { position: relative; }

/* Contenedor en la esquina superior derecha */
.top-right{
  position: absolute; top: 12px; right: 12px;
  display: flex; gap: 8px; align-items: center;
}

/* Botón discreto para abrir el popover */
.btn.subtle{ background:#222; color:#ddd; }
.btn.subtle:hover{ background:#333; }

/* Popover de login */
.login-popover{
  position: absolute; top: 40px; right: 0;
  width: 260px; padding: 12px;
  background: #1a1a1a; border: 1px solid #444; border-radius: 10px;
  display: flex; flex-direction: column; gap: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
  z-index: 50;
}
.login-title{ font-weight: 600; margin-bottom: 4px; }
.row{ display:flex; justify-content:flex-end; gap:8px; }
.error.small{ font-size: .9em; }

@media (max-width: 640px){
  .form-grid{ grid-template-columns: 1fr; }
}
</style>
