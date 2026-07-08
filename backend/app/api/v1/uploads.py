"""Image upload endpoints."""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.dependencies import CurrentUser
from app.storage import upload_file

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/image")
async def upload_image(
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload an image file.

    Returns the public URL of the uploaded image.
    """
    # Validate file extension
    file_extension = Path(file.filename or "").suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)} MB",
        )

    # Validate it's actually an image
    if not content.startswith(b"\xff\xd8\xff") and not content.startswith(b"\x89PNG") and not content.startswith(b"GIF8"):
        raise HTTPException(status_code=400, detail="Invalid image file")

    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_extension}"

    # Upload to Cloudflare R2 and get its public URL
    content_type = file.content_type or "application/octet-stream"
    public_url = upload_file(filename, content, content_type)

    return JSONResponse(
        content={
            "success": True,
            "url": public_url,
            "filename": filename,
            "size": len(content),
        }
    )
