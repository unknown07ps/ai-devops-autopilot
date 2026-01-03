"""
Additional Database Patterns - 100 more patterns
Covers advanced MySQL, PostgreSQL, MongoDB, Redis, Elasticsearch, Cassandra
"""

from typing import List
from src.training.devops_knowledge_base import (
    IncidentPattern, PatternCategory, Severity, BlastRadius,
    Symptom, RecommendedAction
)


def get_database_patterns_batch2() -> List[IncidentPattern]:
    """100 additional database patterns"""
    patterns = []
    
    db_scenarios = [
        # MySQL advanced (231-260)
        ("db_mysql_gtid_231", "MySQL GTID Replication Error", "GTID-based replication failing", "mysql", Severity.HIGH, ["GTID", "replication", "errant"]),
        ("db_mysql_semi_sync_232", "MySQL Semi-Sync Timeout", "Semi-synchronous replication timeout", "mysql", Severity.HIGH, ["semi-sync", "timeout", "ack"]),
        ("db_mysql_group_repl_233", "MySQL Group Replication", "Group replication member issue", "mysql", Severity.CRITICAL, ["group_replication", "member"]),
        ("db_mysql_parallel_repl_234", "MySQL Parallel Replication", "Parallel replication worker error", "mysql", Severity.HIGH, ["parallel", "worker", "error"]),
        ("db_mysql_undo_log_235", "MySQL Undo Log Growth", "InnoDB undo log growing", "mysql", Severity.MEDIUM, ["undo log", "trx_rseg_history"]),
        ("db_mysql_adaptive_hash_236", "MySQL Adaptive Hash Index", "Adaptive hash index contention", "mysql", Severity.MEDIUM, ["adaptive hash", "contention"]),
        ("db_mysql_foreign_key_237", "MySQL Foreign Key Error", "Foreign key constraint failed", "mysql", Severity.MEDIUM, ["foreign key", "constraint"]),
        ("db_mysql_charset_238", "MySQL Charset Mismatch", "Character set conversion error", "mysql", Severity.MEDIUM, ["charset", "conversion", "collation"]),
        ("db_mysql_max_packet_239", "MySQL Max Packet Exceeded", "Packet too large error", "mysql", Severity.HIGH, ["max_allowed_packet", "too large"]),
        ("db_mysql_audit_log_240", "MySQL Audit Log Full", "Audit log consuming disk", "mysql", Severity.MEDIUM, ["audit log", "disk"]),
        ("db_mysql_ssl_error_241", "MySQL SSL Connection Error", "SSL/TLS connection failed", "mysql", Severity.HIGH, ["SSL", "TLS", "handshake"]),
        ("db_mysql_wait_timeout_242", "MySQL Wait Timeout", "Connection wait timeout exceeded", "mysql", Severity.LOW, ["wait_timeout", "gone away"]),
        ("db_mysql_relay_log_243", "MySQL Relay Log Space", "Relay log consuming disk space", "mysql", Severity.HIGH, ["relay log", "disk", "space"]),
        ("db_mysql_query_cache_244", "MySQL Query Cache Full", "Query cache memory exhausted", "mysql", Severity.LOW, ["query_cache", "full"]),
        ("db_mysql_table_cache_245", "MySQL Table Cache Miss", "Table cache hit rate low", "mysql", Severity.MEDIUM, ["table_open_cache", "miss"]),
        
        # PostgreSQL advanced (246-275)
        ("db_pg_archiver_246", "PostgreSQL Archiver Failed", "WAL archiver failing", "postgresql", Severity.HIGH, ["archiver", "failed", "WAL"]),
        ("db_pg_bgwriter_247", "PostgreSQL BGWriter Issues", "Background writer lagging", "postgresql", Severity.MEDIUM, ["bgwriter", "buffers", "checkpoint"]),
        ("db_pg_autovacuum_248", "PostgreSQL Autovacuum Slow", "Autovacuum not keeping up", "postgresql", Severity.MEDIUM, ["autovacuum", "wraparound"]),
        ("db_pg_index_bloat_249", "PostgreSQL Index Bloat", "Index significantly bloated", "postgresql", Severity.MEDIUM, ["index", "bloat", "reindex"]),
        ("db_pg_table_bloat_250", "PostgreSQL Table Bloat", "Table significantly bloated", "postgresql", Severity.MEDIUM, ["table", "bloat", "vacuum"]),
        ("db_pg_logical_repl_251", "PostgreSQL Logical Replication", "Logical replication lag", "postgresql", Severity.HIGH, ["logical replication", "subscription"]),
        ("db_pg_streaming_repl_252", "PostgreSQL Streaming Replication", "Streaming replication broken", "postgresql", Severity.CRITICAL, ["streaming", "wal_receiver"]),
        ("db_pg_standby_sync_253", "PostgreSQL Standby Sync", "Synchronous standby unavailable", "postgresql", Severity.CRITICAL, ["synchronous_standby", "unavailable"]),
        ("db_pg_extension_254", "PostgreSQL Extension Error", "Extension loading failed", "postgresql", Severity.MEDIUM, ["extension", "shared_preload"]),
        ("db_pg_foreign_table_255", "PostgreSQL Foreign Table", "Foreign data wrapper error", "postgresql", Severity.MEDIUM, ["foreign table", "FDW"]),
        ("db_pg_partition_256", "PostgreSQL Partition Error", "Partition constraint violation", "postgresql", Severity.MEDIUM, ["partition", "constraint"]),
        ("db_pg_sequence_257", "PostgreSQL Sequence Exhausted", "Sequence reached maxvalue", "postgresql", Severity.HIGH, ["sequence", "maxvalue", "exhausted"]),
        ("db_pg_ssl_cert_258", "PostgreSQL SSL Certificate", "SSL certificate expired", "postgresql", Severity.HIGH, ["SSL", "certificate", "expired"]),
        ("db_pg_hba_denied_259", "PostgreSQL HBA Denied", "pg_hba.conf blocking connection", "postgresql", Severity.HIGH, ["pg_hba", "no entry", "rejected"]),
        ("db_pg_role_missing_260", "PostgreSQL Role Missing", "Database role not found", "postgresql", Severity.MEDIUM, ["role", "does not exist"]),
        
        # MongoDB advanced (261-290)
        ("db_mongo_election_261", "MongoDB Election Loop", "Replica set election loop", "mongodb", Severity.CRITICAL, ["election", "stepping down"]),
        ("db_mongo_arbiter_262", "MongoDB Arbiter Unreachable", "Arbiter node unreachable", "mongodb", Severity.HIGH, ["arbiter", "unreachable"]),
        ("db_mongo_hidden_263", "MongoDB Hidden Member Lag", "Hidden member replication lag", "mongodb", Severity.MEDIUM, ["hidden", "lag", "secondary"]),
        ("db_mongo_delayed_264", "MongoDB Delayed Member", "Delayed member catching up", "mongodb", Severity.MEDIUM, ["delayed", "slaveDelay"]),
        ("db_mongo_chunk_265", "MongoDB Chunk Migration", "Chunk migration failing", "mongodb", Severity.HIGH, ["chunk", "migration", "moveChunk"]),
        ("db_mongo_balancer_266", "MongoDB Balancer Stuck", "Balancer not running", "mongodb", Severity.MEDIUM, ["balancer", "stopped"]),
        ("db_mongo_shard_key_267", "MongoDB Shard Key Violation", "Shard key update rejected", "mongodb", Severity.MEDIUM, ["shard key", "immutable"]),
        ("db_mongo_orphan_268", "MongoDB Orphan Documents", "Orphaned documents detected", "mongodb", Severity.MEDIUM, ["orphan", "documents"]),
        ("db_mongo_config_svr_269", "MongoDB Config Server", "Config server unavailable", "mongodb", Severity.CRITICAL, ["config server", "unavailable"]),
        ("db_mongo_mongos_270", "MongoDB Mongos Error", "Mongos routing error", "mongodb", Severity.HIGH, ["mongos", "routing", "error"]),
        ("db_mongo_cursor_timeout_271", "MongoDB Cursor Timeout", "Cursor idle timeout", "mongodb", Severity.LOW, ["cursor", "timeout", "killed"]),
        ("db_mongo_write_concern_272", "MongoDB Write Concern", "Write concern not satisfied", "mongodb", Severity.HIGH, ["writeConcern", "timeout"]),
        ("db_mongo_read_pref_273", "MongoDB Read Preference", "No eligible secondary for read", "mongodb", Severity.MEDIUM, ["readPreference", "no eligible"]),
        ("db_mongo_transaction_274", "MongoDB Transaction Error", "Multi-doc transaction failed", "mongodb", Severity.HIGH, ["transaction", "aborted"]),
        ("db_mongo_oplog_275", "MongoDB Oplog Size", "Oplog size insufficient", "mongodb", Severity.HIGH, ["oplog", "window", "insufficient"]),
        
        # Redis advanced (276-305)
        ("db_redis_master_link_276", "Redis Master Link Down", "Replica lost master connection", "redis", Severity.HIGH, ["master_link_status", "down"]),
        ("db_redis_partial_sync_277", "Redis Partial Sync Failed", "PSYNC failed, full sync needed", "redis", Severity.MEDIUM, ["PSYNC", "full sync"]),
        ("db_redis_buffer_limit_278", "Redis Output Buffer Limit", "Client output buffer exceeded", "redis", Severity.HIGH, ["output buffer", "limit", "exceeded"]),
        ("db_redis_sentinel_279", "Redis Sentinel Quorum", "Sentinel quorum not met", "redis", Severity.CRITICAL, ["sentinel", "quorum", "failover"]),
        ("db_redis_failover_280", "Redis Failover In Progress", "Sentinel failover ongoing", "redis", Severity.HIGH, ["failover", "in-progress"]),
        ("db_redis_cluster_state_281", "Redis Cluster State Error", "Cluster state inconsistent", "redis", Severity.CRITICAL, ["cluster", "state", "fail"]),
        ("db_redis_slot_migration_282", "Redis Slot Migration Error", "Cluster slot migration stuck", "redis", Severity.HIGH, ["slot", "migration", "stuck"]),
        ("db_redis_cluster_bus_283", "Redis Cluster Bus Error", "Cluster bus communication error", "redis", Severity.HIGH, ["cluster bus", "PFAIL", "FAIL"]),
        ("db_redis_aof_rewrite_284", "Redis AOF Rewrite Error", "AOF rewrite failing", "redis", Severity.HIGH, ["AOF", "rewrite", "error"]),
        ("db_redis_rdb_bgsave_285", "Redis RDB BGSAVE Failed", "Background save failed", "redis", Severity.HIGH, ["BGSAVE", "error", "fork"]),
        ("db_redis_maxclients_286", "Redis Max Clients", "Max clients limit reached", "redis", Severity.HIGH, ["maxclients", "limit"]),
        ("db_redis_lua_timeout_287", "Redis Lua Script Timeout", "Lua script killed for timeout", "redis", Severity.MEDIUM, ["BUSY", "Lua", "script"]),
        ("db_redis_pub_sub_288", "Redis Pub/Sub Issues", "Pub/sub channel issues", "redis", Severity.MEDIUM, ["pubsub", "channel", "overflow"]),
        ("db_redis_stream_289", "Redis Stream Consumer", "Stream consumer group error", "redis", Severity.MEDIUM, ["XREADGROUP", "NOGROUP"]),
        ("db_redis_module_290", "Redis Module Error", "Redis module loading failed", "redis", Severity.MEDIUM, ["module", "load", "error"]),
        
        # Elasticsearch (291-315)
        ("db_es_red_cluster_291", "Elasticsearch Red Cluster", "Cluster health is red", "elasticsearch", Severity.CRITICAL, ["cluster health", "red"]),
        ("db_es_yellow_cluster_292", "Elasticsearch Yellow Cluster", "Cluster health is yellow", "elasticsearch", Severity.HIGH, ["cluster health", "yellow"]),
        ("db_es_unassigned_293", "Elasticsearch Unassigned Shards", "Shards unassigned", "elasticsearch", Severity.HIGH, ["unassigned", "shards"]),
        ("db_es_relocating_294", "Elasticsearch Relocating Shards", "Shard relocation slow", "elasticsearch", Severity.MEDIUM, ["relocating", "shards"]),
        ("db_es_disk_watermark_295", "Elasticsearch Disk Watermark", "Disk watermark exceeded", "elasticsearch", Severity.HIGH, ["disk watermark", "flood stage"]),
        ("db_es_heap_pressure_296", "Elasticsearch Heap Pressure", "JVM heap pressure high", "elasticsearch", Severity.HIGH, ["heap", "gc", "pressure"]),
        ("db_es_circuit_breaker_297", "Elasticsearch Circuit Breaker", "Circuit breaker tripped", "elasticsearch", Severity.HIGH, ["circuit breaker", "tripped"]),
        ("db_es_thread_pool_298", "Elasticsearch Thread Pool", "Thread pool rejected", "elasticsearch", Severity.HIGH, ["thread_pool", "rejected"]),
        ("db_es_master_election_299", "Elasticsearch Master Election", "Master node election issue", "elasticsearch", Severity.CRITICAL, ["master", "election"]),
        ("db_es_split_brain_300", "Elasticsearch Split Brain", "Split brain detected", "elasticsearch", Severity.CRITICAL, ["split brain", "multiple masters"]),
        ("db_es_index_readonly_301", "Elasticsearch Index Readonly", "Index set to readonly", "elasticsearch", Severity.HIGH, ["readonly", "blocked"]),
        ("db_es_mapping_302", "Elasticsearch Mapping Error", "Mapping conflict", "elasticsearch", Severity.MEDIUM, ["mapping", "conflict"]),
        ("db_es_bulk_rejected_303", "Elasticsearch Bulk Rejected", "Bulk indexing rejected", "elasticsearch", Severity.HIGH, ["bulk", "rejected"]),
        ("db_es_query_timeout_304", "Elasticsearch Query Timeout", "Search query timed out", "elasticsearch", Severity.MEDIUM, ["query", "timeout"]),
        ("db_es_snapshot_305", "Elasticsearch Snapshot Failed", "Snapshot creation failed", "elasticsearch", Severity.HIGH, ["snapshot", "failed"]),
        
        # Cassandra (306-330)
        ("db_cass_node_down_306", "Cassandra Node Down", "Cassandra node unreachable", "cassandra", Severity.HIGH, ["node", "DOWN", "unreachable"]),
        ("db_cass_gossip_307", "Cassandra Gossip Issue", "Gossip protocol error", "cassandra", Severity.HIGH, ["gossip", "failure"]),
        ("db_cass_hints_308", "Cassandra Hints Full", "Hints directory full", "cassandra", Severity.HIGH, ["hints", "full", "paused"]),
        ("db_cass_compaction_309", "Cassandra Compaction Lag", "Compaction falling behind", "cassandra", Severity.MEDIUM, ["compaction", "pending"]),
        ("db_cass_tombstone_310", "Cassandra Tombstone Warning", "Too many tombstones", "cassandra", Severity.MEDIUM, ["tombstone", "threshold"]),
        ("db_cass_gc_pause_311", "Cassandra GC Pause", "Long GC pause detected", "cassandra", Severity.HIGH, ["GC", "pause", "long"]),
        ("db_cass_heap_312", "Cassandra Heap Pressure", "JVM heap under pressure", "cassandra", Severity.HIGH, ["heap", "OutOfMemory"]),
        ("db_cass_commitlog_313", "Cassandra Commitlog Full", "Commitlog disk full", "cassandra", Severity.CRITICAL, ["commitlog", "full"]),
        ("db_cass_repair_314", "Cassandra Repair Failed", "Repair operation failed", "cassandra", Severity.MEDIUM, ["repair", "failed"]),
        ("db_cass_streaming_315", "Cassandra Streaming Error", "Streaming operation failed", "cassandra", Severity.HIGH, ["streaming", "failed"]),
        ("db_cass_read_timeout_316", "Cassandra Read Timeout", "Read operation timed out", "cassandra", Severity.HIGH, ["ReadTimeoutException"]),
        ("db_cass_write_timeout_317", "Cassandra Write Timeout", "Write operation timed out", "cassandra", Severity.HIGH, ["WriteTimeoutException"]),
        ("db_cass_unavailable_318", "Cassandra Unavailable", "Not enough replicas", "cassandra", Severity.CRITICAL, ["UnavailableException"]),
        ("db_cass_schema_319", "Cassandra Schema Mismatch", "Schema versions differ", "cassandra", Severity.MEDIUM, ["schema", "mismatch"]),
        ("db_cass_bootstrap_320", "Cassandra Bootstrap Failed", "Node bootstrap failed", "cassandra", Severity.HIGH, ["bootstrap", "failed"]),
        
        # General database (321-330)
        ("db_connection_leak_321", "Database Connection Leak", "Connections not being released", "general", Severity.HIGH, ["connection", "leak"]),
        ("db_pool_contention_322", "Connection Pool Contention", "High pool wait times", "general", Severity.MEDIUM, ["pool", "contention", "wait"]),
        ("db_ssl_renewal_323", "Database SSL Renewal", "SSL certificate renewal needed", "general", Severity.HIGH, ["SSL", "certificate", "renewal"]),
        ("db_maintenance_mode_324", "Database Maintenance Mode", "Database in maintenance", "general", Severity.MEDIUM, ["maintenance", "mode"]),
        ("db_upgrade_required_325", "Database Upgrade Required", "Version upgrade needed", "general", Severity.LOW, ["upgrade", "version"]),
        ("db_license_expiry_326", "Database License Expiring", "Commercial license expiring", "general", Severity.MEDIUM, ["license", "expiring"]),
        ("db_param_change_327", "Database Parameter Change", "Parameter change requires restart", "general", Severity.LOW, ["parameter", "restart required"]),
        ("db_encryption_error_328", "Database Encryption Error", "Encryption at rest issue", "general", Severity.HIGH, ["encryption", "error"]),
        ("db_audit_failure_329", "Database Audit Failure", "Audit logging failing", "general", Severity.MEDIUM, ["audit", "logging", "failed"]),
        ("db_ha_failover_330", "Database HA Failover", "High availability failover triggered", "general", Severity.HIGH, ["failover", "HA", "switchover"]),
    ]
    
    for pid, name, desc, subcat, sev, signals in db_scenarios:
        patterns.append(IncidentPattern(
            pattern_id=pid, name=name, description=desc,
            category=PatternCategory.DATABASE, subcategory=subcat, severity=sev,
            symptoms=[Symptom("log", signals[0], "contains", True, 3.0)],
            signals=signals, root_causes=["configuration", "capacity", "hardware"],
            recommended_actions=[
                RecommendedAction("investigate", "database", 95, {}, False, 30),
                RecommendedAction("remediate", "database", 80, {}, False, 60),
            ],
            autonomous_safe=False, blast_radius=BlastRadius.MEDIUM,
            resolution_time_avg_seconds=180, tags=[subcat]
        ))
    
    return patterns
