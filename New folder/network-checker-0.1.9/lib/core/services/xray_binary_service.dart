import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Download progress callback
typedef DownloadProgressCallback = void Function(int received, int total);

/// Service for managing xray binary downloads and versions
class XrayBinaryService {
  static const String _prefXrayVersion = 'xray_version';
  static const String _prefGeoVersion = 'geo_version';
  
  /// Get the xray directory path
  Future<Directory> getXrayDirectory() async {
    final appDir = await getApplicationSupportDirectory();
    final xrayDir = Directory('${appDir.path}/xray');
    if (!await xrayDir.exists()) {
      await xrayDir.create(recursive: true);
    }
    return xrayDir;
  }

  /// Get the xray binary path
  Future<String> getXrayBinaryPath() async {
    final xrayDir = await getXrayDirectory();
    if (Platform.isWindows) {
      return '${xrayDir.path}/xray.exe';
    } else {
      return '${xrayDir.path}/xray';
    }
  }

  /// Check if xray binary exists
  Future<bool> isXrayInstalled() async {
    final binaryPath = await getXrayBinaryPath();
    return File(binaryPath).exists();
  }

  /// Get the currently installed xray version
  Future<String?> getInstalledVersion() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_prefXrayVersion);
  }

  /// Fetch the latest xray release version from GitHub
  Future<String> fetchLatestVersion() async {
    try {
      final response = await http.get(
        Uri.parse('https://api.github.com/repos/XTLS/Xray-core/releases/latest'),
        headers: {'Accept': 'application/vnd.github.v3+json'},
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return data['tag_name'] as String;
      } else {
        throw Exception('Failed to fetch latest release: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error fetching latest xray version: $e');
      rethrow;
    }
  }

  /// Get the platform-specific asset name for xray
  /// Get the asset name for the current platform (desktop only)
  String _getXrayAssetName() {
    if (Platform.isWindows) {
      return 'Xray-windows-64.zip';
    } else if (Platform.isLinux) {
      return 'Xray-linux-64.zip';
    } else {
      throw UnsupportedError('Platform not supported for CDN Scan');
    }
  }

  /// Download xray binary for the specified version
  Future<void> downloadXray(
    String version, {
    DownloadProgressCallback? onProgress,
  }) async {
    final assetName = _getXrayAssetName();
    final downloadUrl = 'https://github.com/XTLS/Xray-core/releases/download/$version/$assetName';
    
    debugPrint('Downloading xray from: $downloadUrl');
    
    final xrayDir = await getXrayDirectory();
    final zipPath = '${xrayDir.path}/$assetName';
    
    // Download the zip file
    await _downloadFile(downloadUrl, zipPath, onProgress: onProgress);
    
    // Extract the zip
    await _extractZip(zipPath, xrayDir.path);
    
    // Delete the zip file
    await File(zipPath).delete();
    
    // Set executable permissions on Unix systems
    if (!Platform.isWindows) {
      final binaryPath = await getXrayBinaryPath();
      await _setExecutablePermission(binaryPath);
    }
    
    // Save the installed version
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefXrayVersion, version);
  }

  /// Download geo data files (geoip.dat and geosite.dat)
  Future<void> downloadGeoData({
    DownloadProgressCallback? onProgress,
  }) async {
    final xrayDir = await getXrayDirectory();
    
    // Download geoip.dat
    const geoipUrl = 'https://github.com/v2fly/geoip/releases/latest/download/geoip.dat';
    await _downloadFile(
      geoipUrl,
      '${xrayDir.path}/geoip.dat',
      onProgress: onProgress,
    );
    
    // Download geosite.dat
    const geositeUrl = 'https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat';
    await _downloadFile(
      geositeUrl,
      '${xrayDir.path}/geosite.dat',
      onProgress: onProgress,
    );
    
    // Save geo version as current date
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefGeoVersion, DateTime.now().toIso8601String());
  }

  /// Check if geo data files exist
  Future<bool> hasGeoData() async {
    final xrayDir = await getXrayDirectory();
    final geoipFile = File('${xrayDir.path}/geoip.dat');
    final geositeFile = File('${xrayDir.path}/geosite.dat');
    return await geoipFile.exists() && await geositeFile.exists();
  }

  /// Download a file with progress reporting
  Future<void> _downloadFile(
    String url,
    String savePath, {
    DownloadProgressCallback? onProgress,
  }) async {
    final client = http.Client();
    try {
      final request = http.Request('GET', Uri.parse(url));
      final response = await client.send(request);
      
      if (response.statusCode != 200) {
        throw Exception('Failed to download: ${response.statusCode}');
      }
      
      final contentLength = response.contentLength ?? 0;
      int received = 0;
      
      final file = File(savePath);
      final sink = file.openWrite();
      
      await for (final chunk in response.stream) {
        sink.add(chunk);
        received += chunk.length;
        onProgress?.call(received, contentLength);
      }
      
      await sink.close();
    } finally {
      client.close();
    }
  }

  /// Extract a zip file
  Future<void> _extractZip(String zipPath, String extractPath) async {
    final bytes = await File(zipPath).readAsBytes();
    final archive = ZipDecoder().decodeBytes(bytes);
    
    for (final file in archive) {
      final filename = file.name;
      if (file.isFile) {
        final data = file.content as List<int>;
        final outFile = File('$extractPath/$filename');
        await outFile.create(recursive: true);
        await outFile.writeAsBytes(data);
      } else {
        await Directory('$extractPath/$filename').create(recursive: true);
      }
    }
  }

  /// Delete xray installation
  Future<void> deleteXray() async {
    final xrayDir = await getXrayDirectory();
    if (await xrayDir.exists()) {
      await xrayDir.delete(recursive: true);
    }
    
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_prefXrayVersion);
    await prefs.remove(_prefGeoVersion);
  }

  /// Set executable permission on a file (Linux/Windows only)
  Future<void> _setExecutablePermission(String filePath) async {
    // This feature is only available on desktop platforms
    if (!Platform.isWindows) {
      await Process.run('chmod', ['+x', filePath]);
    }
  }

  /// Get platform display name for UI (desktop only)
  String getPlatformDisplayName() {
    if (Platform.isWindows) {
      return 'Windows (64-bit)';
    } else if (Platform.isLinux) {
      return 'Linux (64-bit)';
    } else {
      return 'Unknown Platform';
    }
  }
}

