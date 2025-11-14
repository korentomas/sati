"""Tile server routes for serving COG imagery as map tiles."""

import hashlib
import os
from io import BytesIO
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request, Response
from PIL import Image
from rio_tiler.io import Reader

# Configure AWS for unsigned requests (public S3 buckets)
os.environ["AWS_NO_SIGN_REQUEST"] = "YES"

router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get(
    "/{scene_id}/{z}/{x}/{y}.png",
    responses={
        200: {"content": {"image/png": {}}, "description": "Tile image"},
        404: {"description": "Tile not found"},
    },
)
async def get_scene_tile(
    scene_id: str,
    z: int,
    x: int,
    y: int,
    request: Request,
    bands: Optional[str] = Query(
        "B4,B3,B2", description="Band names (e.g., B4,B3,B2 for RGB)"
    ),
    rescale: Optional[str] = Query(None, description="Min,max values for rescaling"),
    collection: Optional[str] = Query("sentinel-2-l2a", description="Collection name"),
    url: Optional[str] = Query(None, description="Optional direct COG URL"),
) -> Response:
    """
    Get a tile from a satellite scene.

    Args:
        scene_id: Scene ID
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        bands: Band names to use
        rescale: Rescaling values
        collection: Collection name for scene lookup
        url: Direct COG URL (overrides scene lookup)

    Returns:
        PNG tile
    """
    # Import here to avoid circular dependency
    from app.api.v1.features.imagery.search.service import SearchService

    try:
        # If URL is provided directly, use it
        if url:
            # This would be for a single COG with multiple bands
            # For now, we'll skip this case and focus on scene-based tiles
            raise HTTPException(
                status_code=400, detail="Direct URL mode not yet implemented"
            )

        # Otherwise, look up the scene to get asset URLs
        service = SearchService()
        scene = await service.get_scene(collection, scene_id)

        if not scene:
            # Fallback to AWS public bucket for Sentinel-2
            if "sentinel" in collection.lower() or "s2" in scene_id.upper():
                # Try the AWS public bucket approach
                return await get_sentinel2_tile_fallback(
                    scene_id, z, x, y, bands, rescale
                )
            else:
                raise HTTPException(
                    status_code=404, detail=f"Scene {scene_id} not found"
                )

        # Parse bands
        if bands:
            band_list = bands.split(",")
        else:
            band_list = ["B4", "B3", "B2"]  # Default to RGB for Sentinel-2

        # Ensure we have exactly 3 bands for RGB
        if len(band_list) != 3:
            raise HTTPException(
                status_code=400, detail="Exactly 3 bands required for RGB composite"
            )

        # Map band names to asset keys in the STAC item
        # Common band asset naming conventions
        band_asset_mapping = {
            # Sentinel-2 style
            "B1": ["B01", "coastal"],
            "B2": ["B02", "blue"],
            "B3": ["B03", "green"],
            "B4": ["B04", "red"],
            "B5": ["B05", "rededge1", "rededge"],
            "B6": ["B06", "rededge2"],
            "B7": ["B07", "rededge3"],
            "B8": ["B08", "nir", "nir08"],
            "B8A": ["B8A", "nir09"],
            "B9": ["B09", "water-vapor"],
            "B10": ["B10", "cirrus"],
            "B11": ["B11", "swir1", "swir16"],
            "B12": ["B12", "swir2", "swir22"],
            # Alternative formats
            "B01": ["B01", "coastal"],
            "B02": ["B02", "blue"],
            "B03": ["B03", "green"],
            "B04": ["B04", "red"],
            "B05": ["B05", "rededge1"],
            "B06": ["B06", "rededge2"],
            "B07": ["B07", "rededge3"],
            "B08": ["B08", "nir", "nir08"],
            "B09": ["B09", "water-vapor"],
        }

        # Read each band and combine
        band_data = []
        has_valid_data = False

        for band in band_list:
            # Find the asset for this band
            asset_url = None
            possible_names = band_asset_mapping.get(band, [band, band.lower()])

            for asset_name in possible_names:
                if asset_name in scene.assets:
                    asset_url = scene.assets[asset_name]["href"]
                    break

            if not asset_url:
                # Try direct band name match
                if band in scene.assets:
                    asset_url = scene.assets[band]["href"]
                elif band.lower() in scene.assets:
                    asset_url = scene.assets[band.lower()]["href"]
                else:
                    available = list(scene.assets.keys())
                    print(
                        f"Band {band} not found in assets. " f"Available: {available}"
                    )
                    # Create placeholder black band
                    band_data.append(np.zeros((256, 256), dtype=np.uint8))
                    continue

            # Read the band from the COG
            try:
                with Reader(asset_url) as cog:
                    try:
                        img = cog.tile(x, y, z)
                        band_data.append(img.data[0])
                        has_valid_data = True
                    except Exception as tile_error:
                        if (
                            "is outside" in str(tile_error)
                            or "out of bounds" in str(tile_error).lower()
                        ):
                            # This tile is outside the scene bounds
                            # Add a transparent band
                            band_data.append(np.zeros((256, 256), dtype=np.uint8))
                        else:
                            raise tile_error
            except Exception as e:
                print(f"Error reading band {band} from {asset_url}: {e}")
                # If all bands fail, return transparent tile
                if len(band_data) == 0:
                    transparent = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                    buf = BytesIO()
                    transparent.save(buf, format="PNG")
                    buf.seek(0)
                    return Response(content=buf.getvalue(), media_type="image/png")
                # Add placeholder
                band_data.append(np.zeros((256, 256), dtype=np.uint8))

        # If no valid data was found (all tiles outside bounds), return transparent
        if not has_valid_data:
            transparent = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            buf = BytesIO()
            transparent.save(buf, format="PNG")
            buf.seek(0)
            return Response(content=buf.getvalue(), media_type="image/png")

        # Stack bands into RGB image
        img_data = np.stack(band_data)

        # Store original values to determine no-data pixels
        original_sum = np.sum(img_data, axis=0)

        # Apply rescaling
        if rescale:
            min_val, max_val = map(float, rescale.split(","))
            if max_val > min_val:
                img_data = np.clip(
                    (img_data - min_val) / (max_val - min_val) * 255, 0, 255
                ).astype(np.uint8)
            else:
                img_data = np.full_like(img_data, 128, dtype=np.uint8)
        else:
            # Auto-scale for Sentinel-2 (typical range 0-10000)
            if "sentinel" in collection.lower():
                img_data = np.clip(img_data / 3000 * 255, 0, 255).astype(np.uint8)
            else:
                # Auto-scale each band
                scaled_data = np.zeros_like(img_data, dtype=np.uint8)
                for i in range(img_data.shape[0]):
                    band_array: np.ndarray = img_data[i]
                    # Skip empty bands
                    if band_array.max() == 0:
                        scaled_data[i] = band_array
                        continue
                    # Use percentile-based scaling
                    band_min = (
                        np.percentile(band_array[band_array > 0], 2)
                        if (band_array > 0).any()
                        else 0
                    )
                    band_max = np.percentile(band_array, 98)

                    if band_max > band_min:
                        scaled_data[i] = np.clip(
                            (band_array - band_min) / (band_max - band_min) * 255,
                            0,
                            255,
                        ).astype(np.uint8)
                    else:
                        scaled_data[i] = np.full_like(band_array, 128, dtype=np.uint8)
                img_data = scaled_data

        # Create alpha channel based on no-data pixels
        # Pixels are transparent where original data was 0 or very low
        alpha_channel = np.where(original_sum <= 10, 0, 255).astype(np.uint8)

        # Stack RGB with alpha to create RGBA
        rgba_data = np.zeros((img_data.shape[1], img_data.shape[2], 4), dtype=np.uint8)
        rgba_data[:, :, :3] = np.transpose(img_data, (1, 2, 0))
        rgba_data[:, :, 3] = alpha_channel

        # Convert to PIL Image with alpha
        pil_img = Image.fromarray(rgba_data, mode="RGBA")

        # Save to bytes
        buf = BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)

        # Generate ETag for caching
        etag_content = f"{scene_id}-{z}-{x}-{y}-{bands}-{rescale or 'auto'}"
        etag = hashlib.md5(etag_content.encode(), usedforsecurity=False).hexdigest()

        # Check if client has cached version
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            return Response(
                status_code=304,  # Not Modified
                headers={
                    "ETag": f'"{etag}"',
                    "Cache-Control": "public, max-age=604800",  # 7 days
                },
            )

        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=604800",  # Cache for 7 days
                "ETag": f'"{etag}"',
                "X-Tile-Source": "scene",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating tile for {scene_id}: {e}")
        # Try fallback for Sentinel-2
        if "sentinel" in collection.lower() or "s2" in scene_id.upper():
            try:
                return await get_sentinel2_tile_fallback(
                    scene_id, z, x, y, bands, rescale
                )
            except Exception:  # nosec B110
                pass
        raise HTTPException(status_code=500, detail=str(e))


