# Diagrama UML Core - Satellite Imagery Gateway

## Diagrama de Clases Principal

```mermaid
classDiagram
    %% Core Configuration
    class Settings {
        +str app_name
        +str version
        +str supabase_url
        +str secret_key
        +str api_v1_prefix
    }

    %% Authentication Core
    class AuthService {
        +authenticate_user(LoginRequest) TokenResponse
        +create_api_key(user_id, ApiKeyRequest) ApiKeyResponse
        +get_user_profile(user_id) UserProfile
    }

    class SupabaseAuth {
        +verify_token(token) User
        +create_user(email, password) User
    }

    %% Imagery Core
    class SearchService {
        +search_imagery(SearchRequest) SearchResponse
        +list_collections() List[CollectionInfo]
        +get_scene(collection_id, scene_id) SceneResponse
    }

    class STACClient {
        +search(collections, bbox, datetime) STACItemCollection
        +get_item(collection_id, item_id) STACItem
        +list_collections() List[STACCollection]
    }

    %% Core Models
    class STACItem {
        +str id
        +str collection
        +List[float] bbox
        +Dict properties
        +Dict assets
        +datetime() datetime
        +cloud_cover() float
    }

    class SearchRequest {
        +datetime date_from
        +datetime date_to
        +List[float] bbox
        +List[str] collections
        +float cloud_cover_max
    }

    class SearchResponse {
        +int total
        +List[SceneResponse] scenes
        +Optional[str] next_token
    }

    class SceneResponse {
        +str id
        +str collection
        +List[float] bbox
        +Dict properties
        +Optional[str] thumbnail_url
    }

    %% Authentication Models
    class LoginRequest {
        +str email
        +str password
    }

    class TokenResponse {
        +str access_token
        +str token_type
        +int expires_in
    }

    class UserProfile {
        +str user_id
        +str email
        +str created_at
    }

    %% Core Relationships
    AuthService --> LoginRequest : uses
    AuthService --> TokenResponse : returns
    AuthService --> UserProfile : returns
    AuthService --> SupabaseAuth : uses

    SearchService --> SearchRequest : uses
    SearchService --> SearchResponse : returns
    SearchService --> SceneResponse : returns
    SearchService --> STACClient : uses

    STACClient --> STACItem : returns
    STACItem --> SceneResponse : converts to

    SupabaseAuth --> Settings : uses
    STACClient --> Settings : uses
```

## Componentes Core del Sistema

### 🔐 Sistema de Autenticación
- **AuthService**: Servicio principal de autenticación
- **SupabaseAuth**: Integración con Supabase
- **LoginRequest/TokenResponse**: DTOs de autenticación

### 🛰️ Sistema de Imágenes Satelitales
- **SearchService**: Servicio principal de búsqueda
- **STACClient**: Cliente para APIs STAC externas
- **STACItem**: Modelo de escena satelital
- **SearchRequest/SearchResponse**: DTOs de búsqueda

### ⚙️ Configuración
- **Settings**: Configuración centralizada

## Flujo Principal

1. **Autenticación**: Usuario → AuthService → SupabaseAuth → Token
2. **Búsqueda**: Usuario → SearchService → STACClient → STAC APIs
3. **Respuesta**: STACItem → SceneResponse → Usuario

## Patrones de Diseño

- **Service Layer Pattern**: AuthService, SearchService
- **Repository Pattern**: STACClient
- **DTO Pattern**: Request/Response models
- **Singleton Pattern**: Settings, SupabaseAuth
