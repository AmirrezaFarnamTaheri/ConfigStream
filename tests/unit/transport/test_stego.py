"""Comprehensive tests for steganography transport module."""

from unittest.mock import patch
from cryptography.fernet import Fernet
import zlib

from configstream.transport.stego import (
    StegoPacker,
    generate_stego_assets,
    MAGIC_MARKER,
)


class TestStegoPacker:
    """Test cases for StegoPacker class."""

    def test_init_with_key(self):
        """Test initialization with provided key."""
        key = Fernet.generate_key()
        packer = StegoPacker(key=key)
        assert packer.key == key
        assert packer.cipher is not None

    def test_init_without_key(self):
        """Test initialization without key generates a new one."""
        packer = StegoPacker()
        assert packer.key is not None
        assert len(packer.key) > 0
        assert packer.cipher is not None

    def test_get_key_str(self):
        """Test getting key as string."""
        key = Fernet.generate_key()
        packer = StegoPacker(key=key)
        key_str = packer.get_key_str()
        assert isinstance(key_str, str)
        assert key_str == key.decode("utf-8")

    def test_pack_success(self, tmp_path):
        """Test successful packing of data into cover image."""
        # Create test files
        cover_image = tmp_path / "cover.png"
        output_image = tmp_path / "output.png"

        # Create a fake cover image
        cover_data = b"PNG_HEADER_DATA" + b"\x00" * 100
        cover_image.write_bytes(cover_data)

        # Create packer and pack data
        packer = StegoPacker()
        payload = "test configuration data"
        result = packer.pack(cover_image, payload, output_image)

        assert result is True
        assert output_image.exists()

        # Verify the output contains the cover image and marker
        output_data = output_image.read_bytes()
        assert output_data.startswith(cover_data)
        assert MAGIC_MARKER in output_data

    def test_pack_cover_image_not_found(self, tmp_path):
        """Test pack fails when cover image doesn't exist."""
        cover_image = tmp_path / "nonexistent.png"
        output_image = tmp_path / "output.png"

        packer = StegoPacker()
        result = packer.pack(cover_image, "test data", output_image)

        assert result is False
        assert not output_image.exists()

    def test_pack_with_encryption_and_compression(self, tmp_path):
        """Test that pack encrypts and compresses the payload."""
        cover_image = tmp_path / "cover.png"
        output_image = tmp_path / "output.png"

        cover_data = b"PNG_DATA"
        cover_image.write_bytes(cover_data)

        packer = StegoPacker()
        payload = "test configuration data" * 10  # Larger payload for compression
        result = packer.pack(cover_image, payload, output_image)

        assert result is True

        # Read output and extract encrypted payload
        output_data = output_image.read_bytes()
        marker_pos = output_data.find(MAGIC_MARKER)
        assert marker_pos != -1

        encrypted_payload = output_data[marker_pos + len(MAGIC_MARKER) :]

        # Decrypt and decompress
        decrypted = packer.cipher.decrypt(encrypted_payload)
        decompressed = zlib.decompress(decrypted).decode("utf-8")

        assert decompressed == payload

    def test_pack_with_write_error(self, tmp_path):
        """Test pack handles write errors gracefully."""
        cover_image = tmp_path / "cover.png"
        output_image = tmp_path / "output.png"

        cover_image.write_bytes(b"PNG_DATA")

        packer = StegoPacker()

        # Make output directory read-only to cause write error
        with patch("builtins.open", side_effect=OSError("Write error")):
            result = packer.pack(cover_image, "test data", output_image)
            assert result is False

    def test_pack_with_invalid_payload(self, tmp_path):
        """Test pack handles invalid payload gracefully."""
        cover_image = tmp_path / "cover.png"
        output_image = tmp_path / "output.png"

        cover_image.write_bytes(b"PNG_DATA")

        packer = StegoPacker()

        # Test with non-serializable payload
        with patch("zlib.compress", side_effect=Exception("Compression error")):
            result = packer.pack(cover_image, "test", output_image)
            assert result is False

    def test_pack_creates_larger_file(self, tmp_path):
        """Test that packed file is larger than cover image."""
        cover_image = tmp_path / "cover.png"
        output_image = tmp_path / "output.png"

        cover_data = b"PNG_DATA" * 10
        cover_image.write_bytes(cover_data)

        packer = StegoPacker()
        payload = "configuration data"
        packer.pack(cover_image, payload, output_image)

        assert output_image.stat().st_size > cover_image.stat().st_size

    def test_pack_with_empty_payload(self, tmp_path):
        """Test pack with empty payload."""
        cover_image = tmp_path / "cover.png"
        output_image = tmp_path / "output.png"

        cover_image.write_bytes(b"PNG_DATA")

        packer = StegoPacker()
        result = packer.pack(cover_image, "", output_image)

        assert result is True
        assert output_image.exists()

    def test_pack_with_unicode_payload(self, tmp_path):
        """Test pack with unicode payload."""
        cover_image = tmp_path / "cover.png"
        output_image = tmp_path / "output.png"

        cover_image.write_bytes(b"PNG_DATA")

        packer = StegoPacker()
        payload = "测试数据 🚀 émojis"
        result = packer.pack(cover_image, payload, output_image)

        assert result is True

        # Verify we can decrypt it back
        output_data = output_image.read_bytes()
        marker_pos = output_data.find(MAGIC_MARKER)
        encrypted = output_data[marker_pos + len(MAGIC_MARKER) :]
        decrypted = packer.cipher.decrypt(encrypted)
        decompressed = zlib.decompress(decrypted).decode("utf-8")
        assert decompressed == payload


