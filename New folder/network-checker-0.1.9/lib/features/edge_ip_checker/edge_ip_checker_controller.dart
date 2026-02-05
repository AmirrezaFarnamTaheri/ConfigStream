import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/services/edge_ip_scanner.dart';

/// State for an IP in the checker
class IpCheckState {
  final String ip;
  final IpCheckStatus status;
  final EdgeIpResult? result;

  IpCheckState({
    required this.ip,
    this.status = IpCheckStatus.idle,
    this.result,
  });

  IpCheckState copyWith({
    IpCheckStatus? status,
    EdgeIpResult? result,
  }) {
    return IpCheckState(
      ip: ip,
      status: status ?? this.status,
      result: result ?? this.result,
    );
  }
}

enum IpCheckStatus { idle, checking, success, failure }

class EdgeIpCheckerController extends ChangeNotifier {

  // Scan configuration
  EdgeScanConfig _config = const EdgeScanConfig();
  EdgeScanConfig get config => _config;

  // Input text for IPs/subnets
  String _inputText = '';
  String get inputText => _inputText;

  // Parsed IPs
  List<String> _parsedIps = [];
  List<String> get parsedIps => _parsedIps;
  int get parsedIpCount => _parsedIps.length;

  // Scan state
  bool _isScanning = false;
  bool get isScanning => _isScanning;

  bool _isPreparingScan = false;
  bool get isPreparingScan => _isPreparingScan;

  int _scannedCount = 0;
  int get scannedCount => _scannedCount;

  int _successCount = 0;
  int get successCount => _successCount;

  int get failureCount => _scannedCount - _successCount;

  double get progress => _parsedIps.isNotEmpty ? _scannedCount / _parsedIps.length : 0;

  // Working IPs (sorted by latency)
  List<EdgeIpResult> _workingIps = [];
  List<EdgeIpResult> get workingIps => _workingIps;

  // Stream subscription for cancellation
  StreamSubscription? _scanSubscription;

  /// Update the IP input text and parse IPs
  void updateInput(String text) {
    _inputText = text;
    _parsedIps = EdgeIpScanner.parseIpInput(text);
    notifyListeners();
  }

  /// Update scan configuration
  void updateConfig({
    String? testDomain,
    String? testPath,
    int? port,
    Duration? timeout,
    int? maxWorkers,
    bool? testDownload,
    int? downloadSize,
  }) {
    _config = _config.copyWith(
      testDomain: testDomain,
      testPath: testPath,
      port: port,
      timeout: timeout,
      maxWorkers: maxWorkers,
      testDownload: testDownload,
      downloadSize: downloadSize,
    );
    notifyListeners();
  }

  /// Start scanning all parsed IPs
  Future<void> startScan() async {
    if (_isScanning || _isPreparingScan || _parsedIps.isEmpty) return;

    _isPreparingScan = true;
    _isScanning = true;
    _scannedCount = 0;
    _successCount = 0;
    _workingIps = [];
    notifyListeners();

    final scanner = EdgeIpScanner(config: _config);

    _scanSubscription = scanner.scanIps(_parsedIps).listen(
      (progress) {
        _isPreparingScan = false;
        _scannedCount = progress.completed;
        _successCount = progress.successful;
        _workingIps = progress.workingIps.toList()
          ..sort((a, b) => (a.latencyMs ?? double.infinity).compareTo(b.latencyMs ?? double.infinity));

        notifyListeners();
      },
      onDone: () {
        _isScanning = false;
        _scanSubscription = null;
        notifyListeners();
      },
      onError: (error) {
        debugPrint('Scan error: $error');
        _isScanning = false;
        _isPreparingScan = false;
        _scanSubscription = null;
        notifyListeners();
      },
    );
  }

  /// Stop the current scan
  void stopScan() {
    _scanSubscription?.cancel();
    _scanSubscription = null;
    _isScanning = false;
    _isPreparingScan = false;
    notifyListeners();
  }

  /// Reset all results
  void resetResults() {
    _scannedCount = 0;
    _successCount = 0;
    _workingIps = [];
    notifyListeners();
  }

  /// Clear input and results
  void clearAll() {
    _inputText = '';
    _parsedIps = [];
    _scannedCount = 0;
    _successCount = 0;
    _workingIps = [];
    notifyListeners();
  }

  /// Copy working IPs to clipboard format
  String getWorkingIpsText() {
    return _workingIps.map((r) => r.ip).join('\n');
  }

  /// Copy working IPs with details
  String getWorkingIpsDetailedText() {
    final buffer = StringBuffer();
    buffer.writeln('# Edge IP Scan Results');
    buffer.writeln('# Domain: ${_config.testDomain}');
    buffer.writeln('# Total scanned: $_scannedCount');
    buffer.writeln('# Working IPs: ${_workingIps.length}');
    buffer.writeln('# Timestamp: ${DateTime.now().toIso8601String()}');
    buffer.writeln('');

    for (final result in _workingIps) {
      final latency = result.latencyMs?.toStringAsFixed(2) ?? 'N/A';
      final speed = result.speedKbps?.toStringAsFixed(2) ?? 'N/A';
      buffer.writeln('${result.ip} | Latency: ${latency}ms | Speed: ${speed} KB/s');
    }

    return buffer.toString();
  }

  @override
  void dispose() {
    _scanSubscription?.cancel();
    super.dispose();
  }
}

