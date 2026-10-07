import time
import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://localhost:8000"

def log(msg):
    print(f"[TEST] {msg}")

def request(method, path, query_params=None):
    url = f"{BASE_URL}{path}"
    if query_params:
        url += "?" + urllib.parse.urlencode(query_params)
    
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            return response.status, content
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return None, str(e)

def main():
    log("Verificando disponibilidad de la API...")
    for _ in range(10):
        status, body = request("GET", "/health")
        if status == 200:
            log("API saludable y conectada a PostgreSQL!")
            break
        time.sleep(2)
    else:
        log("No se pudo conectar a la API en http://localhost:8000. Asegúrate de que docker-compose esté arriba.")
        sys.exit(1)

    # 1. Crear usuarios (POST)
    sample_users = [
        {"name": "Alice", "age": 25},
        {"name": "Bob", "age": 30},
        {"name": "Charlie", "age": 22},
        {"name": "Diana", "age": 28},
        {"name": "Edward", "age": 35}
    ]

    log("\n--- Probando POST /users (Creación de usuarios) ---")
    created_ids = []
    for u in sample_users:
        status, body = request("POST", "/users", u)
        log(f"POST /users?name={u['name']}&age={u['age']} -> Status {status}: {body}")
        if status in (200, 201):
            data = json.loads(body)
            created_ids.append(data.get("id"))

    # 2. Listar usuarios (GET /users)
    log("\n--- Probando GET /users (Listado de usuarios) ---")
    status, body = request("GET", "/users")
    log(f"GET /users -> Status {status}: {body}")

    # 3. Obtener usuario individual (GET /users/{id})
    if created_ids:
        test_id = created_ids[0]
        log(f"\n--- Probando GET /users/{test_id} ---")
        status, body = request("GET", f"/users/{test_id}")
        log(f"GET /users/{test_id} -> Status {status}: {body}")

    # 4. Actualizar usuario (PUT /users/{id})
    if created_ids:
        test_id = created_ids[0]
        log(f"\n--- Probando PUT /users/{test_id}?age=26 ---")
        status, body = request("PUT", f"/users/{test_id}", {"age": 26})
        log(f"PUT /users/{test_id} -> Status {status}: {body}")

    # 5. Eliminar usuario (DELETE /users/{id})
    if len(created_ids) > 1:
        del_id = created_ids[-1]
        log(f"\n--- Probando DELETE /users/{del_id} ---")
        status, body = request("DELETE", f"/users/{del_id}")
        log(f"DELETE /users/{del_id} -> Status {status}: {body}")

    # 6. Consultar métricas de Prometheus
    log("\n--- Consultando GET /metrics (Métricas expuestas para Prometheus) ---")
    status, body = request("GET", "/metrics")
    if status == 200:
        lines = [line for line in body.splitlines() if line.startswith("user_created") or line.startswith("user_deleted") or line.startswith("users_total")]
        log("Métricas clave registradas:")
        for line in lines:
            print("  " + line)
    
    log("\n¡Pruebas finalizadas con éxito! Revisa Grafana en http://localhost:3000 para observar los paneles.")

if __name__ == "__main__":
    main()
