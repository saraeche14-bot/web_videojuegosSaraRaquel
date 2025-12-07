# servidor.py
import os
import psycopg2
import psycopg2.extras
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import re

# ---------- Configuración ----------
DEFAULT_DSN = "dbname=games user=postgres password=TU_CONTRASEÑA host=localhost port=5432"

def ensure_database(dsn: str):
    parts = dict(re.findall(r'(\w+)=([^\s]+)', dsn))
    dbname = parts.get('dbname', 'games')
    user = parts.get('user', 'postgres')
    password = parts.get('password', '')
    host = parts.get('host', 'localhost')
    port = parts.get('port', '5432')

    try:
        conn = psycopg2.connect(dsn)
        conn.close()
        return
    except psycopg2.OperationalError:
        pass

    maintenance_dsn = f"dbname=postgres user={user} password={password} host={host} port={port}"
    conn = psycopg2.connect(maintenance_dsn)
    conn.set_session(autocommit=True)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(f'CREATE DATABASE "{dbname}"')
    cur.close()
    conn.close()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True  
CORS(app, supports_credentials=True)


#ensure_database(DEFAULT_DSN)

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "API de videojuegos funcionando",
        "health_url": "/api/health"
    })

# ---------- BBDD ----------
class DataBase:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv("DATABASE_URL", DEFAULT_DSN)
        self._conn = None

    def connect(self):
        import psycopg2
        from psycopg2 import sql
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg2.connect(self.dsn)
            except psycopg2.OperationalError as e:
                # Si la base 'games' no existe, la creamos
                if "does not exist" in str(e):
                    print("Base de datos 'games' no encontrada. Creándola automáticamente...")
                    # Extraemos credenciales sin el dbname
                    import re
                    base_dsn = re.sub(r"dbname=\S+", "dbname=postgres", self.dsn)
                    conn_tmp = psycopg2.connect(base_dsn)
                    conn_tmp.autocommit = True
                    cur = conn_tmp.cursor()
                    cur.execute("CREATE DATABASE games;")
                    cur.close()
                    conn_tmp.close()
                    print("Base de datos 'games' creada.")
                    # Reintentamos conectar
                    self._conn = psycopg2.connect(self.dsn)
                else:
                    raise e
        return self._conn

    def execute(self, sql_query, params=None, fetch="none"):
        conn = self.connect()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if params is None:
                cur.execute(sql_query)
            else:
                cur.execute(sql_query, params)

            if fetch == "one":
                row = cur.fetchone()
                conn.commit()
                return row
            elif fetch == "all":
                rows = cur.fetchall()
                conn.commit()
                return rows
            else:
                conn.commit()
                return None


    def init_schema(self):
        self.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)
        self.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            year INT NOT NULL,
            url TEXT,
            image_path TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)

    def ensure_admin(self):
        user = self.execute("SELECT id FROM users WHERE username=%s", ("admin",), fetch="one")
        if not user:
            self.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)",
                ("admin", generate_password_hash("admin123"), True)
            )

    def seed_games_if_empty(self):
        count = self.execute("SELECT COUNT(*) AS c FROM games", fetch="one")["c"]
        if count == 0:
            print("Insertando juegos iniciales...")
            seed = [
                {"name":"Among Us","description":"¡Cuidado con los impostores! Informa de cadáveres y convoca reuniones para expulsar al impostor.","year":2020,"url":"https://buy.among.us/","image_path":None},
                {"name":"League of Legends","description":"MOBA competitivo de Riot Games, donde dos equipos luchan por destruir la base enemiga.","year":2009,"url":None},
                {"name":"DOTA 2","description":"MOBA de Valve, enfrentando dos equipos de cinco jugadores en intensas batallas estratégicas.","year":2013,"url":"https://www.dota2.com/","image_path":None},
                {"name":"King of Glory","description":"MOBA móvil muy popular en China, desarrollado por Tencent Games.","year":2015,"url":"https://pvp.qq.com/","image_path":None},
                {"name":"Fortnite","description":"Battle Royale de Epic Games, donde 100 jugadores luchan por ser el último en pie.","year":2017,"url":"https://www.fortnite.com/","image_path":None},
                {"name":"PUBG: Battlegrounds","description":"Battle Royale pionero, donde los jugadores compiten en un mapa para sobrevivir.","year":2017,"url":"https://pubg.com/","image_path":None},
                {"name":"Counter-Strike 2","description":"Shooter táctico de Valve, sucesor de CS:GO, enfrentando terroristas y antiterroristas.","year":2023,"url":"https://www.counter-strike.net/cs2","image_path":None},
                {"name":"Valorant","description":"Shooter táctico de Riot Games, con agentes y habilidades únicas en partidas 5v5.","year":2020,"url":"https://playvalorant.com/","image_path": None},
                {"name":"Call of Duty: Warzone 2.0","description":"Battle Royale de Activision, con acción frenética y mapas enormes.","year":2022,"url":"https://www.callofduty.com/warzone","image_path":None},
                {"name":"EA Sports FC 24","description":"Simulador de fútbol de EA Sports, sucesor de FIFA, con licencias oficiales y modos variados.","year":2023,"url":"https://www.ea.com/games/ea-sports-fc/fc-24","image_path":None},
                {"name":"Minecraft","description":"Juego de construcción y aventuras en mundo abierto, donde puedes crear y explorar sin límites.","year":2011,"url":"https://www.minecraft.net/","image_path":None},
                {"name":"Tres en raya","description":"Versión web del clásico tres en raya. Juega en el navegador contra otro jugador local.","year":2025,"url":"/tictactoe.html","image_path":None}
            ]
            for g in seed:
                img = g.get("image_path") or "/static/uploads/defecto.jpg"
                self.execute("""
                    INSERT INTO games (name, description, year, url, image_path)
                    VALUES (%s, %s, %s, %s, %s)
                """, (g["name"], g["description"], g["year"], g["url"], img))

            print("Juegos iniciales cargados correctamente.")


