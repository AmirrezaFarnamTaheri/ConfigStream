import 'dart:async';
import 'dart:io';
import 'dart:isolate';

/// Target domains and their expected IP patterns for clean DNS verification
enum DnsHunterTarget {
  twitter(
    name: 'X / Twitter',
    domain: 'x.com',
    // Cloudflare subnet patterns
    patterns: [
      r'^104\.(1[6-9]|2[0-3])\.',
      r'^172\.(6[4-9]|7[0-1])\.',
      r'^108\.162\.',
      r'^162\.15[8-9]\.',
    ],
  ),
  youtube(
    name: 'YouTube',
    domain: 'youtube.com',
    // Google subnet patterns
    patterns: [
      r'^142\.25[0-1]\.',
      r'^172\.217\.',
      r'^172\.253\.',
      r'^74\.125\.',
      r'^208\.117\.',
    ],
  ),
  custom(
    name: 'Custom',
    domain: '',
    patterns: [], // Accept any valid response
  );

  const DnsHunterTarget({
    required this.name,
    required this.domain,
    required this.patterns,
  });

  final String name;
  final String domain;
  final List<String> patterns;

  bool matchesPattern(String ip) {
    if (patterns.isEmpty) return true; // Custom target accepts any
    for (final pattern in patterns) {
      if (RegExp(pattern).hasMatch(ip)) return true;
    }
    return false;
  }
}

/// Result of a DNS hunter scan on a single IP
class DnsHunterResult {
  final String ip;
  final bool isClean;
  final int? latencyMs;
  final List<String> resolvedIps;
  final String? error;
  final bool supportsSecureDns;

  DnsHunterResult({
    required this.ip,
    required this.isClean,
    this.latencyMs,
    this.resolvedIps = const [],
    this.error,
    this.supportsSecureDns = false,
  });

  DnsHunterResult copyWith({bool? supportsSecureDns}) {
    return DnsHunterResult(
      ip: ip,
      isClean: isClean,
      latencyMs: latencyMs,
      resolvedIps: resolvedIps,
      error: error,
      supportsSecureDns: supportsSecureDns ?? this.supportsSecureDns,
    );
  }
}

/// A CIDR range to scan
class CidrRange {
  final String cidr;
  final String provider;

  CidrRange({required this.cidr, required this.provider});

  /// Parse CIDR notation and return list of IPs to scan
  List<String> getIpsToScan() {
    final parts = cidr.split('/');
    if (parts.length != 2) return [];

    final ipParts = parts[0].split('.');
    if (ipParts.length != 4) return [];

    final prefix = int.tryParse(parts[1]);
    if (prefix == null || prefix < 0 || prefix > 32) return [];

    final baseIp = ipParts.map((p) => int.tryParse(p) ?? 0).toList();

    // Calculate number of hosts
    final hostBits = 32 - prefix;
    final numHosts = 1 << hostBits; // 2^hostBits

    // For very large ranges, limit to reasonable number
    final maxHosts = numHosts > 256 ? 256 : numHosts;

    final ips = <String>[];
    for (var i = 1; i < maxHosts - 1; i++) {
      // Skip network and broadcast
      final ip = _addToIp(baseIp, i);
      ips.add(ip);
    }

    return ips;
  }

  String _addToIp(List<int> baseIp, int offset) {
    var carry = offset;
    final result = List<int>.from(baseIp);

    for (var i = 3; i >= 0; i--) {
      result[i] += carry;
      carry = result[i] ~/ 256;
      result[i] = result[i] % 256;
    }

    return result.join('.');
  }

  /// Get total number of IPs in this range
  int get totalIps {
    final parts = cidr.split('/');
    if (parts.length != 2) return 0;
    final prefix = int.tryParse(parts[1]);
    if (prefix == null) return 0;
    final hostBits = 32 - prefix;
    final numHosts = 1 << hostBits;
    return numHosts > 256 ? 254 : (numHosts - 2).clamp(0, 254);
  }
}

/// Service for hunting clean DNS servers in IP ranges
class DnsHunterService {
  static const Duration defaultTimeout = Duration(seconds: 2);
  static const int defaultConcurrency = 50;

