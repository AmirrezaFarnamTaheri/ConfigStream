import 'dart:async';
import 'dart:io';

import 'xray_binary_service.dart';
import 'xray_process_manager.dart';

// Re-export exceptions for convenience
export 'xray_process_manager.dart' show XrayStartupException, PortInUseException;

/// Result of a CDN IP scan
class CdnScanResult {
  final String ip;
  final bool success;
  final double? latencyMs;
  final String? errorMessage;
  final DateTime timestamp;

  CdnScanResult({
    required this.ip,
    required this.success,
    this.latencyMs,
    this.errorMessage,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  @override
  String toString() {
    if (success) {
      return '$ip: ${latencyMs?.toStringAsFixed(0)}ms';
    } else {
      return '$ip: Failed ($errorMessage)';
    }
  }
}

/// Progress information for CDN scans
class CdnScanProgress {
  final CdnScanResult? result;
  final int completed;
  final int total;
  final int successful;
  final List<CdnScanResult> results;

  CdnScanProgress({
    this.result,
    required this.completed,
    required this.total,
    required this.successful,
    required this.results,
  });

  double get progress => total > 0 ? completed / total : 0;
  int get remaining => total - completed;
  bool get isComplete => completed >= total;
  int get failed => completed - successful;
}

/// Configuration for CDN scanning
class CdnScanConfig {
  final int concurrentInstances;
  final Duration timeout;
  final String testUrl;
  final int basePort;

  const CdnScanConfig({
    this.concurrentInstances = 5,
    this.timeout = const Duration(seconds: 10),
    this.testUrl = 'https://www.gstatic.com/generate_204',
    this.basePort = 10808,
  });

  CdnScanConfig copyWith({
    int? concurrentInstances,
    Duration? timeout,
    String? testUrl,
    int? basePort,
  }) {
    return CdnScanConfig(
      concurrentInstances: concurrentInstances ?? this.concurrentInstances,
      timeout: timeout ?? this.timeout,
      testUrl: testUrl ?? this.testUrl,
      basePort: basePort ?? this.basePort,
    );
  }
}

/// Service for scanning CDN IPs through xray proxy
class CdnConfigScanner {
  final XrayBinaryService _binaryService;
  final CdnScanConfig config;

  XrayProcessManager? _processManager;
  bool _isScanning = false;
  bool _shouldStop = false;
  final List<Process> _activeProcesses = [];

  CdnConfigScanner({
    XrayBinaryService? binaryService,
    this.config = const CdnScanConfig(),
  }) : _binaryService = binaryService ?? XrayBinaryService();

  bool get isScanning => _isScanning;

  /// Parse IP input (supports single IPs and CIDR notation)
  static List<String> parseIpInput(String input) {
    final ips = <String>[];
    final lines = input.split('\n');

    for (var line in lines) {
      line = line.trim();
      if (line.isEmpty || line.startsWith('#')) continue;

      if (line.contains('/')) {
        // CIDR notation
        try {
          ips.addAll(_generateIpsFromSubnet(line));
        } catch (e) {
          // Skip invalid subnet
        }
      } else {
        // Single IP
        if (_isValidIp(line)) {
          ips.add(line);
        }
      }
    }

    return ips;
  }

  /// Generate list of IPs from a subnet in CIDR notation
  static List<String> _generateIpsFromSubnet(String subnet) {
    final parts = subnet.split('/');
    if (parts.length != 2) return [];

    final ipStr = parts[0];
    final prefixLength = int.tryParse(parts[1]);
    if (prefixLength == null || prefixLength < 0 || prefixLength > 32) return [];

    final ipParts = ipStr.split('.');
    if (ipParts.length != 4) return [];

    final octets = ipParts.map((p) => int.tryParse(p)).toList();
    if (octets.any((o) => o == null || o < 0 || o > 255)) return [];

    // Calculate network address
    int ipInt = 0;
    for (var i = 0; i < 4; i++) {
      ipInt = (ipInt << 8) | octets[i]!;
    }

    // Calculate number of hosts
    final hostBits = 32 - prefixLength;
    final numHosts = 1 << hostBits;

    // Network mask
    final netmask = ~((1 << hostBits) - 1) & 0xFFFFFFFF;
    final networkAddr = ipInt & netmask;

    // Generate IPs (excluding network and broadcast addresses for /31 and larger)
    final ips = <String>[];
    final start = prefixLength >= 31 ? 0 : 1;
    final end = prefixLength >= 31 ? numHosts : numHosts - 1;

    for (var i = start; i < end; i++) {
      final addr = networkAddr + i;
      final ip =
          '${(addr >> 24) & 0xFF}.${(addr >> 16) & 0xFF}.${(addr >> 8) & 0xFF}.${addr & 0xFF}';
      ips.add(ip);
    }

    return ips;
  }

  /// Validate an IP address
  static bool _isValidIp(String ip) {
    final parts = ip.split('.');
    if (parts.length != 4) return false;

    for (final part in parts) {
      final num = int.tryParse(part);
      if (num == null || num < 0 || num > 255) return false;
    }

    return true;
  }

  /// Test connection through SOCKS5 proxy using curl command
  /// This feature is only available on desktop (Linux/Windows)
  Future<CdnScanResult> _testWithSocks5Proxy(String ip, int proxyPort) async {
    Process? curlProcess;
    try {
      // Use curl with SOCKS5 proxy - socks5h means DNS resolution on proxy side
      curlProcess = await Process.start(
        'curl',
        [
          '-s', // Silent mode
          '-o',
          Platform.isWindows ? 'NUL' : '/dev/null', // Discard output
          '-w',
          '%{http_code},%{time_total}', // Output status code and time
          '--proxy',
          'socks5h://127.0.0.1:$proxyPort',
          '--connect-timeout',
          config.timeout.inSeconds.toString(),
          '-k', // Allow insecure SSL
          config.testUrl,
        ],
      );

      // Track active process for cleanup
      _activeProcesses.add(curlProcess);

      final result = await curlProcess.exitCode
          .timeout(config.timeout + const Duration(seconds: 2));

      // Read output
      final stdout = await curlProcess.stdout.transform(const SystemEncoding().decoder).join();
      final stderr = await curlProcess.stderr.transform(const SystemEncoding().decoder).join();

      // Remove from active processes
      _activeProcesses.remove(curlProcess);

      if (result == 0) {
        // Parse output: "204,0.123456"
        final output = stdout.trim();
        final parts = output.split(',');

        if (parts.length >= 2) {
          final statusCode = int.tryParse(parts[0]) ?? 0;
          final timeSeconds = double.tryParse(parts[1]) ?? 0;
          final timeMs = timeSeconds * 1000;

          if (statusCode == 204 || (statusCode >= 200 && statusCode < 300)) {
            return CdnScanResult(
              ip: ip,
              success: true,
              latencyMs: timeMs,
            );
          } else {
            return CdnScanResult(
              ip: ip,
              success: false,
              errorMessage: 'HTTP $statusCode',
            );
          }
        }
      }

      // curl failed
      return CdnScanResult(
        ip: ip,
        success: false,
        errorMessage: stderr.isNotEmpty ? stderr.trim() : 'curl exit code $result',
      );
    } on TimeoutException {
      // Kill the process if it's still running
      curlProcess?.kill();
      _activeProcesses.remove(curlProcess);
      return CdnScanResult(
        ip: ip,
        success: false,
        errorMessage: 'Connection timed out',
      );
    } catch (e) {
      _activeProcesses.remove(curlProcess);
      return CdnScanResult(
        ip: ip,
        success: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// Start scanning IPs
  Stream<CdnScanProgress> scanIps(
    List<String> ips,
    Map<String, dynamic> baseConfig,
  ) {
    final controller = StreamController<CdnScanProgress>();
    _runScan(ips, baseConfig, controller);
    return controller.stream;
  }

  Future<void> _runScan(
    List<String> ips,
    Map<String, dynamic> baseConfig,
    StreamController<CdnScanProgress> controller,
  ) async {
    if (ips.isEmpty) {
      await controller.close();
      return;
    }

    _isScanning = true;
    _shouldStop = false;

    int completed = 0;
    int successful = 0;
    final total = ips.length;
    final results = <CdnScanResult>[];

    try {
      // Initialize process manager
      _processManager = XrayProcessManager(
        binaryService: _binaryService,
        basePort: config.basePort,
      );

      // Start xray instances - this will throw if ports are in use or xray fails
      await _processManager!.startInstances(baseConfig, config.concurrentInstances);

      // Create a queue of IPs to test
      final ipQueue = List<String>.from(ips);

      // Process IPs in batches using instances
      final batchSize = config.concurrentInstances;

      for (var i = 0; i < ipQueue.length; i += batchSize) {
        if (_shouldStop || controller.isClosed) break;

        final batchEnd = (i + batchSize).clamp(0, ipQueue.length);
        final batch = ipQueue.sublist(i, batchEnd);

        // Process batch in parallel
        final batchFutures = <Future<CdnScanResult>>[];

        for (var j = 0; j < batch.length; j++) {
          if (_shouldStop || controller.isClosed) break;

          final ip = batch[j];
          final instanceIndex = j % _processManager!.instanceCount;
          final instance = _processManager!.instances[instanceIndex];

          batchFutures.add(_testIpWithInstance(instance, ip, baseConfig));
        }

        // Wait for batch to complete with a timeout to prevent hanging
        List<CdnScanResult> batchResults;
        try {
          batchResults = await Future.wait(batchFutures)
              .timeout(config.timeout * 3); // Give enough time for retries
        } on TimeoutException {
          // If batch times out, create failure results for remaining IPs
          batchResults = batch
              .map((ip) => CdnScanResult(
                    ip: ip,
                    success: false,
                    errorMessage: 'Batch timeout',
                  ))
              .toList();
        }

        for (final result in batchResults) {
          if (_shouldStop || controller.isClosed) break;

          completed++;
          if (result.success) {
            successful++;
            results.add(result);
            // Keep results sorted by latency
            results.sort((a, b) =>
                (a.latencyMs ?? double.infinity).compareTo(b.latencyMs ?? double.infinity));
          }

          controller.add(CdnScanProgress(
            result: result,
            completed: completed,
            total: total,
            successful: successful,
            results: List.unmodifiable(results),
          ));
        }
      }
    } on PortInUseException {
      // Re-throw port in use exception as-is so the UI can show a helpful message
      rethrow;
    } on XrayStartupException {
      // Re-throw xray startup exceptions so the UI can handle them
      rethrow;
    } catch (e) {
      controller.addError(e);
    } finally {
      await _cleanup();
      _isScanning = false;
      if (!controller.isClosed) {
        await controller.close();
      }
    }
  }

  Future<CdnScanResult> _testIpWithInstance(
    XrayInstance instance,
    String ip,
    Map<String, dynamic> baseConfig,
  ) async {
    try {
      // Update the instance to use the new IP
      await _processManager!.updateInstanceAddress(instance, ip, baseConfig);

      // Test through the proxy
      return await _testWithSocks5Proxy(ip, instance.port);
    } on XrayStartupException catch (e) {
      return CdnScanResult(
        ip: ip,
        success: false,
        errorMessage: 'Xray error: ${e.message}',
      );
    } catch (e) {
      return CdnScanResult(
        ip: ip,
        success: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// Clean up all resources
  Future<void> _cleanup() async {
    // Kill any active curl processes
    for (final process in _activeProcesses) {
      try {
        process.kill();
      } catch (_) {}
    }
    _activeProcesses.clear();

    // Stop all xray instances
    if (_processManager != null) {
      await _processManager!.stopAll();
      _processManager = null;
    }
  }

  /// Stop the current scan
  Future<void> stopScan() async {
    _shouldStop = true;
    await _cleanup();
  }

  /// Dispose resources
  Future<void> dispose() async {
    _shouldStop = true;
    await _cleanup();
  }
}
