import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'database.g.dart';

/// Table for storing domain list entries
class DomainEntries extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get url => text().withLength(min: 1, max: 500)();
  BoolColumn get isDefault => boolean().withDefault(const Constant(false))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
}

@DriftDatabase(tables: [DomainEntries])
class AppDatabase extends _$AppDatabase {
  AppDatabase._() : super(_openConnection());

  static AppDatabase? _instance;

  static AppDatabase get instance {
    _instance ??= AppDatabase._();
    return _instance!;
  }

  @override
  int get schemaVersion => 2;

  @override
  MigrationStrategy get migration {
    return MigrationStrategy(
      onCreate: (Migrator m) async {
        await m.createAll();
      },
      onUpgrade: (Migrator m, int from, int to) async {
        if (from < 2) {
          // Drop the old history tables if they exist
          await customStatement('DROP TABLE IF EXISTS check_results');
          await customStatement('DROP TABLE IF EXISTS check_sessions');
        }
      },
    );
  }

  static QueryExecutor _openConnection() {
    return driftDatabase(name: 'rdnbenet_db');
  }

  // Domain Entry Operations
  Future<List<DomainEntry>> getAllDomains() => select(domainEntries).get();

  Future<List<DomainEntry>> getDefaultDomains() =>
      (select(domainEntries)..where((d) => d.isDefault.equals(true))).get();

  Future<List<DomainEntry>> getCustomDomains() =>
      (select(domainEntries)..where((d) => d.isDefault.equals(false))).get();

  Future<int> insertDomain(DomainEntriesCompanion entry) =>
      into(domainEntries).insert(entry);

  Future<void> insertDomains(List<DomainEntriesCompanion> entries) async {
    await batch((batch) {
      batch.insertAll(domainEntries, entries);
    });
  }

  Future<int> deleteDomain(int id) =>
      (delete(domainEntries)..where((d) => d.id.equals(id))).go();

  Future<int> deleteCustomDomains() =>
      (delete(domainEntries)..where((d) => d.isDefault.equals(false))).go();

  Future<bool> domainExists(String url) async {
    final query = select(domainEntries)..where((d) => d.url.equals(url));
    final result = await query.getSingleOrNull();
    return result != null;
  }
}
