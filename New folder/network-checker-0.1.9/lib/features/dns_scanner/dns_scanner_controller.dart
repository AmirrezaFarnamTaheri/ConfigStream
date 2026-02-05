import 'package:flutter/foundation.dart';

import '../../core/services/dns_latency_service.dart';
import 'data/dns_providers.dart';

/// Check status for a DNS provider
enum DnsCheckStatus { idle, checking, success, failure }

/// State for a DNS provider in the scanner
class DnsProviderState {
  final DnsProvider provider;
  final String primaryAddress;
  final DnsCheckStatus status;
  final DnsLatencyResult? result;

  DnsProviderState({
    required this.provider,
    required this.primaryAddress,
    this.status = DnsCheckStatus.idle,
    this.result,
  });

  DnsProviderState copyWith({
    DnsCheckStatus? status,
    DnsLatencyResult? result,
  }) {
    return DnsProviderState(
      provider: provider,
      primaryAddress: primaryAddress,
      status: status ?? this.status,
      result: result ?? this.result,
    );
  }
}

/// Sort mode for DNS results
enum DnsSortMode {
  name,
  latency,
  status,
}

class DnsScannerController extends ChangeNotifier {
  List<DnsProviderState> _providers = [];
  List<DnsProvider> _customProviders = [];
  bool _isScanning = false;
  int _scannedCount = 0;
  int _successCount = 0;
  int _failureCount = 0;
  DnsSortMode _sortMode = DnsSortMode.name;
  int _nextCustomId = 1000; // Start custom IDs from 1000

  // Getters
  List<DnsProviderState> get providers => _sortedProviders;
  List<DnsProvider> get customProviders => _customProviders;
  bool get isScanning => _isScanning;
  int get scannedCount => _scannedCount;
  int get successCount => _successCount;
  int get failureCount => _failureCount;
  int get totalCount => _providers.length;
  double get progress => totalCount > 0 ? _scannedCount / totalCount : 0;
  DnsSortMode get sortMode => _sortMode;

  List<DnsProviderState> get _sortedProviders {
    final sorted = List<DnsProviderState>.from(_providers);
    switch (_sortMode) {
      case DnsSortMode.name:
        sorted.sort((a, b) => a.provider.name.compareTo(b.provider.name));
      case DnsSortMode.latency:
        sorted.sort((a, b) {
          final aLatency = a.result?.latencyMs ?? 999999;
          final bLatency = b.result?.latencyMs ?? 999999;
          return aLatency.compareTo(bLatency);
        });
      case DnsSortMode.status:
        sorted.sort((a, b) {
          final statusOrder = {
            DnsCheckStatus.success: 0,
            DnsCheckStatus.failure: 1,
            DnsCheckStatus.checking: 2,
            DnsCheckStatus.idle: 3,
          };
          final aOrder = statusOrder[a.status]!;
          final bOrder = statusOrder[b.status]!;
          if (aOrder != bOrder) return aOrder.compareTo(bOrder);
          // Secondary sort by latency for successful ones
          if (a.status == DnsCheckStatus.success && b.status == DnsCheckStatus.success) {
            final aLatency = a.result?.latencyMs ?? 999999;
            final bLatency = b.result?.latencyMs ?? 999999;
            return aLatency.compareTo(bLatency);
          }
          return 0;
        });
    }
    return sorted;
  }

  DnsScannerController() {
    _loadProviders();
  }

  void _loadProviders() {
    _providers = [];

    // Add default providers (using only primary address)
    for (final provider in defaultDnsProviders) {
      if (provider.addresses.isNotEmpty) {
        _providers.add(DnsProviderState(
          provider: provider,
          primaryAddress: provider.addresses.first,
        ));
      }
    }

    // Add custom providers
    for (final provider in _customProviders) {
      _providers.add(DnsProviderState(
        provider: provider,
        primaryAddress: provider.addresses.first,
      ));
    }

    notifyListeners();
  }

  /// Add custom DNS servers from text (one per line)
  void addCustomDns(String text) {
    final lines = text.split('\n');
    
    for (var line in lines) {
      line = line.trim();
      if (line.isEmpty) continue;

      // Validate IP address format
      final ip = RegExp(r'^(\d{1,3}\.){3}\d{1,3}$');
      if (!ip.hasMatch(line)) continue;

      // Check if already exists
      final exists = _providers.any((p) => p.primaryAddress == line);
      if (exists) continue;

      final customProvider = DnsProvider.custom(line, _nextCustomId++);
      _customProviders.add(customProvider);
      _providers.add(DnsProviderState(
        provider: customProvider,
        primaryAddress: line,
      ));
    }

    notifyListeners();
  }

  /// Remove a custom DNS provider
  void removeCustomDns(String address) {
    _customProviders.removeWhere((p) => p.addresses.contains(address));
    _providers.removeWhere((p) => p.provider.isCustom && p.primaryAddress == address);
    notifyListeners();
  }

  /// Set the sort mode
  void setSortMode(DnsSortMode mode) {
    _sortMode = mode;
    notifyListeners();
  }

  /// Scan all DNS providers for latency
  Future<void> scanAll() async {
    if (_isScanning) return;

    _isScanning = true;
    _scannedCount = 0;
    _successCount = 0;
    _failureCount = 0;

    // Reset all statuses
    _providers = _providers.map((p) => p.copyWith(
      status: DnsCheckStatus.checking,
      result: null,
    )).toList();
    notifyListeners();

    // Build targets list
    final targets = _providers
        .map((p) => (p.primaryAddress, p.provider.name))
        .toList();

    await for (final result in DnsLatencyService.checkMultiple(targets)) {
      final index = _providers.indexWhere((p) => p.primaryAddress == result.address);
      if (index != -1) {
        _providers[index] = _providers[index].copyWith(
          status: result.success ? DnsCheckStatus.success : DnsCheckStatus.failure,
          result: result,
        );

        _scannedCount++;
        if (result.success) {
          _successCount++;
        } else {
          _failureCount++;
        }

        notifyListeners();
      }
    }

    _isScanning = false;
    // Auto-sort by latency after scan completes
    _sortMode = DnsSortMode.latency;
    notifyListeners();
  }

  /// Scan a single DNS provider
  Future<void> scanSingle(String address) async {
    final index = _providers.indexWhere((p) => p.primaryAddress == address);
    if (index == -1) return;

    _providers[index] = _providers[index].copyWith(status: DnsCheckStatus.checking);
    notifyListeners();

    final result = await DnsLatencyService.checkSingle(
      address,
      _providers[index].provider.name,
    );

    _providers[index] = _providers[index].copyWith(
      status: result.success ? DnsCheckStatus.success : DnsCheckStatus.failure,
      result: result,
    );
    notifyListeners();
  }

  /// Stop scanning
  void stopScanning() {
    _isScanning = false;
    notifyListeners();
  }

  /// Reset all results
  void resetResults() {
    _providers = _providers.map((p) => DnsProviderState(
      provider: p.provider,
      primaryAddress: p.primaryAddress,
    )).toList();
    _scannedCount = 0;
    _successCount = 0;
    _failureCount = 0;
    notifyListeners();
  }

  /// Get the fastest DNS providers (top 5)
  List<DnsProviderState> get fastestProviders {
    final successful = _providers
        .where((p) => p.status == DnsCheckStatus.success && p.result != null)
        .toList();
    successful.sort((a, b) {
      final aLatency = a.result!.latencyMs ?? 999999;
      final bLatency = b.result!.latencyMs ?? 999999;
      return aLatency.compareTo(bLatency);
    });
    return successful.take(5).toList();
  }
}

