import 'package:flutter/foundation.dart';

import '../../core/services/dns_hunter_service.dart';
import 'data/dns_ranges.dart';

/// State for the DNS Hunter feature
enum DnsHunterState {
  idle,
  loadingRanges,
  scanning,
  testingSecure,
  completed,
  error,
}

/// Sort mode for results
enum DnsHunterSortMode {
  ip,
  latency,
}

class DnsHunterController extends ChangeNotifier {
  // State
  DnsHunterState _state = DnsHunterState.idle;
  String? _errorMessage;
  
  // Configuration
  DnsHunterTarget _target = DnsHunterTarget.twitter;
  String _customDomain = '';
  List<CidrRange> _availableRanges = [];
  List<CidrRange> _selectedRanges = [];
  
  // Progress
  int _totalIps = 0;
  int _scannedIps = 0;
  int _cleanCount = 0;
  int _secureCount = 0;
  
  // Results
  List<DnsHunterResult> _cleanResults = [];
  DnsHunterSortMode _sortMode = DnsHunterSortMode.latency;
  
  // Scan control
  bool _stopRequested = false;
  
  // Getters
  DnsHunterState get state => _state;
  String? get errorMessage => _errorMessage;
  DnsHunterTarget get target => _target;
  String get customDomain => _customDomain;
  List<CidrRange> get availableRanges => _availableRanges;
  List<CidrRange> get selectedRanges => _selectedRanges;
  int get totalIps => _totalIps;
  int get scannedIps => _scannedIps;
  int get cleanCount => _cleanCount;
  int get secureCount => _secureCount;
  double get progress => _totalIps > 0 ? _scannedIps / _totalIps : 0;
  bool get isScanning => _state == DnsHunterState.scanning || _state == DnsHunterState.testingSecure;
  DnsHunterSortMode get sortMode => _sortMode;
  
  List<DnsHunterResult> get cleanResults {
    final sorted = List<DnsHunterResult>.from(_cleanResults);
    switch (_sortMode) {
      case DnsHunterSortMode.ip:
        sorted.sort((a, b) => _compareIps(a.ip, b.ip));
      case DnsHunterSortMode.latency:
        sorted.sort((a, b) => (a.latencyMs ?? 9999).compareTo(b.latencyMs ?? 9999));
    }
    return sorted;
  }
  
  List<DnsHunterResult> get secureResults => 
      _cleanResults.where((r) => r.supportsSecureDns).toList();
  
  int _compareIps(String a, String b) {
    final aParts = a.split('.').map((p) => int.tryParse(p) ?? 0).toList();
    final bParts = b.split('.').map((p) => int.tryParse(p) ?? 0).toList();
    for (var i = 0; i < 4; i++) {
      if (aParts[i] != bParts[i]) return aParts[i].compareTo(bParts[i]);
    }
    return 0;
  }
  
  /// Set target for verification
  void setTarget(DnsHunterTarget target) {
    _target = target;
    notifyListeners();
  }
  
  /// Set custom domain (when target is custom)
  void setCustomDomain(String domain) {
    _customDomain = domain.trim();
    notifyListeners();
  }
  
  /// Set sort mode
  void setSortMode(DnsHunterSortMode mode) {
    _sortMode = mode;
    notifyListeners();
  }
  
  /// Load CIDR ranges from embedded data
  void loadRanges() {
    _state = DnsHunterState.loadingRanges;
    _errorMessage = null;
    notifyListeners();
    
    try {
      _availableRanges = [];
      
      // Load from embedded data
      for (final provider in dnsRangeProviders) {
        for (final cidr in provider.ranges) {
          _availableRanges.add(CidrRange(
            cidr: cidr,
            provider: provider.name,
          ));
        }
      }
      
      if (_availableRanges.isEmpty) {
        _state = DnsHunterState.error;
        _errorMessage = 'No CIDR ranges found';
        notifyListeners();
        return;
      }
      
      _state = DnsHunterState.idle;
      notifyListeners();
    } catch (e) {
      _state = DnsHunterState.error;
      _errorMessage = 'Error loading ranges: $e';
      notifyListeners();
    }
  }
  
  /// Toggle range selection
  void toggleRangeSelection(CidrRange range) {
    if (_selectedRanges.contains(range)) {
      _selectedRanges.remove(range);
    } else {
      _selectedRanges.add(range);
    }
    notifyListeners();
  }
  
  /// Select all ranges
  void selectAllRanges() {
    _selectedRanges = List.from(_availableRanges);
    notifyListeners();
  }
  
  /// Clear range selection
  void clearRangeSelection() {
    _selectedRanges.clear();
    notifyListeners();
  }
  
  /// Start scanning selected ranges
  Future<void> startScan() async {
    if (_selectedRanges.isEmpty) {
      _errorMessage = 'No ranges selected';
      notifyListeners();
      return;
    }
    
    if (_target == DnsHunterTarget.custom && _customDomain.isEmpty) {
      _errorMessage = 'Please enter a custom domain';
      notifyListeners();
      return;
    }
    
    _state = DnsHunterState.scanning;
    _stopRequested = false;
    _errorMessage = null;
    _cleanResults.clear();
    _cleanCount = 0;
    _secureCount = 0;
    _scannedIps = 0;
    
    // Calculate total IPs
    _totalIps = _selectedRanges.fold(0, (sum, range) => sum + range.totalIps);
    notifyListeners();
    
    // Collect all IPs to scan
    final allIps = <String>[];
    for (final range in _selectedRanges) {
      allIps.addAll(range.getIpsToScan());
    }
    
    // Scan in batches
    await for (final result in DnsHunterService.scanRange(
      allIps,
      _target,
      _customDomain,
    )) {
      if (_stopRequested) break;
      
      _scannedIps++;
      
      if (result.isClean) {
        _cleanResults.add(result);
        _cleanCount++;
      }
      
      notifyListeners();
    }
    
    if (_stopRequested) {
      _state = DnsHunterState.idle;
      notifyListeners();
      return;
    }
    
    // Phase 2: Test clean nodes for secure DNS
    if (_cleanResults.isNotEmpty) {
      _state = DnsHunterState.testingSecure;
      notifyListeners();
      
      final updatedResults = <DnsHunterResult>[];
      for (var i = 0; i < _cleanResults.length; i++) {
        if (_stopRequested) break;
        
        final result = await DnsHunterService.testSecureDns(_cleanResults[i]);
        updatedResults.add(result);
        
        if (result.supportsSecureDns) {
          _secureCount++;
        }
        
        notifyListeners();
      }
      
      _cleanResults = updatedResults;
    }
    
    _state = DnsHunterState.completed;
    notifyListeners();
  }
  
  /// Stop the current scan
  void stopScan() {
    _stopRequested = true;
    notifyListeners();
  }
  
  /// Reset to initial state
  void reset() {
    _state = DnsHunterState.idle;
    _errorMessage = null;
    _cleanResults.clear();
    _cleanCount = 0;
    _secureCount = 0;
    _scannedIps = 0;
    _totalIps = 0;
    _stopRequested = false;
    notifyListeners();
  }
  
  /// Get provider names from selected ranges
  Set<String> get selectedProviders => 
      _selectedRanges.map((r) => r.provider).toSet();
}