class TestGenerateStegoAssets:
    """Test cases for generate_stego_assets function."""

    def test_generate_with_existing_config(self, tmp_path):
        """Test generating stego assets with existing config file."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        # Create config file
        config_file = config_dir / "singbox.json"
        config_content = '{"outbounds": []}'
        config_file.write_text(config_content)

        # Create cover images
        cover1 = assets_dir / "cover1.png"
        cover2 = assets_dir / "cover2.png"
        cover1.write_bytes(b"PNG_DATA_1")
        cover2.write_bytes(b"PNG_DATA_2")

        # Generate stego assets
        generate_stego_assets(config_dir, assets_dir)

        # Check that stego images were created
        assert (config_dir / "stealth_cover1.png").exists()
        assert (config_dir / "stealth_cover2.png").exists()

    def test_generate_with_secret_key(self, tmp_path):
        """Test generating stego assets with a provided secret key."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        config_file = config_dir / "singbox.json"
        config_file.write_text('{"test": "data"}')

        cover = assets_dir / "cover.png"
        cover.write_bytes(b"PNG_DATA")

        secret_key = Fernet.generate_key().decode()
        generate_stego_assets(config_dir, assets_dir, secret_key)

        assert (config_dir / "stealth_cover.png").exists()

    def test_generate_without_config_file(self, tmp_path, caplog):
        """Test generate handles missing config file gracefully."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        # No config file created
        generate_stego_assets(config_dir, assets_dir)

        # Should log warning and not create any files
        assert any("not found" in record.message.lower() for record in caplog.records)

    def test_generate_without_cover_images(self, tmp_path, caplog):
        """Test generate handles missing cover images gracefully."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        config_file = config_dir / "singbox.json"
        config_file.write_text('{"test": "data"}')

        # No cover images
        generate_stego_assets(config_dir, assets_dir)

        # Should log warning
        assert any(
            "no cover images" in record.message.lower() for record in caplog.records
        )

    def test_generate_with_multiple_covers(self, tmp_path):
        """Test generating stego assets with multiple cover images."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        config_file = config_dir / "singbox.json"
        config_file.write_text('{"test": "data"}')

        # Create multiple cover images
        for i in range(5):
            cover = assets_dir / f"cover{i}.png"
            cover.write_bytes(f"PNG_DATA_{i}".encode())

        generate_stego_assets(config_dir, assets_dir)

        # All covers should have stego versions
        for i in range(5):
            assert (config_dir / f"stealth_cover{i}.png").exists()

    def test_generate_preserves_cover_names(self, tmp_path):
        """Test that generated files preserve cover image names."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        config_file = config_dir / "singbox.json"
        config_file.write_text('{"test": "data"}')

        cover = assets_dir / "my_special_cover.png"
        cover.write_bytes(b"PNG_DATA")

        generate_stego_assets(config_dir, assets_dir)

        assert (config_dir / "stealth_my_special_cover.png").exists()

    def test_generate_with_nonascii_config(self, tmp_path):
        """Test generate with non-ASCII config content."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        config_file = config_dir / "singbox.json"
        config_file.write_text('{"name": "测试"}', encoding="utf-8")

        cover = assets_dir / "cover.png"
        cover.write_bytes(b"PNG_DATA")

        generate_stego_assets(config_dir, assets_dir)

        assert (config_dir / "stealth_cover.png").exists()

    def test_generate_without_secret_key(self, tmp_path):
        """Test that generate creates new key when not provided."""
        config_dir = tmp_path / "configs"
        assets_dir = tmp_path / "assets"
        config_dir.mkdir()
        assets_dir.mkdir()

        config_file = config_dir / "singbox.json"
        config_file.write_text('{"test": "data"}')

        cover = assets_dir / "cover.png"
        cover.write_bytes(b"PNG_DATA")

        # Should not raise error even without secret key
        generate_stego_assets(config_dir, assets_dir, secret_key=None)

        assert (config_dir / "stealth_cover.png").exists()


class TestMagicMarker:
    """Test cases for magic marker constant."""

    def test_magic_marker_constant(self):
        """Test that magic marker is defined correctly."""
        assert MAGIC_MARKER == b"CSTREAM_PAYLOAD_START>>"
        assert isinstance(MAGIC_MARKER, bytes)
        assert len(MAGIC_MARKER) > 0