async def get_sentinel2_tile_fallback(
    scene_id: str,
    z: int,
    x: int,
    y: int,
    bands: Optional[str] = None,
    rescale: Optional[str] = None,
) -> Response:
    """Fallback method to get Sentinel-2 tiles from AWS public bucket."""
    # Map band names to file names
    band_mapping = {
        "B1": "B01.tif",
        "B2": "B02.tif",
        "B3": "B03.tif",
        "B4": "B04.tif",
        "B5": "B05.tif",
        "B6": "B06.tif",
        "B7": "B07.tif",
        "B8": "B08.tif",
        "B8A": "B8A.tif",
        "B9": "B09.tif",
        "B10": "B10.tif",
        "B11": "B11.tif",
        "B12": "B12.tif",
        "B01": "B01.tif",
        "B02": "B02.tif",
        "B03": "B03.tif",
        "B04": "B04.tif",
        "B05": "B05.tif",
        "B06": "B06.tif",
        "B07": "B07.tif",
        "B08": "B08.tif",
        "B09": "B09.tif",
    }

    if bands:
        band_list = bands.split(",")
    else:
        band_list = ["B4", "B3", "B2"]

    band_data = []

    for band in band_list:
        band_file = band_mapping.get(band, f"{band}.tif")

        # Try different URL patterns
        base_url1 = (
            f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/"
            f"sentinel-s2-l2a-cogs/{scene_id}/{band_file}"
        )
        base_url2 = (
            f"https://sentinel-cogs.s3.amazonaws.com/"
            f"sentinel-s2-l2a-cogs/{scene_id}/{band_file}"
        )
        urls_to_try = [base_url1, base_url2]

        band_read = False
        for cog_url in urls_to_try:
            try:
                with Reader(cog_url) as cog:
                    img = cog.tile(x, y, z)
                    band_data.append(img.data[0])
                    band_read = True
                    break
            except Exception:  # nosec B112
                continue

        if not band_read:
            # Add black placeholder
            band_data.append(np.zeros((256, 256), dtype=np.uint8))

    # Stack and process
    img_data = np.stack(band_data)

    # Store original values for no-data detection
    original_sum = np.sum(img_data, axis=0)

    # Apply rescaling or auto-scale
    if rescale:
        min_val, max_val = map(float, rescale.split(","))
        img_data = np.clip(
            (img_data - min_val) / (max_val - min_val) * 255, 0, 255
        ).astype(np.uint8)
    else:
        # Default Sentinel-2 scaling
        img_data = np.clip(img_data / 3000 * 255, 0, 255).astype(np.uint8)

    # Create alpha channel - transparent where no data
    alpha_channel = np.where(original_sum <= 10, 0, 255).astype(np.uint8)

    # Create RGBA image
    rgba_data = np.zeros((img_data.shape[1], img_data.shape[2], 4), dtype=np.uint8)
    rgba_data[:, :, :3] = np.transpose(img_data, (1, 2, 0))
    rgba_data[:, :, 3] = alpha_channel

    # Convert to PIL Image with alpha
    pil_img = Image.fromarray(rgba_data, mode="RGBA")

    # Save to bytes
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


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
    color_formula: Optional[str] = Query(
        None, description="Color formula (e.g., NDVI)"
    ),
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
        # Convert s3:// URLs to https:// for public access
        if url.startswith("s3://"):
            # Convert s3://bucket/key to https://bucket.s3.amazonaws.com/key
            parts = url[5:].split("/", 1)
            if len(parts) == 2:
                bucket = parts[0]
                key = parts[1]
                # Use the appropriate S3 endpoint
                if "sentinel" in bucket:
                    # Sentinel data is in us-west-2
                    url = f"https://{bucket}.s3.us-west-2.amazonaws.com/{key}"
                else:
                    url = f"https://{bucket}.s3.amazonaws.com/{key}"

        # Parse bands
        if bands:
            band_indices = [int(b) for b in bands.split(",")]
        else:
            band_indices = [1, 2, 3]  # Default to RGB

        # Open the COG/JP2
        with Reader(url) as cog:
            # Check if tile is within bounds
            try:
                # Read the tile
                img = cog.tile(x, y, z, indexes=band_indices)
            except Exception as tile_error:
                # Return transparent tile if outside bounds
                if "is outside" in str(tile_error):
                    # Create a transparent 256x256 PNG
                    transparent = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
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
                # Ensure we don't divide by zero
                if max_val > min_val:
                    data = np.clip(
                        (data - min_val) / (max_val - min_val) * 255, 0, 255
                    ).astype(np.uint8)
                else:
                    data = np.zeros_like(data, dtype=np.uint8)
            else:
                # Auto-scale to 0-255 if not already
                scaled_data = np.zeros_like(data, dtype=np.uint8)
                for i in range(data.shape[0]):
                    band = data[i]
                    # Use percentile-based scaling for better contrast
                    band_min = np.percentile(band, 2)  # 2nd percentile
                    band_max = np.percentile(band, 98)  # 98th percentile

                    if band_max > band_min:
                        scaled_data[i] = np.clip(
                            (band - band_min) / (band_max - band_min) * 255, 0, 255
                        ).astype(np.uint8)
                    else:
                        # If no variation, use middle gray
                        scaled_data[i] = np.full_like(band, 128, dtype=np.uint8)
                data = scaled_data

            # Create alpha channel for no-data transparency
            # Detect no-data as pixels where all bands are 0 or very low
            if data.shape[0] >= 3:
                data_sum = np.sum(data[:3], axis=0)  # Sum first 3 bands
            else:
                data_sum = data[0]  # Use single band for grayscale

            alpha_channel = np.where(data_sum <= 5, 0, 255).astype(np.uint8)

            # Convert to PIL Image with transparency
            if data.shape[0] == 1:
                # Single band - grayscale with alpha
                rgba = np.zeros((data.shape[1], data.shape[2], 2), dtype=np.uint8)
                rgba[:, :, 0] = data[0]
                rgba[:, :, 1] = alpha_channel
                pil_img = Image.fromarray(rgba, mode="LA")
            elif data.shape[0] == 3:
                # RGB with alpha
                rgba = np.zeros((data.shape[1], data.shape[2], 4), dtype=np.uint8)
                rgba[:, :, :3] = np.transpose(data, (1, 2, 0))
                rgba[:, :, 3] = alpha_channel
                pil_img = Image.fromarray(rgba, mode="RGBA")
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
    bands: Optional[str] = Query(
        "B04,B03,B02", description="Band names (e.g., B04,B03,B02 for RGB)"
    ),
    rescale: Optional[str] = Query(
        "0,3000", description="Min,max values for rescaling"
    ),
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
        if bands:
            band_list = bands.split(",")
        else:
            band_list = ["B04", "B03", "B02"]  # Default to RGB

        # For RGB composite, we need to combine multiple bands
        if len(band_list) == 3:
            # Read each band separately and combine
            band_data = []

            for band in band_list:
                if band not in band_mapping:
                    raise HTTPException(status_code=400, detail=f"Invalid band: {band}")

                # Construct COG URL for this band
                # Example: S2A_36QWD_20200701_0_L2A/B04.tif
                cog_url = (
                    f"{SENTINEL2_COG_BASE}/sentinel-s2-l2a-cogs/"
                    f"{scene_id}/{band_mapping[band]}"
                )

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
            pil_img = Image.fromarray(np.transpose(img_data, (1, 2, 0)), mode="RGB")

            # Save to bytes
            buf = BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)

            return Response(content=buf.getvalue(), media_type="image/png")
        else:
            # Handle non-RGB band combinations
            raise HTTPException(
                status_code=400,
                detail="Only 3-band RGB composites are currently supported",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
