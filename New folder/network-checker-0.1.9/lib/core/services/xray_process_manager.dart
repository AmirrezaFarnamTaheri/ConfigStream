import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'xray_binary_service.dart';

/// Exception thrown when xray fails to start or encounters an error
class XrayStartupException implements Exception {
  final String message;
  final int? instanceId;
  final int? port;

  XrayStartupException(this.message, {this.instanceId, this.port});

  @override
  String toString() {
    if (instanceId != null && port != null) {
      return 'XrayStartupException (instance $instanceId, port $port): $message';
    }
    return 'XrayStartupException: $message';
  }
}

/// Exception thrown when a port is already in use
class PortInUseException implements Exception {
  final int port;
  final String message;

  PortInUseException(this.port, [String? message])
      : message = message ?? 'Port $port is already in use';

  @override
  String toString() => message;
}

/// Represents a running xray instance
class XrayInstance {
  final int id;
  final int port;
  Process process;
  final String configPath;
  bool isAvailable;
  StreamSubscription<String>? _stdoutSubscription;
  StreamSubscription<String>? _stderrSubscription;
  final List<String> _errorLog = [];

  XrayInstance({
    required this.id,
    required this.port,
    required this.process,
    required this.configPath,
    this.isAvailable = true,
  });

  List<String> get errorLog => List.unmodifiable(_errorLog);

  void addError(String error) {
    _errorLog.add(error);
    // Keep only last 50 error lines to prevent memory bloat
    if (_errorLog.length > 50) {
      _errorLog.removeAt(0);
    }
  }

  Future<void> cancelSubscriptions() async {
    await _stdoutSubscription?.cancel();
    await _stderrSubscription?.cancel();
    _stdoutSubscription = null;
    _stderrSubscription = null;
  }
}

/// Manages multiple xray process instances for parallel testing
class XrayProcessManager {
  final XrayBinaryService _binaryService;
  final List<XrayInstance> _instances = [];
  final int basePort;

  Directory? _tempConfigDir;

  XrayProcessManager({
    XrayBinaryService? binaryService,
    this.basePort = 10808,
  }) : _binaryService = binaryService ?? XrayBinaryService();

  /// Get all running instances
  List<XrayInstance> get instances => List.unmodifiable(_instances);

  /// Get number of running instances
  int get instanceCount => _instances.length;

  /// Parse and validate a config JSON, returning the parsed map
  Map<String, dynamic> parseConfig(String configJson) {
    try {
      final config = json.decode(configJson) as Map<String, dynamic>;

      // Validate required sections
      if (!config.containsKey('inbounds')) {
        throw FormatException('Config missing "inbounds" section');
      }
      if (!config.containsKey('outbounds')) {
        throw FormatException('Config missing "outbounds" section');
      }

      return config;
    } catch (e) {
      if (e is FormatException) rethrow;
      throw FormatException('Invalid JSON: $e');
    }
  }

  /// Extract the original outbound address from config
  String? extractOutboundAddress(Map<String, dynamic> config) {
    final outbounds = config['outbounds'] as List<dynamic>?;
    if (outbounds == null || outbounds.isEmpty) return null;

    // Find the proxy outbound (usually the first one or tagged as "proxy")
    for (final outbound in outbounds) {
      final map = outbound as Map<String, dynamic>;
      final protocol = map['protocol'] as String?;

      if (protocol == 'vless' || protocol == 'vmess' || protocol == 'trojan') {
        final settings = map['settings'] as Map<String, dynamic>?;
        final vnext = settings?['vnext'] as List<dynamic>?;
        if (vnext != null && vnext.isNotEmpty) {
          final server = vnext[0] as Map<String, dynamic>;
          return server['address'] as String?;
        }
      }
    }
    return null;
  }

  /// Extract the inbound port from config
  int? extractInboundPort(Map<String, dynamic> config) {
    final inbounds = config['inbounds'] as List<dynamic>?;
    if (inbounds == null || inbounds.isEmpty) return null;

    for (final inbound in inbounds) {
      final map = inbound as Map<String, dynamic>;
      final protocol = map['protocol'] as String?;

      if (protocol == 'socks' || protocol == 'http') {
        return map['port'] as int?;
      }
    }
    return null;
  }

  /// Create a modified config with new port and IP
  Map<String, dynamic> createModifiedConfig(
    Map<String, dynamic> baseConfig,
    int newPort,
    String newAddress,
  ) {
    // Deep copy the config
    final config =
        json.decode(json.encode(baseConfig)) as Map<String, dynamic>;

    // Modify inbound port
    final inbounds = config['inbounds'] as List<dynamic>;
    for (final inbound in inbounds) {
      final map = inbound as Map<String, dynamic>;
      final protocol = map['protocol'] as String?;
      if (protocol == 'socks' || protocol == 'http') {
        map['port'] = newPort;
        break;
      }
    }

    // Modify outbound address
    final outbounds = config['outbounds'] as List<dynamic>;
    for (final outbound in outbounds) {
      final map = outbound as Map<String, dynamic>;
      final protocol = map['protocol'] as String?;

      if (protocol == 'vless' || protocol == 'vmess' || protocol == 'trojan') {
        final settings = map['settings'] as Map<String, dynamic>;
        final vnext = settings['vnext'] as List<dynamic>;
        if (vnext.isNotEmpty) {
          final server = vnext[0] as Map<String, dynamic>;
          server['address'] = newAddress;
        }
        break;
      }
    }

    return config;
  }

