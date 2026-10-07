# Sistema de Gestión de Usuarios (CRUD) con Monitoreo

implementación de un sistema CRUD para gestionar usuarios, completamente empaquetado con Docker, y sistema de observabilidad y métricas en tiempo real con Prometheus y Grafana.


---


Aplicacion con microservicios utilizando los siguientes componentes
1. **FastAPI (Backend)**
2. **PostgreSQL (Base de datos)**
3. **Prometheus (Monitoreo)** 
4. **Grafana (Visualización)**

Todo corre dentro de contenedores independientes para que no haya que instalar ni configurar nada.

---

## Comunicacion de los servicios

```text
  [Cliente / Navegador / cURL]
               │
               ▼
       [FastAPI en :8000] ──(Guarda y consulta datos)──► [PostgreSQL en :5432]
               │
   (Expone /metrics cada 5s)
               ▼
     [Prometheus en :9090] ──(Alimenta datos al dashboard)──► [Grafana en :3000]
```

---

## Estructura 

```text
user-crud-monitoring/
├── app/
│   ├── Dockerfile           # Cómo se construye la imagen de FastAPI
│   ├── database.py          # Conexión a la base de datos con SQLAlchemy
│   ├── main.py              # Endpoints del CRUD y métricas de Prometheus
│   ├── models.py            # Modelo de la tabla 'users'
│   └── requirements.txt     # Librerías necesarias de Python
├── docs/
│   └── Documentacion_Tecnica_Proyecto.pdf # Documentación técnica oficial del proyecto en PDF
├── prometheus/
│   └── prometheus.yml       # Configuración para que Prometheus vigile a la API
├── grafana/
│   └── provisioning/        # Configuración automática para no tener que configurar Grafana a mano
│       ├── datasources/     # Conecta Prometheus como origen de datos por defecto
│       └── dashboards/      # Carga automáticamente el dashboard con todos los gráficos
├── docker-compose.yml       # Archivo maestro que orquesta los 4 contenedores
├── test_api.py              # Script para probar la API y generar datos en Grafana
└── README.md                # Esta explicación
```


## Viendo las métricas en Grafana

### Enlaces de acceso:
- **Grafana:** [http://localhost:3000](http://localhost:3000) (Usuario: `admin`, Contraseña: `admin`)
- **Prometheus:** [http://localhost:9090](http://localhost:9090)
- **API FastAPI:** [http://localhost:8000](http://localhost:8000)

### Dashboard Listo para usar

1. Entrar a [http://localhost:3000](http://localhost:3000).
2. Entrar a **Dashboards** en el menú de la izquierda.
3. Abrir la carpeta **FastAPI** y entrar en **CRUD & Performance Monitoring"**.
4. Ahí estan los paneles en tiempo real:
   - **Estado del servicio:** (Verde = Prendido, Rojo = Apagado).
   - **Usuarios creados:** Contador de usuarios registrados.
   - **Usuarios actuales en BD:** Cantidad de usuarios en PostgreSQL.
   - **Tasa de creación:** Gráfico de usuarios creados.
   - **Tráfico HTTP:** Solicitudes clasificadas por endpoint (`GET`, `POST`, `PUT`, `DELETE`).
   - **Códigos de respuesta:** Gráfico de respuestas exitosas o errores.
   - **Latencia (p95):** Tiempo de respuesta de la API.
