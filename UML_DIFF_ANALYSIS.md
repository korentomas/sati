# UML Difference Analysis: Current vs. Aligned Version

## Current UML Statistics
- **Total Lines**: 201 lines
- **Classes Defined**: 19 classes
- **Methods Defined**: ~45 methods
- **Relationships**: 18 relationships

## Required Additions for Full Alignment

### 1. New Service Classes to Add (From Existing Implementation)

```mermaid
%% +45 lines approximately
class ProcessingService {
    +calculate_index(scene_id, index_type) ProcessedLayer
    +run_analysis(layer_id, analysis_type) AnalysisResult
    +apply_enhancement(layer_id, adjustments) Layer
    +batch_process(scene_ids, operations) JobStatus
    +create_job(operation_type, parameters) Job
    +get_job_status(job_id) JobStatus
}

class MosaicService {
    +create_mosaic(scene_ids, options) MosaicResult
    +get_mosaic_status(mosaic_id) JobStatus
    +list_user_mosaics(user_id) List~Mosaic~
}

class DirectDownloadService {
    +download_scene(scene_id, options) DownloadResult
    +parallel_download(scene_ids) List~DownloadResult~
    +get_download_status(download_id) JobStatus
}

class TileService {
    +generate_tiles(layer, zoom_levels) TileSet
    +get_tile(x, y, z, layer_id) Tile
    +create_tile_url(layer) str
}
```

### 2. Processing Support Classes (From uml_extended.mermaid)

```mermaid
%% +30 lines approximately
class IndexCalculator {
    +calculate_ndvi(red_band, nir_band) Array
    +calculate_ndwi(green_band, nir_band) Array
    +calculate_evi(red, nir, blue) Array
    +calculate_savi(red, nir, L) Array
}

class Classification {
    +kmeans_clustering(image, n_clusters) ClassifiedImage
    +random_forest(image, training_data) ClassifiedImage
}

class ZonalStatistics {
    +calculate_stats(raster, polygons) StatsResult
    +mean(zone) float
    +median(zone) float
}
```

### 3. Additional Data Models

```mermaid
%% +25 lines approximately
class ProcessedLayer {
    +str id
    +str name
    +str index_type
    +Array data
    +Dict metadata
}

class Job {
    +str job_id
    +str status
    +str operation_type
    +Dict parameters
    +datetime created_at
}

class MosaicResult {
    +str mosaic_id
    +List~str~ scene_ids
    +str status
}
```

### 4. Missing Methods in Existing Classes

```mermaid
%% Current classes need these additions:

class ProjectManager {
    %% +2 lines
    +create_mosaic(scene_ids, options) Layer  %% NEW
    +get_project_status() ProjectStatus  %% NEW
}

class LayerManager {
    %% Already has the missing methods in UML
    %% (add_layer, remove_layer need to be added to UML)
    +add_layer(layer) void  %% +1 line
    +remove_layer(layer_id) void  %% +1 line
}
```

### 5. New Relationships to Add

```mermaid
%% +15 lines approximately
ProjectManager --> ProcessingService : orchestrates
ProjectManager --> MosaicService : uses
AnalysisEngine --> ProcessingService : delegates to
DataImporter --> DirectDownloadService : uses
MapVisualizer --> TileService : uses
ProcessingService --> IndexCalculator : uses
ProcessingService --> Classification : uses
ProcessingService --> ZonalStatistics : uses
ProcessingService --> Job : creates
MosaicService --> Job : creates
DirectDownloadService --> Job : creates
```

## Summary of Changes

### Lines to Add:
| Category | Approximate Lines | Purpose |
|----------|------------------|---------|
| New Service Classes | ~45 | ProcessingService, MosaicService, DirectDownloadService, TileService |
| Processing Support Classes | ~30 | IndexCalculator, Classification, ZonalStatistics |
| Additional Data Models | ~25 | ProcessedLayer, Job, MosaicResult, etc. |
| Missing Methods | ~4 | Additional methods in existing classes |
| New Relationships | ~15 | Service orchestration connections |
| **TOTAL NEW LINES** | **~119 lines** | |

### Lines to Modify:
| Category | Lines | Change Type |
|----------|-------|------------|
| Layer class | 0 | Properties match implementation |
| MetricsReport class | 0 | Properties match implementation |
| LayerManager | 2 | Add missing add_layer, remove_layer |
| **TOTAL MODIFIED** | **~2 lines** | |

## Final UML Statistics After Alignment

### Before:
- **Total Lines**: 201
- **Classes**: 19
- **Methods**: ~45
- **Relationships**: 18

### After Full Alignment:
- **Total Lines**: ~320 (201 + 119)
- **Classes**: 26 (19 + 7 new)
- **Methods**: ~75 (45 + 30 new)
- **Relationships**: 33 (18 + 15 new)

## Visual Comparison

### Current UML Structure:
```
Core (Settings, Auth, Search) → Facade (ProjectManager, etc.) → Models
```

### Aligned UML Structure:
```
Core → Enhanced Facade → Processing Pipeline → Models
  ↓         ↓                    ↓                 ↓
Settings  ProjectManager    ProcessingService   Layer
Auth      LayerManager      MosaicService      Job
Search    AnalysisEngine    TileService        ProcessedLayer
STAC      DataImporter      IndexCalculator    MosaicResult
```

## Key Insights

1. **60% Growth**: The UML would grow by approximately 60% (from 201 to ~320 lines)

2. **Service Layer Expansion**: Most additions are in the service layer, reflecting the actual sophisticated processing capabilities

3. **Backward Compatible**: All original UML elements remain unchanged, we only ADD new elements

4. **Better Representation**: The aligned UML would accurately represent the system's true capabilities

5. **Main Gaps**:
   - Processing pipeline (completely missing in original)
   - Job/async operations (not represented)
   - Tile serving capabilities (not shown)
   - Advanced analysis features (hidden behind stubs)

## Recommendation

Rather than modifying the original `uml.mermaid`, create a new `uml_complete.mermaid` that:
1. Preserves all original elements
2. Adds the ~119 new lines for existing services
3. Shows the complete architecture
4. Maintains clear separation between facade and implementation layers

This approach keeps the original design intent visible while documenting the actual system capabilities.