  /// Check if a port is available
  Future<bool> _isPortAvailable(int port) async {
    try {
      final server = await ServerSocket.bind('127.0.0.1', port);
      await server.close();
      return true;
    } on SocketException {
      return false;
    }
  }

  /// Check all required ports are available before starting
  Future<List<int>> _checkPortsAvailable(int startPort, int count) async {
    final usedPorts = <int>[];
    for (int i = 0; i < count; i++) {
      final port = startPort + i;
      if (!await _isPortAvailable(port)) {
        usedPorts.add(port);
      }
    }
    return usedPorts;
  }

  /// Start multiple xray instances
  Future<void> startInstances(
    Map<String, dynamic> baseConfig,
    int count,
  ) async {
    // Ensure we have xray binary
    final xrayPath = await _binaryService.getXrayBinaryPath();
    if (!await File(xrayPath).exists()) {
      throw StateError('Xray binary not found. Please download it first.');
    }

    // Check if all required ports are available BEFORE starting any instances
    final usedPorts = await _checkPortsAvailable(basePort, count);
    if (usedPorts.isNotEmpty) {
      throw PortInUseException(
        usedPorts.first,
        'The following ports are already in use: ${usedPorts.join(", ")}. '
            'Please free these ports or change the base port in settings.',
      );
    }

    // Create temp directory for configs
    final xrayDir = await _binaryService.getXrayDirectory();
    _tempConfigDir = Directory('${xrayDir.path}/temp_configs');
    if (await _tempConfigDir!.exists()) {
      await _tempConfigDir!.delete(recursive: true);
    }
    await _tempConfigDir!.create();

    // Start instances
    final startedInstances = <XrayInstance>[];
    try {
      for (int i = 0; i < count; i++) {
        final port = basePort + i;

        // Create config for this instance (using original address as placeholder)
        final originalAddress =
            extractOutboundAddress(baseConfig) ?? 'placeholder';
        final instanceConfig =
            createModifiedConfig(baseConfig, port, originalAddress);

        // Write config file
        final configPath = '${_tempConfigDir!.path}/config_$i.json';
        await File(configPath).writeAsString(json.encode(instanceConfig));

        // Start xray process
        final process = await Process.start(
          xrayPath,
          ['-c', configPath],
          workingDirectory: xrayDir.path,
        );

        final instance = XrayInstance(
          id: i,
          port: port,
          process: process,
          configPath: configPath,
          isAvailable: true,
        );

        // Set up stream listeners and track subscriptions
        _setupProcessListeners(instance);

        startedInstances.add(instance);
        _instances.add(instance);
      }

      // Wait for all ports to be ready with better error detection
      await _waitForAllInstancesReady(startedInstances);
    } catch (e) {
      // Clean up any started instances if something fails
      for (final instance in startedInstances) {
        await _killInstance(instance);
      }
      _instances.clear();

      // Clean up temp configs
      if (_tempConfigDir != null && await _tempConfigDir!.exists()) {
        try {
          await _tempConfigDir!.delete(recursive: true);
        } catch (_) {}
      }

      rethrow;
    }
  }

  /// Set up stdout/stderr listeners for an instance
  void _setupProcessListeners(XrayInstance instance) {
    instance._stdoutSubscription =
        instance.process.stdout.transform(utf8.decoder).listen((data) {
      debugPrint('Xray[${instance.id}]: $data');
    });

    instance._stderrSubscription =
        instance.process.stderr.transform(utf8.decoder).listen((data) {
      debugPrint('Xray[${instance.id}] ERR: $data');
      instance.addError(data);
    });
  }

  /// Wait for all instances to be ready with proper error detection
  Future<void> _waitForAllInstancesReady(List<XrayInstance> instances) async {
    const timeout = Duration(seconds: 10);
    final deadline = DateTime.now().add(timeout);

    for (final instance in instances) {
      final remainingTime = deadline.difference(DateTime.now());
      if (remainingTime.isNegative) {
        throw XrayStartupException(
          'Timeout waiting for xray instances to start',
          instanceId: instance.id,
          port: instance.port,
        );
      }

      await _waitForPortOrError(instance, remainingTime);
    }
  }

