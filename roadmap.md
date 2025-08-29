# Prompt para Claude Code

Quiero que generes un **proyecto FastAPI** profesional siguiendo este roadmap y estructura. El proyecto se llama **Satellite Imagery Gateway** y será parte de un portfolio/CV.

## Objetivo

Construir una API unificada para consultar, descargar y procesar **imágenes satelitales** (ej. Sentinel-2, Landsat) usando fuentes públicas (STAC APIs de NASA/USGS, Copernicus). El usuario provee coordenadas y fechas, y la API devuelve escenas disponibles, metadatos, descargas y procesamientos básicos (clip, índices NDVI/NDWI/NDBI).

---

## Requisitos de alto nivel

1. **FastAPI + Swagger/OpenAPI** con documentación limpia en `/docs`.
2. **Endpoints principales**:

   * `/api/v1/imagery/search` → búsqueda de escenas por lat/lon/fechas.
   * `/api/v1/imagery/scenes/{id}` → detalle de una escena.
   * `/api/v1/imagery/download/{id}` → descarga de bandas o RGB combinadas.
   * `/api/v1/imagery/clip` → recorte de escena con polígono GeoJSON.
   * `/api/v1/imagery/indices/{id}` → cálculo de índices espectrales.
   * `/api/v1/imagery/coverage` → qué misiones cubren un área en cierta fecha.
3. **Auth JWT** + scopes de acceso.
4. **Integraciones externas**: adaptadores STAC (SentinelAdapter, LandsatAdapter) con normalización de resultados.
5. **Cache** de búsquedas en Redis, DB mínima en Postgres/SQLite con SQLModel.
6. **Tests** con pytest para rutas clave.
7. **Infra básica**: Dockerfile, docker-compose.yml, Makefile, GitHub Actions con lint + tests.

---

## Estructura de carpetas (usar convención pedida)

```
app/
  main.py
  core/
    config.py
    logging.py
  api/
    v1/
      __init__.py
      features/
        authentication/
          __init__.py
          dto.py
          errors.py
          handler.py
          router.py
          service.py
        imagery/
          search/
            __init__.py
            dto.py
            errors.py
            handler.py
            router.py
            service.py
          scenes/
            __init__.py
            dto.py
            errors.py
            handler.py
            router.py
            service.py
          download/
            __init__.py
            dto.py
            errors.py
            handler.py
            router.py
            service.py
          clip/
            __init__.py
            dto.py
            errors.py
            handler.py
            router.py
            service.py
          indices/
            __init__.py
            dto.py
            errors.py
            handler.py
            router.py
            service.py
          coverage/
            __init__.py
            dto.py
            errors.py
            handler.py
            router.py
            service.py
        ui_template_version/
          bulk_validate_schema/
            __init__.py
            dto.py
            errors.py
            handler.py
            router.py
            service.py
      pages/
        health/
          __init__.py
          router.py
      shared/
        auth/
          __init__.py
          jwt.py
          deps.py
          security.py
        db/
          __init__.py
          session.py
          models.py
        clients/
          __init__.py
          stac_base.py
          sentinel.py
          landsat.py
        utils/
          __init__.py
          geo.py
          pagination.py
          caching.py
```

---

## Patrón de cada **feature**

Cada feature (ej. `search/`, `clip/`) debe tener 5 archivos:

* `dto.py`: Pydantic schemas (request/response).
* `errors.py`: errores específicos como funciones que devuelven HTTPException.
* `service.py`: lógica de dominio (ej. llamar adaptadores STAC, procesar índices).
* `handler.py`: orquesta service + transforma excepciones en errores HTTP.
* `router.py`: define endpoints FastAPI y conecta handler.

---

## Ejemplos de contratos de endpoints

**Search** (`GET /api/v1/imagery/search`):

* Query: `lat, lon, date_from, date_to, cloud_cover_lte, collection, page, page_size`.
* Response:

```json
{
  "items": [
    {
      "scene_id": "S2A_20240801_...",
      "collection": "sentinel-2",
      "datetime": "2024-08-01T13:45:00Z",
      "bbox": [-58.5,-34.7,-58.3,-34.5],
      "cloud_cover": 12.3,
      "preview_jpg": "https://.../thumb.jpg",
      "assets": {"B02":"...", "B03":"...", "B04":"..."}
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1234
}
```

**Clip** (`POST /api/v1/imagery/clip`):

* Body: `{ "scene_id": "S2A_...", "geometry": { "type": "Polygon", "coordinates": [...] }, "bands":["B04","B03","B02"], "format":"GeoTIFF" }`
* Response: archivo (stream) o `202 Accepted` con `job_id`.

**Indices** (`GET /api/v1/imagery/indices/{scene_id}`):

* Query: `index=NDVI|NDWI|NDBI`, `geometry=...`, `stats=true|false`.
* Response (stats=true): `{ "index":"NDVI", "min":-0.2, "max":0.86, "mean":0.41, "std":0.12 }`.

---

## Shared utils

* `auth/jwt.py` → crear/validar tokens.
* `auth/deps.py` → dependencia FastAPI `get_current_user`.
* `clients/stac_base.py` → clase base `StacAdapter` con `search()` y `get_item()`.
* `clients/sentinel.py`, `clients/landsat.py` → adaptadores reales (pueden ser stub al inicio).
* `utils/pagination.py` → clamp de page y size.
* `utils/geo.py` → validaciones de geometría (usar shapely/geojson).

---

## Roadmap de implementación

1. **Infra básica**: `main.py`, configuración Pydantic (`core/config.py`), routers en `main`.
2. **Health page** (`/api/v1/health/live`, `/api/v1/health/ready`).
3. **Auth feature** con login mock (`email@example.com`, pass=secret → token).
4. **Imagery/search** implementando integración con un STAC público (p.ej. Sentinel-2).
5. **Imagery/scenes** devolviendo detalles normalizados.
6. **Imagery/download** stub inicial (redirige a asset URL).
7. **Imagery/clip** stub inicial (valida GeoJSON, devuelve `202 Accepted`).
8. **Imagery/indices** calcula NDVI con Rasterio si posible, o mock.
9. **Coverage** stub con colecciones disponibles según fecha.
10. **Tests** de `search`, `clip` y `indices` con httpx.AsyncClient.
11. **Docker** + `docker-compose` (api, redis, postgres).
12. **CI** con GitHub Actions (lint + tests).

---

## Extras

* Documentar ejemplos en Swagger con `response_model` y `examples`.
* Definir `x-codeSamples` en OpenAPI para curl y Python requests.
* Logging estructurado con `loguru` o `structlog`.
* Preparar `Makefile` con targets `dev`, `test`, `lint`, `up`.

---

👉 **Instrucción final:**
Generá el repo inicial siguiendo esta estructura, con al menos los features `authentication` y `imagery/search` implementados (con dto/service/handler/router completos). Los otros features (`scenes`, `download`, `clip`, `indices`, `coverage`) deben tener sus archivos creados con TODOs/documentación para extender. Incluí `docker-compose.yml`, `Dockerfile`, `.env.example`, `requirements.txt`, `tests/` básicos, y `README.md` con instrucciones.