  /// Build DNS query packet for a domain
  static List<int> _buildDnsQuery(String domain) {
    final query = <int>[
      0xAB, 0xCD, // Transaction ID
      0x01, 0x00, // Flags: standard query, recursion desired
      0x00, 0x01, // Questions: 1
      0x00, 0x00, // Answer RRs: 0
      0x00, 0x00, // Authority RRs: 0
      0x00, 0x00, // Additional RRs: 0
    ];

    // Encode domain name
    final labels = domain.split('.');
    for (final label in labels) {
      query.add(label.length);
      query.addAll(label.codeUnits);
    }
    query.add(0x00); // End of name

    query.addAll([
      0x00, 0x01, // Type: A
      0x00, 0x01, // Class: IN
    ]);

    return query;
  }

  /// Parse DNS response and extract A record IPs
  static List<String> _parseDnsResponse(List<int> data) {
    if (data.length < 12) return [];

    // Check if it's a valid response (QR bit set)
    if ((data[2] & 0x80) == 0) return [];

    // Check response code (should be 0 for no error)
    final rcode = data[3] & 0x0F;
    if (rcode != 0) return [];

    // Get answer count
    final answerCount = (data[6] << 8) | data[7];
    if (answerCount == 0) return [];

    final ips = <String>[];

    // Skip header (12 bytes) and question section
    var offset = 12;

    // Skip question section
    while (offset < data.length && data[offset] != 0) {
      if ((data[offset] & 0xC0) == 0xC0) {
        offset += 2;
        break;
      }
      offset += data[offset] + 1;
    }
    offset++; // Skip null terminator
    offset += 4; // Skip QTYPE and QCLASS

    // Parse answers
    for (var i = 0; i < answerCount && offset < data.length - 10; i++) {
      // Skip name (might be compressed)
      if ((data[offset] & 0xC0) == 0xC0) {
        offset += 2;
      } else {
        while (offset < data.length && data[offset] != 0) {
          offset += data[offset] + 1;
        }
        offset++;
      }

      if (offset + 10 > data.length) break;

      final type = (data[offset] << 8) | data[offset + 1];
      offset += 8; // Skip TYPE, CLASS, TTL

      final rdLength = (data[offset] << 8) | data[offset + 1];
      offset += 2;

      // Type A record (1) with length 4
      if (type == 1 && rdLength == 4 && offset + 4 <= data.length) {
        final ip =
            '${data[offset]}.${data[offset + 1]}.${data[offset + 2]}.${data[offset + 3]}';
        ips.add(ip);
      }

      offset += rdLength;
    }

    return ips;
  }

  /// Check if an IP is a private/local IP
  static bool _isPrivateIp(String ip) {
    final parts = ip.split('.').map((p) => int.tryParse(p) ?? 0).toList();
    if (parts.length != 4) return true;

    // 10.0.0.0/8
    if (parts[0] == 10) return true;

    // 192.168.0.0/16
    if (parts[0] == 192 && parts[1] == 168) return true;

    // 172.16.0.0/12
    if (parts[0] == 172 && parts[1] >= 16 && parts[1] <= 31) return true;

    return false;
  }

