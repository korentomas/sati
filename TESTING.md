# Guía de Testing

## Resumen

Este proyecto usa **pytest** para testing. Los tests están organizados en:
- **Tests unitarios** (`tests/unit/`): Prueban componentes individuales
- **Tests de integración** (`tests/integration/`): Prueban múltiples componentes juntos

## Estructura de Tests

```
tests/
├── conftest.py                    # Fixtures compartidas (DB, client)
├── unit/
│   ├── test_db_models.py         # Tests del modelo User
│   ├── test_auth_service.py      # Tests de AuthService
│   ├── test_jwt.py               # Tests de JWT y password hashing
│   └── test_authentication_endpoints.py  # Tests de endpoints HTTP
└── integration/
    └── test_api_integration.py   # Tests de integración
```

## Configuración

Los tests usan una **base de datos SQLite en memoria** para ser rápidos y aislados. Cada test tiene su propia sesión de base de datos que se limpia automáticamente.

### Fixtures Principales

- `db_session`: Sesión de base de datos para cada test
- `client`: TestClient de FastAPI con base de datos de test

## Cómo Ejecutar los Tests

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Ejecutar todos los tests

```bash
pytest
```

### Ejecutar tests con más detalle

```bash
pytest -v
```

### Ejecutar un archivo específico

```bash
pytest tests/unit/test_db_models.py -v
```

### Ejecutar una clase de tests específica

```bash
pytest tests/unit/test_auth_service.py::TestAuthService -v
```

### Ejecutar un test específico

```bash
pytest tests/unit/test_auth_service.py::TestAuthService::test_register_user_success -v
```

### Ejecutar con cobertura

```bash
pytest --cov=app --cov-report=html
```

## Tests Disponibles

### Tests Unitarios

#### `test_db_models.py`
- ✅ Crear usuario en base de datos
- ✅ Email único
- ✅ Usuario activo por defecto
- ✅ Timestamps automáticos

#### `test_auth_service.py`
- ✅ Registro de usuario exitoso
- ✅ Registro con email duplicado (falla)
- ✅ Autenticación exitosa
- ✅ Autenticación con contraseña incorrecta
- ✅ Autenticación de usuario inexistente
- ✅ Usuario inactivo no puede autenticarse
- ✅ Obtener perfil de usuario
- ✅ Perfil de usuario inexistente

#### `test_jwt.py`
- ✅ Crear token JWT
- ✅ Verificar token válido
- ✅ Verificar token inválido
- ✅ Token sin campo 'sub' (rechazado)
- ✅ Expiración de token
- ✅ Hashing de contraseñas (con parámetros)
- ✅ Verificación de contraseñas
- ✅ Contraseñas diferentes producen hashes diferentes

#### `test_authentication_endpoints.py`
- ✅ Registro exitoso
- ✅ Registro con email duplicado
- ✅ Login exitoso
- ✅ Login con credenciales inválidas
- ✅ Login de usuario inexistente
- ✅ Login con campos faltantes
- ✅ Obtener perfil con token válido
- ✅ Obtener perfil sin token
- ✅ Obtener perfil con token inválido
- ✅ Crear API key con token válido
- ✅ Crear API key sin token
- ✅ Listar API keys
- ✅ Y más...

## Ejemplos de Uso

### Test de Registro

```python
def test_register_success(self, client: TestClient):
    register_data = {"email": "newuser@example.com", "password": "password123"}
    response = client.post("/api/v1/auth/register", json=register_data)
    
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Test de Servicio

```python
def test_register_user_success(self, db_session: Session):
    service = AuthService(db_session)
    user = service.register_user("test@example.com", "password123")
    
    assert user.email == "test@example.com"
    assert user.password_hash != "password123"  # Debe estar hasheado
```

## Notas Importantes

1. **Base de datos de test**: Cada test usa SQLite en memoria, por lo que son rápidos y aislados
2. **Limpieza automática**: Las tablas se crean y eliminan automáticamente para cada test
3. **Fixtures**: Usa `@pytest.fixture` para compartir configuración entre tests
4. **Parametrización**: Algunos tests usan `@pytest.mark.parametrize` para probar múltiples casos

## Troubleshooting

### Error: "No module named 'pytest'"
```bash
pip install pytest pytest-asyncio pytest-cov
```

### Error: "Database locked"
- Los tests deberían ejecutarse secuencialmente, no en paralelo
- Verifica que no haya otros procesos usando la base de datos

### Error: "Table already exists"
- Los fixtures deberían limpiar las tablas automáticamente
- Si persiste, verifica que `Base.metadata.drop_all()` se ejecute en el `finally`

## Próximos Pasos

- [ ] Agregar tests de integración más completos
- [ ] Agregar tests de performance
- [ ] Configurar GitHub Actions para CI/CD
- [ ] Agregar tests de carga con múltiples usuarios

