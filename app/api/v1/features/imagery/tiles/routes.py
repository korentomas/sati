"""Tile server routes for serving COG imagery as map tiles."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response
from rio_tiler.io import Reader
import numpy as np
from io import BytesIO
from PIL import Image

router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get(
    "/{z}/{x}/{y}.png",
    responses={
        200: {"content": {"image/png": {}}, "description": "Tile image"},
        404: {"description": "Tile not found"},
    },
)
async def get_tile(
    z: int,
    x: int,
    y: int,
    url: str = Query(..., description="COG URL to serve tiles from"),
    bands: Optional[str] = Query("1,2,3", description="Comma-separated band indices"),
    rescale: Optional[str] = Query(None, description="Min,max values for rescaling"),
    color_formula: Optional[str] = Query(None, description="Color formula (e.g., NDVI)"),
    token: Optional[str] = Query(None, description="Optional auth token"),
) -> Response:
    """
    Get a map tile from a Cloud Optimized GeoTIFF.

    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        url: URL to the COG file
        bands: Band indices to use (default: 1,2,3 for RGB)
        rescale: Min,max values for rescaling
        color_formula: Apply a color formula

    Returns:
        PNG tile image
    """
    try:
        # Parse bands
        band_indices = [int(b) for b in bands.split(",")]

        # Open the COG
        with Reader(url) as cog:
            # Check if tile is within bounds
            try:
                # Read the tile
                img = cog.tile(x, y, z, indexes=band_indices)
            except Exception as tile_error:
                # Return transparent tile if outside bounds
                if "is outside" in str(tile_error):
                    # Create a transparent 256x256 PNG
                    transparent = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
                    buf = BytesIO()
                    transparent.save(buf, format="PNG")
                    buf.seek(0)
                    return Response(content=buf.getvalue(), media_type="image/png")
                raise tile_error

            # Get the image data array
            data = img.data

            # Apply rescaling if provided
            if rescale:
                min_val, max_val = map(float, rescale.split(","))
                data = np.clip(
                    (data - min_val) / (max_val - min_val) * 255, 0, 255
                ).astype(np.uint8)
            else:
                # Auto-scale to 0-255 if not already
                scaled_data = np.zeros_like(data, dtype=np.uint8)
                for i in range(data.shape[0]):
                    band = data[i]
                    if band.max() > 255:
                        # Scale from data range to 0-255
                        band_min = band.min()
                        band_max = band.max()
                        if band_max > band_min:
                            scaled_data[i] = (
                                (band - band_min) / (band_max - band_min) * 255
                            ).astype(np.uint8)
                        else:
                            scaled_data[i] = band.astype(np.uint8)
                    else:
                        scaled_data[i] = band.astype(np.uint8)
                data = scaled_data

            # Convert to PIL Image
            if data.shape[0] == 1:
                # Single band - grayscale
                pil_img = Image.fromarray(data[0], mode="L")
            elif data.shape[0] == 3:
                # RGB
                pil_img = Image.fromarray(
                    np.transpose(data, (1, 2, 0)), mode="RGB"
                )
            else:
                raise ValueError(f"Unsupported number of bands: {data.shape[0]}")

            # Save to bytes
            buf = BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)

            return Response(content=buf.getvalue(), media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_cog_info(url: str = Query(..., description="COG URL")) -> dict:
    """
    Get information about a Cloud Optimized GeoTIFF.

    Args:
        url: URL to the COG file

    Returns:
        COG metadata including bounds, bands, and resolution
    """
    try:
        with Reader(url) as cog:
            info = cog.info()
            stats = cog.statistics()

            return {
                "bounds": cog.bounds,
                "crs": str(cog.crs),
                "bands": info.band_descriptions,
                "width": cog.dataset.width,
                "height": cog.dataset.height,
                "count": cog.dataset.count,
                "dtype": str(cog.dataset.dtypes[0]),
                "statistics": {
                    f"band_{i+1}": {
                        "min": float(stats[i + 1].min),
                        "max": float(stats[i + 1].max),
                        "mean": float(stats[i + 1].mean),
                        "std": float(stats[i + 1].std),
                    }
                    for i in range(cog.dataset.count)
                },
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Public Sentinel-2 COG endpoints (examples)
SENTINEL2_COG_BASE = "https://sentinel-cogs.s3.us-west-2.amazonaws.com"


@router.get("/sentinel2/{scene_id}/{z}/{x}/{y}.png")
async def get_sentinel2_tile(
    scene_id: str,
    z: int,
    x: int,
    y: int,
    bands: Optional[str] = Query("B04,B03,B02", description="Band names (e.g., B04,B03,B02 for RGB)"),
    rescale: Optional[str] = Query("0,3000", description="Min,max values for rescaling"),
) -> Response:
    """
    Get a tile from Sentinel-2 COGs on AWS.

    Args:
        scene_id: Sentinel-2 scene ID
        z, x, y: Tile coordinates
        bands: Band names to use
        rescale: Rescaling values

    Returns:
        PNG tile
    """
    # Map band names to URLs
    band_mapping = {
        "B01": "B01.tif",  # Coastal aerosol
        "B02": "B02.tif",  # Blue
        "B03": "B03.tif",  # Green
        "B04": "B04.tif",  # Red
        "B05": "B05.tif",  # Red edge 1
        "B06": "B06.tif",  # Red edge 2
        "B07": "B07.tif",  # Red edge 3
        "B08": "B08.tif",  # NIR
        "B8A": "B8A.tif",  # NIR narrow
        "B09": "B09.tif",  # Water vapor
        "B10": "B10.tif",  # SWIR - Cirrus
        "B11": "B11.tif",  # SWIR 1
        "B12": "B12.tif",  # SWIR 2
    }

    try:
        band_list = bands.split(",")

        # For RGB composite, we need to combine multiple bands
        if len(band_list) == 3:
            # Read each band separately and combine
            band_data = []

            for band in band_list:
                if band not in band_mapping:
                    raise HTTPException(status_code=400, detail=f"Invalid band: {band}")

                # Construct COG URL for this band
                # Example: https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/36/Q/WD/2020/7/S2A_36QWD_20200701_0_L2A/B04.tif
                cog_url = f"{SENTINEL2_COG_BASE}/sentinel-s2-l2a-cogs/{scene_id}/{band_mapping[band]}"

                with Reader(cog_url) as cog:
                    img = cog.tile(x, y, z)
                    band_data.append(img.data[0])

            # Stack bands
            img_data = np.stack(band_data)

            # Apply rescaling
            if rescale:
                min_val, max_val = map(float, rescale.split(","))
                img_data = np.clip(
                    (img_data - min_val) / (max_val - min_val) * 255, 0, 255
                ).astype(np.uint8)

            # Convert to PIL Image
            pil_img = Image.fromarray(
                np.transpose(img_data, (1, 2, 0)), mode="RGB"
            )

            # Save to bytes
            buf = BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)

            return Response(content=buf.getvalue(), media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))