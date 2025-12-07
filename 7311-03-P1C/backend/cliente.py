# cliente.py
import requests

BASE = "http://localhost:9000"
S = requests.Session()  # mantiene cookies

def show(title, data):
    print(f"\n--- {title} ---")
    print(data)

def main():
    # health
    r = S.get(f"{BASE}/api/health")
    show("health", r.json())

    # me (antes de login)
    r = S.get(f"{BASE}/api/auth/me")
    show("me (anon)", r.json())

    # login admin
    r = S.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
    show("login admin", r.json())

    # me (después)
    r = S.get(f"{BASE}/api/auth/me")
    show("me (admin)", r.json())

    # listar juegos
    r = S.get(f"{BASE}/api/games")
    games = r.json()
    show("games (lista)", games[:2])  # muestra 2 por brevedad

    # crear juego
    nuevo = {
        "name": "Prueba CRUD",
        "description": "Creado por cliente de pruebas",
        "year": 2025,
        "url": "https://example.com",
        "image_path": None
    }
    r = S.post(f"{BASE}/api/games", json=nuevo)
    created = r.json()
    show("create", created)
    gid = created["id"]

    # editar juego
    r = S.put(f"{BASE}/api/games/{gid}", json={"description": "Descripción actualizada"})
    show("update", r.json())

    # Subida de imagen y actualización de image_path 
    fname = "demo.png"
    open(fname, "wb").write(b"\x89PNG\r\n\x1a\n")  # PNG mínimo de prueba
    with open(fname, "rb") as f:
        r = S.post(f"{BASE}/api/upload", files={"file": (fname, f, "image/png")})
    uploaded = r.json()  # {'filename': 'demo.png', ...}
    print("upload:", uploaded)
    import os; os.remove(fname)

    image_path = f"/static/uploads/{uploaded['filename']}"
    r = S.put(f"{BASE}/api/games/{gid}", json={"image_path": image_path})
    print("update image_path:", r.json())

    # borrar juego
    r = S.delete(f"{BASE}/api/games/{gid}")
    show("delete", r.json())

    # logout
    r = S.post(f"{BASE}/api/auth/logout")
    show("logout", r.json())

    # me (tras logout)
    r = S.get(f"{BASE}/api/auth/me")
    show("me (anon after logout)", r.json())

if __name__ == "__main__":
    main()