db = DataBase()
db.init_schema()
db.ensure_admin()
db.seed_games_if_empty()
db.execute("UPDATE games SET image_path = '/static/' || image_path WHERE image_path LIKE 'uploads/%'")
db.execute("UPDATE games SET image_path = '/' || image_path WHERE image_path IS NOT NULL AND image_path <> '' AND image_path NOT LIKE '/%'")
db.execute("UPDATE games SET image_path = '/static/uploads/defecto.jpg' WHERE image_path IS NULL OR image_path = ''")

# ---------- Ayudas ----------
def require_admin():
    if not session.get("user_id") or not session.get("is_admin"):
        return jsonify({"error": "admin_required"}), 403

def game_from_request(data, partial=False):
    fields = {}
    if "name" in data or not partial:
        fields["name"] = data.get("name")
    if "description" in data or not partial:
        fields["description"] = data.get("description")
    if "year" in data or not partial:
        fields["year"] = data.get("year")
    if "url" in data or not partial:
        fields["url"] = data.get("url")

    # Imagen:
    if partial:
        # En updates, solo tocar image_path si viene en la petición
        if "image_path" in data:
            fields["image_path"] = data.get("image_path")
    else:
        # En creación, si no viene o viene vacío -> por defecto
        fields["image_path"] = data.get("image_path") or "/static/uploads/defecto.jpg"

    return fields


# ---------- Rutas ----------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# --- Auth ---
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    user = db.execute("SELECT id, password_hash, is_admin FROM users WHERE username=%s",
                      (username,), fetch="one")
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "UPS! Contraseña incorrecta..."}), 401
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["is_admin"] = bool(user["is_admin"])
    return jsonify({"message": "logueado!", "user": {"username": username, "is_admin": bool(user["is_admin"])}})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Hasta la próxima"})

@app.route("/api/auth/me", methods=["GET"])
def me():
    if not session.get("user_id"):
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, "is_admin": bool(session.get("is_admin", False))})

# --- Games ---
@app.route("/api/games", methods=["GET"])
def list_games():
    rows = db.execute("SELECT * FROM games ORDER BY id ASC", fetch="all")
    return jsonify(rows)

@app.route("/api/games/<int:game_id>", methods=["GET"])
def get_game(game_id):
    row = db.execute("SELECT * FROM games WHERE id=%s", (game_id,), fetch="one")
    if not row:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(row)

@app.route("/api/games", methods=["POST"])
def create_game():
    deny = require_admin()
    if deny: return deny
    data = request.get_json() or {}
    g = game_from_request(data, partial=False)
    if not all([g.get("name"), g.get("description"), g.get("year")]):
        return jsonify({"error": "rellena todos los campos"}), 400
    row = db.execute("""
        INSERT INTO games (name, description, year, url, image_path)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *;
    """, (g["name"], g["description"], g["year"], g.get("url"), g.get("image_path")), fetch="one")
    return jsonify(row), 201


@app.route("/api/games/<int:game_id>", methods=["PUT"])
def update_game(game_id):
    deny = require_admin()
    if deny: return deny
    data = request.get_json() or {}
    g = game_from_request(data, partial=True)
    if not g:
        return jsonify({"error": "sin cambios"}), 400

    sets = []
    params = []
    for k, v in g.items():
        sets.append(f"{k}=%s")
        params.append(v)
    sets.append("updated_at=NOW()")
    params.append(game_id)

    row = db.execute(f"""
        UPDATE games SET {", ".join(sets)} WHERE id=%s RETURNING *;
    """, tuple(params), fetch="one")
    if not row:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(row)

@app.route("/api/games/<int:game_id>", methods=["DELETE"])
def delete_game(game_id):
    deny = require_admin()
    if deny: return deny
    row = db.execute("DELETE FROM games WHERE id=%s RETURNING id", (game_id,), fetch="one")
    if not row:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify({"deleted": row["id"]})

# --- Upload de imágenes ---
@app.route("/api/upload", methods=["POST"])
def upload_image():
    deny = require_admin()
    if deny: return deny
    if "file" not in request.files:
        return jsonify({"error": "sin archivo"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "nombre vacio"}), 400
    # Guardar con nombre seguro (simple)
    filename = f.filename.replace(" ", "_")
    save_path = os.path.join(UPLOAD_DIR, filename)
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(save_path):
        filename = f"{base}_{i}{ext}"
        save_path = os.path.join(UPLOAD_DIR, filename)
        i += 1
    f.save(save_path)
    return jsonify({"filename": filename})


# Servir archivos de /static/uploads si fuera necesario acceder directo (Flask ya sirve /static)
@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(port=9000, debug=True)




