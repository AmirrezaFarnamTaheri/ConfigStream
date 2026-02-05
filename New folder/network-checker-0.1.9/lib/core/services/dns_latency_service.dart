import 'dart:async';
import 'dart:io';
import 'dart:isolate';

/// Result of a DNS latency check
class DnsLatencyResult {
  final String address;
  final String providerName;
  final bool success;
  final int? latencyMs;
  final String? errorMessage;
  final DateTime checkedAt;

  DnsLatencyResult({
    required this.address,
    required this.providerName,
    required this.success,
    this.latencyMs,
    this.errorMessage,
    DateTime? checkedAt,
  }) : checkedAt = checkedAt ?? DateTime.now();
}

/// Service for checking DNS server latency using UDP DNS queries
class DnsLatencyService {
  /// Default timeout for DNS queries (2 second - reasonable for latency testing)
  static const Duration defaultTimeout = Duration(seconds: 2);

  /// Default number of concurrent checks
  static const int defaultConcurrency = 10;

  /// DNS query for google.com A record (standard query)
  /// Transaction ID: 0xABCD
  /// Flags: 0x0100 (standard query, recursion desired)
  /// Questions: 1, Answers: 0, Authority: 0, Additional: 0
  /// Query: google.com, Type: A (1), Class: IN (1)
  static final List<int> _dnsQuery = [
    0xAB, 0xCD, // Transaction ID
    0x01, 0x00, // Flags: standard query, recursion desired
    0x00, 0x01, // Questions: 1
    0x00, 0x00, // Answer RRs: 0
    0x00, 0x00, // Authority RRs: 0
    0x00, 0x00, // Additional RRs: 0
    // Query: google.com
    0x06, 0x67, 0x6f, 0x6f, 0x67, 0x6c, 0x65, // "google"
    0x03, 0x63, 0x6f, 0x6d, // "com"
    0x00, // End of name
    0x00, 0x01, // Type: A
    0x00, 0x01, // Class: IN
  ];

  /// Check latency to a single DNS server
  static Future<DnsLatencyResult> checkSingle(
    String address,
    String providerName, {
    Duration timeout = defaultTimeout,
  }) async {
    final stopwatch = Stopwatch()..start();

    try {
      // Parse the IP address
      final ip = InternetAddress.tryParse(address);
      if (ip == null) {
        return DnsLatencyResult(
          address: address,
          providerName: providerName,
          success: false,
          errorMessage: 'Invalid IP address',
        );
      }

      // Create UDP socket
      final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);

      try {
        // Send DNS query
        socket.send(_dnsQuery, ip, 53);

        // Wait for response with timeout
        final completer = Completer<bool>();
        Timer? timeoutTimer;

        timeoutTimer = Timer(timeout, () {
          if (!completer.isCompleted) {
            completer.complete(false);
          }
        });

        socket.listen((event) {
          if (event == RawSocketEvent.read && !completer.isCompleted) {
            final datagram = socket.receive();
            if (datagram != null && datagram.data.length > 2) {
              // Check if response has matching transaction ID
              if (datagram.data[0] == 0xAB && datagram.data[1] == 0xCD) {
                completer.complete(true);
              }
            }
          }
        });

        final success = await completer.future;
        stopwatch.stop();
        timeoutTimer.cancel();

        if (success) {
          return DnsLatencyResult(
            address: address,
            providerName: providerName,
            success: true,
            latencyMs: stopwatch.elapsedMilliseconds,
          );
        } else {
          return DnsLatencyResult(
            address: address,
            providerName: providerName,
            success: false,
            latencyMs: stopwatch.elapsedMilliseconds,
            errorMessage: 'Timeout after ${timeout.inSeconds}s',
          );
        }
      } finally {
        socket.close();
      }
    } on SocketException catch (e) {
      stopwatch.stop();
      return DnsLatencyResult(
        address: address,
        providerName: providerName,
        success: false,
        latencyMs: stopwatch.elapsedMilliseconds,
        errorMessage: _formatSocketError(e),
      );
    } catch (e) {
      stopwatch.stop();
      return DnsLatencyResult(
        address: address,
        providerName: providerName,
        success: false,
        latencyMs: stopwatch.elapsedMilliseconds,
        errorMessage: e.toString(),
      );
    }
  }

  /// Check latency to multiple DNS servers in parallel
  static Stream<DnsLatencyResult> checkMultiple(
    List<(String address, String providerName)> targets, {
    Duration timeout = defaultTimeout,
    int concurrency = defaultConcurrency,
  }) async* {
    if (targets.isEmpty) return;

    // Create batches for controlled concurrency
    final batches = <List<(String, String)>>[];
    for (var i = 0; i < targets.length; i += concurrency) {
      batches.add(
        targets.sublist(
          i,
          i + concurrency > targets.length ? targets.length : i + concurrency,
        ),
      );
    }

    for (final batch in batches) {
      final futures = batch.map(
        (target) => _checkInIsolate(target.$1, target.$2, timeout),
      );
      final results = await Future.wait(futures);

      for (final result in results) {
        yield result;
      }
    }
  }

  /// Run DNS check in a separate isolate for true parallel execution
  static Future<DnsLatencyResult> _checkInIsolate(
    String address,
    String providerName,
    Duration timeout,
  ) async {
    try {
      return await Isolate.run(() async {
        return await checkSingle(address, providerName, timeout: timeout);
      });
    } catch (e) {
      // Fallback if isolate fails
      return checkSingle(address, providerName, timeout: timeout);
    }
  }

  /// Format socket errors for display
  static String _formatSocketError(SocketException e) {
    final message = e.message;

    if (message.contains('Network is unreachable')) {
      return 'Network unreachable';
    }
    if (message.contains('No route to host')) {
      return 'No route to host';
    }
    if (message.contains('Connection refused')) {
      return 'Connection refused';
    }
    if (message.contains('Permission denied')) {
      return 'Permission denied';
    }

    return message.length > 50 ? '${message.substring(0, 47)}...' : message;
  }
}

