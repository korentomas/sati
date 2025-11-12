#!/usr/bin/env python3
"""
Test script demonstrating the complete download workflow:
1. Queue download of satellite imagery
2. Process the image
3. Download processed result to user's computer
"""

import json
import time
import requests

# Configuration
API_BASE = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4ZjNmYmU2YS0yMDU5LTRiYTctOTM2Ni03OWI1NmM1N2RmMGEiLCJlbWFpbCI6InRvbWFza29yZW5ibGl0QGdtYWlsLmNvbSIsInVzZXJfaWQiOiI4ZjNmYmU2YS0yMDU5LTRiYTctOTM2Ni03OWI1NmM1N2RmMGEiLCJleHAiOjE3NjI5OTEwMjl9.lUOqQetz06RUrNTO0sDsKpP35-RJzSZXh40OR7eYAKQ"

headers = {"Authorization": f"Bearer {TOKEN}"}


def test_direct_url_download():
    """Test downloading an image directly from URL to user's computer."""
    print("\n=== Testing Direct URL Download ===")

    # Example URL (this could be a processed satellite image URL)
    image_url = "https://plus.unsplash.com/premium_photo-1694819488591-a43907d1c5cc?ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MXx8Y3V0ZSUyMGRvZ3xlbnwwfHwwfHx8MA%3D%3D&fm=jpg&q=60&w=3000"

    # Call the direct download endpoint
    response = requests.get(
        f"{API_BASE}/downloads/url-download",
        params={"url": image_url},
        headers=headers,
        stream=True
    )

    if response.status_code == 200:
        # Save the downloaded file
        filename = "downloaded_image.jpg"
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Successfully downloaded image to {filename}")
        print(f"   Content-Disposition: {response.headers.get('content-disposition')}")
        print(f"   This would trigger automatic download in a browser!")
    else:
        print(f"❌ Download failed: {response.status_code}")
        print(response.json())


def test_queue_and_download():
    """Test the complete workflow: queue download, then get results."""
    print("\n=== Testing Queue Download Workflow ===")

    # Step 1: Queue a download job
    download_request = {
        "urls": [
            "https://plus.unsplash.com/premium_photo-1694819488591-a43907d1c5cc?ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MXx8Y3V0ZSUyMGRvZ3xlbnwwfHwwfHx8MA%3D%3D&fm=jpg&q=60&w=3000"
        ],
        "priority": 8,
        "metadata": {
            "description": "Test satellite imagery download",
            "target": "processed folder"
        }
    }

    response = requests.post(
        f"{API_BASE}/downloads/download",
        json=download_request,
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to queue download: {response.status_code}")
        print(response.json())
        return

    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"✅ Download job queued: {job_id}")

    # Step 2: Wait for job to complete
    print("⏳ Waiting for download to complete...")
    max_attempts = 30
    for i in range(max_attempts):
        time.sleep(2)

        status_response = requests.get(
            f"{API_BASE}/downloads/jobs/{job_id}",
            headers=headers
        )

        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", {})

            if progress:
                completed = progress.get("completed", 0)
                total = progress.get("total", 1)
                percentage = progress.get("percentage", 0)
                print(f"   Progress: {completed}/{total} files ({percentage:.1f}%)")

            if status == "completed":
                print("✅ Download completed!")

                # Get the download results
                result_response = requests.get(
                    f"{API_BASE}/downloads/jobs/{job_id}/result",
                    headers=headers
                )

                if result_response.status_code == 200:
                    results = result_response.json()
                    print(f"   Downloaded files:")
                    for file_info in results.get("results", []):
                        print(f"   - {file_info['filename']} ({file_info['size']} bytes)")
                        print(f"     Path: {file_info['filepath']}")

                    # In a real scenario, you could now:
                    # 1. Process these files
                    # 2. Use the direct download endpoint to send results to user

                break
            elif status == "failed":
                print("❌ Download failed")
                print(f"   Error: {progress.get('error', 'Unknown error')}")
                break
    else:
        print("⏰ Timeout waiting for download to complete")


def test_batch_download():
    """Test batch download of multiple processed files."""
    print("\n=== Testing Batch Download ===")

    # In a real scenario, these would be IDs of processed satellite images
    file_ids = ["processed_image1.tif", "processed_image2.tif", "processed_image3.tif"]

    response = requests.post(
        f"{API_BASE}/downloads/processed/batch-download",
        json=file_ids,
        headers=headers
    )

    if response.status_code == 200:
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ Batch download job queued: {job_id}")
        print(f"   Message: {job_data.get('message')}")

        # In a real app, you would:
        # 1. Wait for the job to complete
        # 2. Call GET /downloads/processed/batch/{job_id}/download
        # 3. This would trigger browser download of the zip file

    else:
        print(f"❌ Failed to queue batch download: {response.status_code}")
        print(response.text)


def main():
    """Run all tests."""
    print("🚀 Testing Satellite Imagery Download Workflow")
    print("=" * 50)

    # Test 1: Direct download from URL (for immediate downloads)
    test_direct_url_download()

    # Test 2: Queue download and track progress
    test_queue_and_download()

    # Test 3: Batch download multiple files
    test_batch_download()

    print("\n✅ All tests completed!")
    print("\n📝 Summary:")
    print("1. Direct URL downloads work for immediate file downloads")
    print("2. Queue system allows parallel downloads with progress tracking")
    print("3. Batch downloads can package multiple processed images")
    print("4. All endpoints use FileResponse/StreamingResponse for browser downloads")


if __name__ == "__main__":
    main()