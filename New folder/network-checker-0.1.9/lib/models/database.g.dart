// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $DomainEntriesTable extends DomainEntries
    with TableInfo<$DomainEntriesTable, DomainEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $DomainEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _urlMeta = const VerificationMeta('url');
  @override
  late final GeneratedColumn<String> url = GeneratedColumn<String>(
    'url',
    aliasedName,
    false,
    additionalChecks: GeneratedColumn.checkTextLength(
      minTextLength: 1,
      maxTextLength: 500,
    ),
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _isDefaultMeta = const VerificationMeta(
    'isDefault',
  );
  @override
  late final GeneratedColumn<bool> isDefault = GeneratedColumn<bool>(
    'is_default',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_default" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [id, url, isDefault, createdAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'domain_entries';
  @override
  VerificationContext validateIntegrity(
    Insertable<DomainEntry> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('url')) {
      context.handle(
        _urlMeta,
        url.isAcceptableOrUnknown(data['url']!, _urlMeta),
      );
    } else if (isInserting) {
      context.missing(_urlMeta);
    }
    if (data.containsKey('is_default')) {
      context.handle(
        _isDefaultMeta,
        isDefault.isAcceptableOrUnknown(data['is_default']!, _isDefaultMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  DomainEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return DomainEntry(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      url: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}url'],
      )!,
      isDefault: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_default'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $DomainEntriesTable createAlias(String alias) {
    return $DomainEntriesTable(attachedDatabase, alias);
  }
}

class DomainEntry extends DataClass implements Insertable<DomainEntry> {
  final int id;
  final String url;
  final bool isDefault;
  final DateTime createdAt;
  const DomainEntry({
    required this.id,
    required this.url,
    required this.isDefault,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['url'] = Variable<String>(url);
    map['is_default'] = Variable<bool>(isDefault);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  DomainEntriesCompanion toCompanion(bool nullToAbsent) {
    return DomainEntriesCompanion(
      id: Value(id),
      url: Value(url),
      isDefault: Value(isDefault),
      createdAt: Value(createdAt),
    );
  }

  factory DomainEntry.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return DomainEntry(
      id: serializer.fromJson<int>(json['id']),
      url: serializer.fromJson<String>(json['url']),
      isDefault: serializer.fromJson<bool>(json['isDefault']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'url': serializer.toJson<String>(url),
      'isDefault': serializer.toJson<bool>(isDefault),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  DomainEntry copyWith({
    int? id,
    String? url,
    bool? isDefault,
    DateTime? createdAt,
  }) => DomainEntry(
    id: id ?? this.id,
    url: url ?? this.url,
    isDefault: isDefault ?? this.isDefault,
    createdAt: createdAt ?? this.createdAt,
  );
  DomainEntry copyWithCompanion(DomainEntriesCompanion data) {
    return DomainEntry(
      id: data.id.present ? data.id.value : this.id,
      url: data.url.present ? data.url.value : this.url,
      isDefault: data.isDefault.present ? data.isDefault.value : this.isDefault,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('DomainEntry(')
          ..write('id: $id, ')
          ..write('url: $url, ')
          ..write('isDefault: $isDefault, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, url, isDefault, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is DomainEntry &&
          other.id == this.id &&
          other.url == this.url &&
          other.isDefault == this.isDefault &&
          other.createdAt == this.createdAt);
}

class DomainEntriesCompanion extends UpdateCompanion<DomainEntry> {
  final Value<int> id;
  final Value<String> url;
  final Value<bool> isDefault;
  final Value<DateTime> createdAt;
  const DomainEntriesCompanion({
    this.id = const Value.absent(),
    this.url = const Value.absent(),
    this.isDefault = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  DomainEntriesCompanion.insert({
    this.id = const Value.absent(),
    required String url,
    this.isDefault = const Value.absent(),
    this.createdAt = const Value.absent(),
  }) : url = Value(url);
  static Insertable<DomainEntry> custom({
    Expression<int>? id,
    Expression<String>? url,
    Expression<bool>? isDefault,
    Expression<DateTime>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (url != null) 'url': url,
      if (isDefault != null) 'is_default': isDefault,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  DomainEntriesCompanion copyWith({
    Value<int>? id,
    Value<String>? url,
    Value<bool>? isDefault,
    Value<DateTime>? createdAt,
  }) {
    return DomainEntriesCompanion(
      id: id ?? this.id,
      url: url ?? this.url,
      isDefault: isDefault ?? this.isDefault,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (url.present) {
      map['url'] = Variable<String>(url.value);
    }
    if (isDefault.present) {
      map['is_default'] = Variable<bool>(isDefault.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('DomainEntriesCompanion(')
          ..write('id: $id, ')
          ..write('url: $url, ')
          ..write('isDefault: $isDefault, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $DomainEntriesTable domainEntries = $DomainEntriesTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [domainEntries];
}

typedef $$DomainEntriesTableCreateCompanionBuilder =
    DomainEntriesCompanion Function({
      Value<int> id,
      required String url,
      Value<bool> isDefault,
      Value<DateTime> createdAt,
    });
typedef $$DomainEntriesTableUpdateCompanionBuilder =
    DomainEntriesCompanion Function({
      Value<int> id,
      Value<String> url,
      Value<bool> isDefault,
      Value<DateTime> createdAt,
    });

class $$DomainEntriesTableFilterComposer
    extends Composer<_$AppDatabase, $DomainEntriesTable> {
  $$DomainEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get url => $composableBuilder(
    column: $table.url,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get isDefault => $composableBuilder(
    column: $table.isDefault,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$DomainEntriesTableOrderingComposer
    extends Composer<_$AppDatabase, $DomainEntriesTable> {
  $$DomainEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get url => $composableBuilder(
    column: $table.url,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get isDefault => $composableBuilder(
    column: $table.isDefault,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$DomainEntriesTableAnnotationComposer
    extends Composer<_$AppDatabase, $DomainEntriesTable> {
  $$DomainEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get url =>
      $composableBuilder(column: $table.url, builder: (column) => column);

  GeneratedColumn<bool> get isDefault =>
      $composableBuilder(column: $table.isDefault, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$DomainEntriesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $DomainEntriesTable,
          DomainEntry,
          $$DomainEntriesTableFilterComposer,
          $$DomainEntriesTableOrderingComposer,
          $$DomainEntriesTableAnnotationComposer,
          $$DomainEntriesTableCreateCompanionBuilder,
          $$DomainEntriesTableUpdateCompanionBuilder,
          (
            DomainEntry,
            BaseReferences<_$AppDatabase, $DomainEntriesTable, DomainEntry>,
          ),
          DomainEntry,
          PrefetchHooks Function()
        > {
  $$DomainEntriesTableTableManager(_$AppDatabase db, $DomainEntriesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$DomainEntriesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$DomainEntriesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$DomainEntriesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> url = const Value.absent(),
                Value<bool> isDefault = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
              }) => DomainEntriesCompanion(
                id: id,
                url: url,
                isDefault: isDefault,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String url,
                Value<bool> isDefault = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
              }) => DomainEntriesCompanion.insert(
                id: id,
                url: url,
                isDefault: isDefault,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$DomainEntriesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $DomainEntriesTable,
      DomainEntry,
      $$DomainEntriesTableFilterComposer,
      $$DomainEntriesTableOrderingComposer,
      $$DomainEntriesTableAnnotationComposer,
      $$DomainEntriesTableCreateCompanionBuilder,
      $$DomainEntriesTableUpdateCompanionBuilder,
      (
        DomainEntry,
        BaseReferences<_$AppDatabase, $DomainEntriesTable, DomainEntry>,
      ),
      DomainEntry,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$DomainEntriesTableTableManager get domainEntries =>
      $$DomainEntriesTableTableManager(_db, _db.domainEntries);
}
