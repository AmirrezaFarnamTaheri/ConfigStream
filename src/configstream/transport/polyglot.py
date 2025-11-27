# src/configstream/transport/polyglot.py

import logging
import zipfile
import io
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# DEPRECATED / EXPERIMENTAL
# =============================================================================
# This module implements "Polyglot" steganography (PNG + ZIP concatenation).
# As of v2.0.0, the primary transport method is the MARKER-BASED approach
# implemented in `src/configstream/transport/stego.py`.
#
# This module is retained for research/fallback purposes but is NOT used
# in the default ConfigStream pipeline.
# =============================================================================


class PolyglotPacker:
    def pack(
        self,
        cover_image: Path,
        payload_data: str,
        payload_filename: str,
        output_path: Path,
    ):
        try:
            # 1. Create In-Memory ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(payload_filename, payload_data)

            zip_bytes = zip_buffer.getvalue()

            # 2. Read Image
            image_bytes = cover_image.read_bytes()

            # 3. Concatenate
            final_bytes = image_bytes + zip_bytes

            # 4. Write
            output_path.write_bytes(final_bytes)
            logger.info(f"Polyglot image saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Polyglot packing failed: {e}")
            return False
