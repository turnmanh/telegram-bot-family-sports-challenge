async def process_ocr_activity(photo_data: bytes) -> dict:
    """
    Mock function to process OCR from photo data.
    
    Args:
        photo_data: The binary content of the photo.
        
    Returns:
        dict: A dictionary containing the mock activity data.
    """
    # Simulate processing logic
    return {
        "type": "Run",
        "distance": 5000, # Mock distance in meters
        "raw_text": "Mocked OCR Result: 5.0km Run"
    }
