import 'dart:async';

import 'package:drift/drift.dart';
import 'package:flutter/foundation.dart';

import '../../core/services/connectivity_service.dart';
import '../../models/database.dart';
import 'data/top_domains.dart';

/// State for a domain in the checker
class DomainCheckState {
  final String domain;
  final bool isDefault;
  final CheckStatus status;
  final ConnectivityResult? result;

  DomainCheckState({
    required this.domain,
    required this.isDefault,
    this.status = CheckStatus.idle,
    this.result,
  });

  DomainCheckState copyWith({
    CheckStatus? status,
    ConnectivityResult? result,
  }) {
    return DomainCheckState(
      domain: domain,
      isDefault: isDefault,
      status: status ?? this.status,
      result: result ?? this.result,
    );
  }
}

enum CheckStatus { idle, checking, success, failure }

class DomainCheckerController extends ChangeNotifier {
  final AppDatabase _db = AppDatabase.instance;

  List<DomainCheckState> _domains = [];
  bool _isLoading = false;
  bool _isChecking = false;
  int _checkedCount = 0;
  int _successCount = 0;
  int _failureCount = 0;
  
  // Throttle UI updates for better performance
  Timer? _updateTimer;
  bool _hasPendingUpdate = false;
  static const _updateInterval = Duration(milliseconds: 100);

  List<DomainCheckState> get domains => _domains;
  bool get isLoading => _isLoading;
  bool get isChecking => _isChecking;
  int get checkedCount => _checkedCount;
  int get successCount => _successCount;
  int get failureCount => _failureCount;
  int get totalCount => _domains.length;
  double get progress => totalCount > 0 ? _checkedCount / totalCount : 0;
  
  /// Throttled notify - batches updates to avoid excessive UI rebuilds
  void _throttledNotify() {
    _hasPendingUpdate = true;
    _updateTimer ??= Timer(_updateInterval, () {
      _updateTimer = null;
      if (_hasPendingUpdate) {
        _hasPendingUpdate = false;
        notifyListeners();
      }
    });
  }
  
  /// Force immediate notification (for important state changes)
  void _immediateNotify() {
    _updateTimer?.cancel();
    _updateTimer = null;
    _hasPendingUpdate = false;
    notifyListeners();
  }
  
  @override
  void dispose() {
    _updateTimer?.cancel();
    super.dispose();
  }

  DomainCheckerController() {
    _loadDomains();
  }

  Future<void> _loadDomains() async {
    _isLoading = true;
    notifyListeners();

    try {
      // Sync default domains - add any missing ones from the hardcoded list
      await _syncDefaultDomains();
      
      // Load all domains from database
      final dbDomains = await _db.getAllDomains();
      _domains = dbDomains.map((d) => DomainCheckState(
        domain: d.url,
        isDefault: d.isDefault,
      )).toList();
    } catch (e) {
      debugPrint('Error loading domains: $e');
      // Fallback to hardcoded list
      _domains = topDomains.map((d) => DomainCheckState(
        domain: d,
        isDefault: true,
      )).toList();
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> _syncDefaultDomains() async {
    final existingDomains = await _db.getAllDomains();
    final existingUrls = existingDomains.map((d) => d.url).toSet();
    
    // Find domains that are in topDomains but not in the database
    final newDomains = topDomains
        .where((domain) => !existingUrls.contains(domain))
        .map((domain) => DomainEntriesCompanion.insert(
              url: domain,
              isDefault: const Value(true),
            ))
        .toList();
    
    if (newDomains.isNotEmpty) {
      await _db.insertDomains(newDomains);
      debugPrint('Added ${newDomains.length} new default domains');
    }
  }

  Future<void> addDomain(String url) async {
    // Normalize URL
    String normalizedUrl = url.trim().toLowerCase();
    if (normalizedUrl.startsWith('http://')) {
      normalizedUrl = normalizedUrl.substring(7);
    } else if (normalizedUrl.startsWith('https://')) {
      normalizedUrl = normalizedUrl.substring(8);
    }
    if (normalizedUrl.endsWith('/')) {
      normalizedUrl = normalizedUrl.substring(0, normalizedUrl.length - 1);
    }

    // Check if already exists
    final exists = await _db.domainExists(normalizedUrl);
    if (exists) return;

    // Add to database
    await _db.insertDomain(DomainEntriesCompanion.insert(
      url: normalizedUrl,
      isDefault: const Value(false),
    ));

    // Add to local list
    _domains.add(DomainCheckState(
      domain: normalizedUrl,
      isDefault: false,
    ));
    notifyListeners();
  }

  Future<void> removeDomain(String domain) async {
    // Find and remove from database
    final dbDomains = await _db.getAllDomains();
    final entry = dbDomains.firstWhere(
      (d) => d.url == domain,
      orElse: () => throw Exception('Domain not found'),
    );
    
    if (!entry.isDefault) {
      await _db.deleteDomain(entry.id);
      _domains.removeWhere((d) => d.domain == domain);
      notifyListeners();
    }
  }

  Future<void> checkAll() async {
    if (_isChecking) return;

    _isChecking = true;
    _checkedCount = 0;
    _successCount = 0;
    _failureCount = 0;

    // Reset all statuses to checking
    _domains = _domains.map((d) => d.copyWith(
      status: CheckStatus.checking,
      result: null,
    )).toList();
    _immediateNotify(); // Show spinners immediately

    final targets = _domains.map((d) => d.domain).toList();

    await for (final result in ConnectivityService.checkMultiple(targets)) {
      // Check if stop was requested
      if (!_isChecking) {
        // Mark remaining domains as idle
        _domains = _domains.map((d) {
          if (d.status == CheckStatus.checking) {
            return d.copyWith(status: CheckStatus.idle);
          }
          return d;
        }).toList();
        _immediateNotify();
        return;
      }

      final index = _domains.indexWhere((d) => d.domain == result.target);
      if (index != -1) {
        _domains[index] = _domains[index].copyWith(
          status: result.success ? CheckStatus.success : CheckStatus.failure,
          result: result,
        );
        
        _checkedCount++;
        if (result.success) {
          _successCount++;
        } else {
          _failureCount++;
        }

        _throttledNotify(); // Batch UI updates for results
      }
    }

    _isChecking = false;
    _immediateNotify(); // Ensure final state is shown
  }

  Future<void> checkSingle(String domain) async {
    final index = _domains.indexWhere((d) => d.domain == domain);
    if (index == -1) return;

    _domains[index] = _domains[index].copyWith(status: CheckStatus.checking);
    notifyListeners();

    final result = await ConnectivityService.checkSingle(domain);
    
    _domains[index] = _domains[index].copyWith(
      status: result.success ? CheckStatus.success : CheckStatus.failure,
      result: result,
    );
    notifyListeners();
  }

  void stopChecking() {
    _isChecking = false;
    _immediateNotify();
  }

  void resetResults() {
    _domains = _domains.map((d) => DomainCheckState(
      domain: d.domain,
      isDefault: d.isDefault,
    )).toList();
    _checkedCount = 0;
    _successCount = 0;
    _failureCount = 0;
    notifyListeners();
  }

  Future<void> refresh() async {
    await _loadDomains();
  }
}

