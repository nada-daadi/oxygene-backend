import asyncio
import cloudinary
import cloudinary.uploader
from app.core.config import settings

def init_cloudinary():
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )

async def upload_to_cloudinary(
    file_bytes: bytes, 
    public_id: str, 
    resource_type: str = "video",
    overwrite: bool = False,
    transformation: list[dict] | None = None
) -> dict:
    """
    Uploads a file to Cloudinary in a non-blocking way.
    Note: Both audio (.mp3, .m4a, .3gp) and video (.mp4) must use resource_type="video".
    Avatars use resource_type="image".
    """
    loop = asyncio.get_event_loop()
    
    def _upload():
        kwargs = {
            "public_id": public_id,
            "resource_type": resource_type,
            "overwrite": overwrite
        }
        if transformation:
            kwargs["transformation"] = transformation
            
        return cloudinary.uploader.upload(file_bytes, **kwargs)
        
    return await loop.run_in_executor(None, _upload)