  /// Test a single IP as a DNS server
  static Future<DnsHunterResult> testSingle(
    String ip,
    DnsHunterTarget target,
    String domain, {
    Duration timeout = defaultTimeout,
  }) async {
    final targetDomain = target == DnsHunterTarget.custom ? domain : target.domain;
    final stopwatch = Stopwatch()..start();

    try {
      final addr = InternetAddress.tryParse(ip);
      if (addr == null) {
        return DnsHunterResult(ip: ip, isClean: false, error: 'Invalid IP');
      }

      final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);

      try {
        final query = _buildDnsQuery(targetDomain);
        socket.send(query, addr, 53);

        final completer = Completer<List<int>?>();
        Timer? timeoutTimer;

        timeoutTimer = Timer(timeout, () {
          if (!completer.isCompleted) {
            completer.complete(null);
          }
        });

        socket.listen((event) {
          if (event == RawSocketEvent.read && !completer.isCompleted) {
            final datagram = socket.receive();
            if (datagram != null &&
                datagram.data.length > 2 &&
                datagram.data[0] == 0xAB &&
                datagram.data[1] == 0xCD) {
              completer.complete(datagram.data);
            }
          }
        });

        final response = await completer.future;
        stopwatch.stop();
        timeoutTimer.cancel();

        if (response == null) {
          return DnsHunterResult(
            ip: ip,
            isClean: false,
            latencyMs: stopwatch.elapsedMilliseconds,
            error: 'Timeout',
          );
        }

        final resolvedIps = _parseDnsResponse(response);

        // Filter out the DNS server IP itself and private IPs
        final publicIps = resolvedIps
            .where((resolved) => resolved != ip && !_isPrivateIp(resolved))
            .toList();

        if (publicIps.isEmpty) {
          return DnsHunterResult(
            ip: ip,
            isClean: false,
            latencyMs: stopwatch.elapsedMilliseconds,
            resolvedIps: resolvedIps,
            error: 'No valid response',
          );
        }

        // Check if any resolved IP matches the expected pattern
        final isClean = target == DnsHunterTarget.custom ||
            publicIps.any((resolved) => target.matchesPattern(resolved));

        return DnsHunterResult(
          ip: ip,
          isClean: isClean,
          latencyMs: stopwatch.elapsedMilliseconds,
          resolvedIps: publicIps,
        );
      } finally {
        socket.close();
      }
    } on SocketException catch (e) {
      stopwatch.stop();
      return DnsHunterResult(
        ip: ip,
        isClean: false,
        latencyMs: stopwatch.elapsedMilliseconds,
        error: e.message,
      );
    } catch (e) {
      stopwatch.stop();
      return DnsHunterResult(
        ip: ip,
        isClean: false,
        latencyMs: stopwatch.elapsedMilliseconds,
        error: e.toString(),
      );
    }
  }

  /// Test if a clean DNS server supports secure DNS (DoH on port 443)
  static Future<DnsHunterResult> testSecureDns(
    DnsHunterResult result, {
    Duration timeout = const Duration(seconds: 8),
  }) async {
    if (!result.isClean) return result;

    try {
      // Try TCP connection to port 443
      final socket = await Socket.connect(
        result.ip,
        443,
        timeout: timeout,
      );

      // If we can connect, it might support DoH
      socket.destroy();

      return result.copyWith(supportsSecureDns: true);
    } catch (e) {
      return result.copyWith(supportsSecureDns: false);
    }
  }

  /// Scan multiple IPs in parallel
  static Stream<DnsHunterResult> scanRange(
    List<String> ips,
    DnsHunterTarget target,
    String customDomain, {
    Duration timeout = defaultTimeout,
    int concurrency = defaultConcurrency,
  }) async* {
    if (ips.isEmpty) return;

    // Create batches
    final batches = <List<String>>[];
    for (var i = 0; i < ips.length; i += concurrency) {
      batches.add(ips.sublist(
        i,
        i + concurrency > ips.length ? ips.length : i + concurrency,
      ));
    }

    for (final batch in batches) {
      final futures = batch.map((ip) => _testInIsolate(
            ip,
            target,
            customDomain,
            timeout,
          ));
      final results = await Future.wait(futures);

      for (final result in results) {
        yield result;
      }
    }
  }

  static Future<DnsHunterResult> _testInIsolate(
    String ip,
    DnsHunterTarget target,
    String customDomain,
    Duration timeout,
  ) async {
    try {
      return await Isolate.run(() async {
        return await testSingle(ip, target, customDomain, timeout: timeout);
      });
    } catch (e) {
      // Fallback if isolate fails
      return testSingle(ip, target, customDomain, timeout: timeout);
    }
  }

  /// Parse CIDR ranges from text file content
  static List<CidrRange> parseCidrRanges(String content) {
    final ranges = <CidrRange>[];
    String currentProvider = 'Unknown';

    final lines = content.split('\n');

    for (final line in lines) {
      // Check for provider name
      if (line.contains('Provider:')) {
        final match = RegExp(r'Provider:\s*(.+)').firstMatch(line);
        if (match != null) {
          currentProvider = match.group(1)?.trim() ?? 'Unknown';
        }
        continue;
      }

      // Check for CIDR notation
      final cidrMatch = RegExp(r'(\d+\.\d+\.\d+\.\d+/\d+)').firstMatch(line);
      if (cidrMatch != null) {
        ranges.add(CidrRange(
          cidr: cidrMatch.group(1)!,
          provider: currentProvider,
        ));
      }
    }

    return ranges;
  }
}

