import os
import json
import asyncio
import tempfile

_STATE_LOCK = asyncio.Lock()

async def safe_save_state(file_path: str, data: dict) -> bool:
    async with _STATE_LOCK:
        dir_name = os.path.dirname(file_path)
        os.makedirs(dir_name, exist_ok=True)
        
        # Write to temporary file first
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(data, tf, indent=2, ensure_ascii=False)
                temp_name = tf.name
            
            # Atomic replace
            os.replace(temp_name, file_path)
            return True
        except Exception as e:
            if 'temp_name' in locals() and os.path.exists(temp_name):
                os.remove(temp_name)
            raise e

async def safe_load_state(file_path: str, default_data: dict = None) -> dict:
    async with _STATE_LOCK:
        if not os.path.exists(file_path):
            return default_data if default_data is not None else {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default_data if default_data is not None else {}
