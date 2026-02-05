import 'dart:async';
import 'dart:isolate';
import 'package:http/http.dart' as http;

/// Result of a connectivity check
class ConnectivityResult {
  final String target;
  final bool success;
  final int? responseTimeMs;
  final int? statusCode;
  final String? errorMessage;
  final DateTime checkedAt;

  ConnectivityResult({
    required this.target,
    required this.success,
    this.responseTimeMs,
    this.statusCode,
    this.errorMessage,
    DateTime? checkedAt,
  }) : checkedAt = checkedAt ?? DateTime.now();

  Map<String, dynamic> toMap() => {
        'target': target,
        'success': success,
        'responseTimeMs': responseTimeMs,
        'statusCode': statusCode,
        'errorMessage': errorMessage,
        'checkedAt': checkedAt.toIso8601String(),
      };

  factory ConnectivityResult.fromMap(Map<String, dynamic> map) {
    return ConnectivityResult(
      target: map['target'] as String,
      success: map['success'] as bool,
      responseTimeMs: map['responseTimeMs'] as int?,
      statusCode: map['statusCode'] as int?,
      errorMessage: map['errorMessage'] as String?,
      checkedAt: DateTime.parse(map['checkedAt'] as String),
    );
  }
}

/// Service for checking network connectivity
class ConnectivityService {
  /// Default timeout for HTTP requests (5 seconds)
  static const Duration defaultTimeout = Duration(seconds: 3);

  /// Default number of concurrent requests
  static const int defaultConcurrency = 10;

  /// Checks connectivity to a single domain using HTTP HEAD
  static Future<ConnectivityResult> checkSingle(
    String target, {
    Duration timeout = defaultTimeout,
  }) async {
    final uri = _buildUri(target);
    final stopwatch = Stopwatch()..start();

    try {
      final response = await http.head(uri).timeout(timeout);
      stopwatch.stop();

      return ConnectivityResult(
        target: target,
        success: response.statusCode < 400,
        responseTimeMs: stopwatch.elapsedMilliseconds,
        statusCode: response.statusCode,
      );
    } on TimeoutException {
      stopwatch.stop();
      return ConnectivityResult(
        target: target,
        success: false,
        responseTimeMs: stopwatch.elapsedMilliseconds,
        errorMessage: 'Connection timed out after ${timeout.inSeconds}s',
      );
    } catch (e) {
      stopwatch.stop();
      return ConnectivityResult(
        target: target,
        success: false,
        responseTimeMs: stopwatch.elapsedMilliseconds,
        errorMessage: _formatError(e),
      );
    }
  }

  /// Checks connectivity to multiple domains in parallel
  /// Uses isolates for true parallel execution
  /// Returns a stream of results as they complete
  static Stream<ConnectivityResult> checkMultiple(
    List<String> targets, {
    Duration timeout = defaultTimeout,
    int concurrency = defaultConcurrency,
  }) async* {
    if (targets.isEmpty) return;

    // Create batches for controlled concurrency
    final batches = <List<String>>[];
    for (var i = 0; i < targets.length; i += concurrency) {
      batches.add(
        targets.sublist(
          i,
          i + concurrency > targets.length ? targets.length : i + concurrency,
        ),
      );
    }

    for (final batch in batches) {
      // Run batch in parallel using isolates
      final futures = batch.map((target) => _checkInIsolate(target, timeout));
      final results = await Future.wait(futures);

      for (final result in results) {
        yield result;
      }
    }
  }

  /// Runs a connectivity check in a separate isolate
  static Future<ConnectivityResult> _checkInIsolate(
    String target,
    Duration timeout,
  ) async {
    try {
      // Use Isolate.run for parallel execution
      return await Isolate.run(() async {
        final uri = _buildUri(target);
        final stopwatch = Stopwatch()..start();

        try {
          final client = http.Client();
          try {
            final response = await client.head(uri).timeout(timeout);
            stopwatch.stop();

            return ConnectivityResult(
              target: target,
              success: response.statusCode < 400,
              responseTimeMs: stopwatch.elapsedMilliseconds,
              statusCode: response.statusCode,
            );
          } finally {
            client.close();
          }
        } on TimeoutException {
          stopwatch.stop();
          return ConnectivityResult(
            target: target,
            success: false,
            responseTimeMs: stopwatch.elapsedMilliseconds,
            errorMessage: 'Connection timed out after ${timeout.inSeconds}s',
          );
        } catch (e) {
          stopwatch.stop();
          return ConnectivityResult(
            target: target,
            success: false,
            responseTimeMs: stopwatch.elapsedMilliseconds,
            errorMessage: e.toString(),
          );
        }
      });
    } catch (e) {
      // Fallback if isolate fails
      return checkSingle(target, timeout: timeout);
    }
  }

  /// Builds a URI from a domain string
  /// Adds https:// if no protocol specified
  static Uri _buildUri(String target) {
    String url = target.trim();

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://$url';
    }

    return Uri.parse(url);
  }

  /// Formats error messages for display
  static String _formatError(dynamic error) {
    final message = error.toString();

    // Simplify common error messages
    if (message.contains('SocketException')) {
      if (message.contains('No route to host')) {
        return 'No route to host';
      }
      if (message.contains('Connection refused')) {
        return 'Connection refused';
      }
      if (message.contains('Network is unreachable')) {
        return 'Network unreachable';
      }
      return 'Connection failed';
    }

    if (message.contains('HandshakeException')) {
      return 'SSL/TLS handshake failed';
    }

    if (message.contains('CertificateException')) {
      return 'Invalid certificate';
    }

    // Truncate long messages
    if (message.length > 100) {
      return '${message.substring(0, 97)}...';
    }

    return message;
  }

  /// Checks if a domain is reachable (quick check)
  static Future<bool> isReachable(String target, {Duration? timeout}) async {
    final result =
        await checkSingle(target, timeout: timeout ?? defaultTimeout);
    return result.success;
  }
}

/// Extension to provide progress tracking
extension ConnectivityServiceProgress on ConnectivityService {
  /// Checks multiple targets with progress callback
  static Stream<CheckProgress> checkWithProgress(
    List<String> targets, {
    Duration timeout = ConnectivityService.defaultTimeout,
    int concurrency = ConnectivityService.defaultConcurrency,
  }) async* {
    if (targets.isEmpty) return;

    int completed = 0;
    int successful = 0;
    int failed = 0;
    final total = targets.length;

    await for (final result in ConnectivityService.checkMultiple(
      targets,
      timeout: timeout,
      concurrency: concurrency,
    )) {
      completed++;
      if (result.success) {
        successful++;
      } else {
        failed++;
      }

      yield CheckProgress(
        result: result,
        completed: completed,
        total: total,
        successful: successful,
        failed: failed,
      );
    }
  }
}

/// Progress information for batch checks
class CheckProgress {
  final ConnectivityResult result;
  final int completed;
  final int total;
  final int successful;
  final int failed;

  CheckProgress({
    required this.result,
    required this.completed,
    required this.total,
    required this.successful,
    required this.failed,
  });

  double get progress => total > 0 ? completed / total : 0;
  int get remaining => total - completed;
  bool get isComplete => completed >= total;
}