  /// Wait for a port to be available or detect if the process has exited with an error
  Future<void> _waitForPortOrError(
      XrayInstance instance, Duration timeout) async {
    final deadline = DateTime.now().add(timeout);
    Socket? socket;

    while (DateTime.now().isBefore(deadline)) {
      // Check if process has exited (error condition)
      final exitCodeFuture = instance.process.exitCode;
      final checkResult = await Future.any([
        exitCodeFuture.then((code) => ('exited', code)),
        Future.delayed(const Duration(milliseconds: 100))
            .then((_) => ('timeout', -1)),
      ]);

      if (checkResult.$1 == 'exited') {
        final exitCode = checkResult.$2;
        final errors = instance.errorLog.join('\n');
        throw XrayStartupException(
          'Xray process exited with code $exitCode. Errors:\n$errors',
          instanceId: instance.id,
          port: instance.port,
        );
      }

      // Try to connect to the port
      try {
        socket = await Socket.connect(
          '127.0.0.1',
          instance.port,
          timeout: const Duration(milliseconds: 200),
        );
        await socket.close();
        socket = null;
        return; // Port is ready
      } on SocketException {
        // Port not ready yet, continue waiting
      } finally {
        // Ensure socket is cleaned up
        try {
          await socket?.close();
        } catch (_) {}
        socket = null;
      }
    }

    // Timeout reached - check for any errors in the log
    final errors = instance.errorLog;
    if (errors.isNotEmpty) {
      throw XrayStartupException(
        'Port ${instance.port} did not become ready. Xray errors:\n${errors.join('\n')}',
        instanceId: instance.id,
        port: instance.port,
      );
    }

    throw XrayStartupException(
      'Port ${instance.port} did not become ready within timeout',
      instanceId: instance.id,
      port: instance.port,
    );
  }

  /// Update an instance's config to use a new IP address
  Future<void> updateInstanceAddress(
      XrayInstance instance, String newAddress, Map<String, dynamic> baseConfig) async {
    // Create new config with the new address
    final newConfig = createModifiedConfig(baseConfig, instance.port, newAddress);

    // Write updated config
    await File(instance.configPath).writeAsString(json.encode(newConfig));

    // Cancel existing subscriptions before killing
    await instance.cancelSubscriptions();

    // Kill and wait for the process to exit
    instance.process.kill();
    try {
      await instance.process.exitCode.timeout(
        const Duration(seconds: 2),
        onTimeout: () {
          instance.process.kill(ProcessSignal.sigkill);
          return -1;
        },
      );
    } catch (_) {
      // Process might have already exited
    }

    final xrayPath = await _binaryService.getXrayBinaryPath();
    final xrayDir = await _binaryService.getXrayDirectory();

    final newProcess = await Process.start(
      xrayPath,
      ['-c', instance.configPath],
      workingDirectory: xrayDir.path,
    );

    // Update instance with new process
    instance.process = newProcess;
    instance._errorLog.clear();

    // Set up new listeners
    _setupProcessListeners(instance);

    // Wait for the port to be ready with error detection
    try {
      await _waitForPortOrError(instance, const Duration(seconds: 5));
    } catch (e) {
      // If the instance fails to start, mark it as unavailable but don't throw
      // This allows the scan to continue with remaining instances
      instance.isAvailable = false;
      debugPrint('Instance ${instance.id} failed to restart: $e');
      rethrow;
    }
  }

  /// Kill a single instance and clean up its resources
  Future<void> _killInstance(XrayInstance instance) async {
    try {
      // Cancel subscriptions first
      await instance.cancelSubscriptions();

      // Kill the process
      instance.process.kill();
      await instance.process.exitCode.timeout(
        const Duration(seconds: 2),
        onTimeout: () {
          instance.process.kill(ProcessSignal.sigkill);
          return -1;
        },
      );
    } catch (e) {
      debugPrint('Error killing xray instance ${instance.id}: $e');
    }
  }

  /// Get an available instance for testing
  XrayInstance? getAvailableInstance() {
    for (final instance in _instances) {
      if (instance.isAvailable) {
        return instance;
      }
    }
    return null;
  }

  /// Mark an instance as busy
  void markInstanceBusy(XrayInstance instance) {
    instance.isAvailable = false;
  }

  /// Mark an instance as available
  void markInstanceAvailable(XrayInstance instance) {
    instance.isAvailable = true;
  }

  /// Stop all xray instances
  Future<void> stopAll() async {
    // Kill all instances in parallel for faster cleanup
    await Future.wait(_instances.map(_killInstance));
    _instances.clear();

    // Clean up temp configs
    if (_tempConfigDir != null && await _tempConfigDir!.exists()) {
      try {
        await _tempConfigDir!.delete(recursive: true);
      } catch (e) {
        debugPrint('Error cleaning temp configs: $e');
      }
    }
    _tempConfigDir = null;
  }

  /// Dispose and clean up
  Future<void> dispose() async {
    await stopAll();
  }
}
