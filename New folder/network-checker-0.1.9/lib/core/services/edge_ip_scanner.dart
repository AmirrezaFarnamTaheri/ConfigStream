import 'dart:async';
import 'dart:io';

/// Result of an Edge IP scan
class EdgeIpResult {
  final String ip;
  final int port;
  final bool success;
  final double? latencyMs;
  final double? speedKbps;
  final int? downloadedBytes;
  final String? errorMessage;
  final DateTime timestamp;

  EdgeIpResult({
    required this.ip,
    required this.port,
    required this.success,
    this.latencyMs,
    this.speedKbps,
    this.downloadedBytes,
    this.errorMessage,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toMap() => {
        'ip': ip,
        'port': port,
        'success': success,
        'latencyMs': latencyMs,
        'speedKbps': speedKbps,
        'downloadedBytes': downloadedBytes,
        'errorMessage': errorMessage,
        'timestamp': timestamp.toIso8601String(),
      };
}

/// Configuration for the Edge IP Scanner
class EdgeScanConfig {
  final String testDomain;
  final String testPath;
  final int port;
  final Duration timeout;
  final int maxWorkers;
  final bool testDownload;
  final int downloadSize;

  const EdgeScanConfig({
    this.testDomain = 'chatgpt.com',
    this.testPath = '/',
    this.port = 443,
    this.timeout = const Duration(seconds: 3),
    this.maxWorkers = 20,
    this.testDownload = true,
    this.downloadSize = 100 * 1024, // 100KB
  });

  EdgeScanConfig copyWith({
    String? testDomain,
    String? testPath,
    int? port,
    Duration? timeout,
    int? maxWorkers,
    bool? testDownload,
    int? downloadSize,
  }) {
    return EdgeScanConfig(
      testDomain: testDomain ?? this.testDomain,
      testPath: testPath ?? this.testPath,
      port: port ?? this.port,
      timeout: timeout ?? this.timeout,
      maxWorkers: maxWorkers ?? this.maxWorkers,
      testDownload: testDownload ?? this.testDownload,
      downloadSize: downloadSize ?? this.downloadSize,
    );
  }
}

/// Scanner for testing Cloudflare/CDN Edge IPs
class EdgeIpScanner {
  final EdgeScanConfig config;

  EdgeIpScanner({EdgeScanConfig? config}) : config = config ?? const EdgeScanConfig();

  /// Test a single IP via HTTPS with TLS SNI
  Future<EdgeIpResult?> testIpHttp(String ip) async {
    final stopwatch = Stopwatch()..start();

    try {
      // Create socket and connect
      final socket = await Socket.connect(
        ip,
        config.port,
        timeout: config.timeout,
      );

      try {
        // Wrap with SSL and specify SNI hostname
        final secureSocket = await SecureSocket.secure(
          socket,
          host: config.testDomain,
          onBadCertificate: (_) => true, // Accept all certificates
        );

        try {
          // Send HTTP GET request
          final request = 'GET ${config.testPath} HTTP/1.1\r\n'
              'Host: ${config.testDomain}\r\n'
              'Connection: close\r\n'
              '\r\n';
          secureSocket.write(request);
          await secureSocket.flush();

          // Receive response
          final response = <int>[];
          int downloaded = 0;

          await for (final chunk in secureSocket.timeout(config.timeout)) {
            response.addAll(chunk);
            downloaded += chunk.length;

            // Stop after downloading test size
            if (config.testDownload && downloaded >= config.downloadSize) {
              break;
            }
          }

          stopwatch.stop();
          final latency = stopwatch.elapsedMilliseconds.toDouble();

          // Check if response is valid HTTP
          final responseStr = String.fromCharCodes(response.take(20));
          if (responseStr.contains('HTTP/')) {
            // Calculate download speed
            final downloadTime = stopwatch.elapsedMilliseconds / 1000.0;
            final speedKbps = downloadTime > 0 ? (downloaded / 1024) / downloadTime : 0.0;

            return EdgeIpResult(
              ip: ip,
              port: config.port,
              success: true,
              latencyMs: latency,
              speedKbps: speedKbps,
              downloadedBytes: downloaded,
            );
          }
          return null;
        } finally {
          await secureSocket.close();
        }
      } catch (_) {
        await socket.close();
        rethrow;
      }
    } on SocketException catch (e) {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: e.message,
      );
    } on HandshakeException catch (e) {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: 'TLS handshake failed: ${e.message}',
      );
    } on TimeoutException {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: 'Connection timed out',
      );
    } catch (e) {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// Fast TCP connection test with TLS handshake only (no HTTP)
  Future<EdgeIpResult?> testIpFast(String ip) async {
    final stopwatch = Stopwatch()..start();

    try {
      // Create socket and connect
      final socket = await Socket.connect(
        ip,
        config.port,
        timeout: config.timeout,
      );

      try {
        // TLS handshake with SNI
        final secureSocket = await SecureSocket.secure(
          socket,
          host: config.testDomain,
          onBadCertificate: (_) => true,
        );

        stopwatch.stop();
        final latency = stopwatch.elapsedMilliseconds.toDouble();

        await secureSocket.close();

        return EdgeIpResult(
          ip: ip,
          port: config.port,
          success: true,
          latencyMs: latency,
        );
      } catch (_) {
        await socket.close();
        rethrow;
      }
    } on SocketException catch (e) {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: e.message,
      );
    } on HandshakeException catch (e) {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: 'TLS handshake failed: ${e.message}',
      );
    } on TimeoutException {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: 'Connection timed out',
      );
    } catch (e) {
      return EdgeIpResult(
        ip: ip,
        port: config.port,
        success: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// Test a single IP
  Future<EdgeIpResult?> testIp(String ip) {
    if (config.testDownload) {
      return testIpHttp(ip);
    } else {
      return testIpFast(ip);
    }
  }

  /// Parse IP ranges and individual IPs from input text
  /// Supports: CIDR notation (e.g., 104.18.0.0/20) and individual IPs
  static List<String> parseIpInput(String input) {
    final ips = <String>[];
    final lines = input.split('\n');

    for (var line in lines) {
      line = line.trim();
      if (line.isEmpty || line.startsWith('#')) continue;

      if (line.contains('/')) {
        // CIDR notation - parse subnet
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
      final ip = '${(addr >> 24) & 0xFF}.${(addr >> 16) & 0xFF}.${(addr >> 8) & 0xFF}.${addr & 0xFF}';
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

  /// Scan multiple IPs concurrently
  /// Returns a stream of results as they complete
  Stream<EdgeIpScanProgress> scanIps(List<String> ips) {
    // Use a StreamController to emit results as they complete
    final controller = StreamController<EdgeIpScanProgress>();
    
    _runScan(ips, controller);
    
    return controller.stream;
  }

  Future<void> _runScan(List<String> ips, StreamController<EdgeIpScanProgress> controller) async {
    if (ips.isEmpty) {
      await controller.close();
      return;
    }

    int completed = 0;
    int successful = 0;
    final total = ips.length;
    final results = <EdgeIpResult>[];

    // Create batches for controlled concurrency
    final batches = <List<String>>[];
    for (var i = 0; i < ips.length; i += config.maxWorkers) {
      batches.add(
        ips.sublist(
          i,
          i + config.maxWorkers > ips.length ? ips.length : i + config.maxWorkers,
        ),
      );
    }

    try {
      for (final batch in batches) {
        if (controller.isClosed) break;
        
        // Run batch in parallel using Future.wait
        final futures = batch.map((ip) => testIp(ip));
        final batchResults = await Future.wait(futures);

        for (final result in batchResults) {
          if (controller.isClosed) break;
          
          completed++;
          if (result != null && result.success) {
            successful++;
            results.add(result);
          }

          controller.add(EdgeIpScanProgress(
            result: result,
            completed: completed,
            total: total,
            successful: successful,
            workingIps: List.unmodifiable(results),
          ));
        }
      }
    } catch (e) {
      controller.addError(e);
    } finally {
      await controller.close();
    }
  }
}

/// Progress information for IP scans
class EdgeIpScanProgress {
  final EdgeIpResult? result;
  final int completed;
  final int total;
  final int successful;
  final List<EdgeIpResult> workingIps;

  EdgeIpScanProgress({
    this.result,
    required this.completed,
    required this.total,
    required this.successful,
    required this.workingIps,
  });

  double get progress => total > 0 ? completed / total : 0;
  int get remaining => total - completed;
  bool get isComplete => completed >= total;
  int get failed => completed - successful;
}

