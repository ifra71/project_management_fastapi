from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

UPLOAD_DIR = Path("uploads/documents")
MAX_FILE_SIZE = 10 * 1024 * 1024


async def save_document_file(file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower()
    stored_name = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_name

    size = 0

    try:
        with file_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File size cannot exceed 10 MB",
                    )

                destination.write(chunk)

    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    return {
        "original_name": original_name,
        "stored_name": stored_name,
        "file_path": str(file_path),
        "size": size,
    }
