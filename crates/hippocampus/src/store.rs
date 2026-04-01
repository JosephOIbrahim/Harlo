//! SQLite storage for traces and reflexes.
//!
//! Uses rusqlite with bundled SQLite. Stores SDR vectors as BLOBs.
//! Rule 2: No float32 vectors. Only 1-bit SDR blobs.
//! Rule 5: Apoptosis physically DELETEs + VACUUMs.

use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

/// A stored trace record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceRecord {
    pub id: String,
    pub message: String,
    pub sdr_blob: Vec<u8>,
    pub initial_strength: f64,
    pub decay_lambda: f64,
    pub created_at: i64,
    pub last_accessed: i64,
    pub boosts_json: String,
    pub tags_json: String,
    pub domain: Option<String>,
    pub source: Option<String>,
}

/// Apoptosis report after cleanup.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApoptosisReport {
    pub traces_deleted: usize,
    pub db_size_before: u64,
    pub db_size_after: u64,
}

/// Consolidation report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsolidationReport {
    pub traces_merged: usize,
    pub graph_nodes: usize,
    pub graph_edges: usize,
}

/// Initialize the database schema.
pub fn init_db(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS traces (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            sdr_blob BLOB NOT NULL,
            initial_strength REAL NOT NULL DEFAULT 1.0,
            decay_lambda REAL NOT NULL DEFAULT 0.05,
            created_at INTEGER NOT NULL,
            last_accessed INTEGER NOT NULL,
            boosts_json TEXT NOT NULL DEFAULT '[]',
            tags_json TEXT NOT NULL DEFAULT '[]',
            domain TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS reflexes (
            pattern_hash TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            merkle_root TEXT NOT NULL,
            verification_state TEXT NOT NULL,
            is_permanent INTEGER NOT NULL DEFAULT 0,
            hit_count INTEGER NOT NULL DEFAULT 0,
            compiled INTEGER NOT NULL DEFAULT 1,
            success_count INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS graph_edges (
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 1.0,
            edge_type TEXT NOT NULL DEFAULT 'association',
            created_at INTEGER NOT NULL,
            PRIMARY KEY (source_id, target_id)
        );

        CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);
        CREATE INDEX IF NOT EXISTS idx_traces_domain ON traces(domain);
        CREATE INDEX IF NOT EXISTS idx_graph_source ON graph_edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_graph_target ON graph_edges(target_id);
        ",
    )?;
    Ok(())
}

/// Open or create the database at the given path.
pub fn open_db(path: &Path) -> Result<Connection> {
    let conn = Connection::open(path)?;
    // Performance pragmas
    conn.execute_batch(
        "
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA cache_size=-8000;
        PRAGMA mmap_size=268435456;
        ",
    )?;
    init_db(&conn)?;
    Ok(conn)
}

/// Open an in-memory database (for testing).
pub fn open_memory_db() -> Result<Connection> {
    let conn = Connection::open_in_memory()?;
    init_db(&conn)?;
    Ok(conn)
}

/// Store a new trace.
pub fn store_trace(conn: &Connection, trace: &TraceRecord) -> Result<()> {
    conn.execute(
        "INSERT OR REPLACE INTO traces
         (id, message, sdr_blob, initial_strength, decay_lambda,
          created_at, last_accessed, boosts_json, tags_json, domain, source)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        params![
            trace.id,
            trace.message,
            trace.sdr_blob,
            trace.initial_strength,
            trace.decay_lambda,
            trace.created_at,
            trace.last_accessed,
            trace.boosts_json,
            trace.tags_json,
            trace.domain,
            trace.source,
        ],
    )?;
    Ok(())
}

/// Load all trace SDR blobs for search.
pub fn load_all_sdrs(conn: &Connection) -> Result<Vec<(String, Vec<u8>)>> {
    let mut stmt = conn.prepare("SELECT id, sdr_blob FROM traces")?;
    let rows = stmt.query_map([], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, Vec<u8>>(1)?))
    })?;
    rows.collect()
}

/// Load a single trace by ID.
pub fn load_trace(conn: &Connection, id: &str) -> Result<Option<TraceRecord>> {
    let mut stmt = conn.prepare(
        "SELECT id, message, sdr_blob, initial_strength, decay_lambda,
                created_at, last_accessed, boosts_json, tags_json, domain, source
         FROM traces WHERE id = ?1",
    )?;
    let mut rows = stmt.query_map(params![id], |row| {
        Ok(TraceRecord {
            id: row.get(0)?,
            message: row.get(1)?,
            sdr_blob: row.get(2)?,
            initial_strength: row.get(3)?,
            decay_lambda: row.get(4)?,
            created_at: row.get(5)?,
            last_accessed: row.get(6)?,
            boosts_json: row.get(7)?,
            tags_json: row.get(8)?,
            domain: row.get(9)?,
            source: row.get(10)?,
        })
    })?;
    match rows.next() {
        Some(Ok(trace)) => Ok(Some(trace)),
        Some(Err(e)) => Err(e),
        None => Ok(None),
    }
}

/// Update last_accessed and add a boost.
pub fn boost_trace(conn: &Connection, id: &str, amount: f64, now: i64) -> Result<bool> {
    // Load current boosts
    let mut stmt = conn.prepare("SELECT boosts_json FROM traces WHERE id = ?1")?;
    let boosts_json: Option<String> = stmt
        .query_row(params![id], |row| row.get(0))
        .ok();

    let Some(boosts_json) = boosts_json else {
        return Ok(false);
    };

    let mut boosts: Vec<crate::decay::Boost> =
        serde_json::from_str(&boosts_json).unwrap_or_default();
    boosts.push(crate::decay::Boost {
        timestamp: now,
        amount,
    });
    let new_boosts_json = serde_json::to_string(&boosts).unwrap_or_default();

    conn.execute(
        "UPDATE traces SET last_accessed = ?1, boosts_json = ?2 WHERE id = ?3",
        params![now, new_boosts_json, id],
    )?;
    Ok(true)
}

/// Apoptosis: DELETE traces below epsilon + VACUUM.
/// Rule 5: Physical deletion. Database file size MUST decrease.
pub fn microglia_apoptosis(
    conn: &Connection,
    epsilon: f64,
    lambda: f64,
    now: i64,
) -> Result<ApoptosisReport> {
    // We must compute decay for each trace to determine which to delete.
    // Rule 4: Lazy decay computed at retrieval/check time.
    let mut stmt = conn.prepare(
        "SELECT id, initial_strength, decay_lambda, created_at, boosts_json FROM traces",
    )?;

    let to_delete: Vec<String> = stmt
        .query_map([], |row| {
            let id: String = row.get(0)?;
            let initial: f64 = row.get(1)?;
            let trace_lambda: f64 = row.get(2)?;
            let created_at: i64 = row.get(3)?;
            let boosts_json: String = row.get(4)?;
            Ok((id, initial, trace_lambda, created_at, boosts_json))
        })?
        .filter_map(|r| r.ok())
        .filter(|(_, initial, trace_lambda, created_at, boosts_json)| {
            let boosts: Vec<crate::decay::Boost> =
                serde_json::from_str(boosts_json).unwrap_or_default();
            let effective_lambda = if *trace_lambda > 0.0 {
                *trace_lambda
            } else {
                lambda
            };
            let strength =
                crate::decay::compute_lazy_decay(*initial, effective_lambda, *created_at, &boosts, now);
            crate::decay::below_epsilon(strength, epsilon)
        })
        .map(|(id, ..)| id)
        .collect();

    let count = to_delete.len();

    // Get DB size before (for in-memory, this will be 0)
    let db_size_before: u64 = conn
        .query_row("PRAGMA page_count", [], |r| r.get::<_, i64>(0))
        .unwrap_or(0) as u64
        * conn
            .query_row("PRAGMA page_size", [], |r| r.get::<_, i64>(0))
            .unwrap_or(4096) as u64;

    for id in &to_delete {
        conn.execute("DELETE FROM traces WHERE id = ?1", params![id])?;
        // Also clean up graph edges
        conn.execute(
            "DELETE FROM graph_edges WHERE source_id = ?1 OR target_id = ?1",
            params![id],
        )?;
    }

    // VACUUM to reclaim space. Rule 5.
    conn.execute_batch("VACUUM")?;

    let db_size_after: u64 = conn
        .query_row("PRAGMA page_count", [], |r| r.get::<_, i64>(0))
        .unwrap_or(0) as u64
        * conn
            .query_row("PRAGMA page_size", [], |r| r.get::<_, i64>(0))
            .unwrap_or(4096) as u64;

    Ok(ApoptosisReport {
        traces_deleted: count,
        db_size_before,
        db_size_after,
    })
}

/// Get total trace count.
pub fn trace_count(conn: &Connection) -> Result<usize> {
    conn.query_row("SELECT COUNT(*) FROM traces", [], |r| r.get::<_, usize>(0))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::encoder::{encode_to_sdr, sdr_to_bytes, Metadata};

    fn make_trace(id: &str, message: &str, created_at: i64) -> TraceRecord {
        let sdr = encode_to_sdr(message, &Metadata::default());
        TraceRecord {
            id: id.to_string(),
            message: message.to_string(),
            sdr_blob: sdr_to_bytes(&sdr),
            initial_strength: 1.0,
            decay_lambda: 0.05,
            created_at,
            last_accessed: created_at,
            boosts_json: "[]".to_string(),
            tags_json: "[]".to_string(),
            domain: None,
            source: None,
        }
    }

    #[test]
    fn test_store_and_load_trace() {
        let conn = open_memory_db().unwrap();
        let trace = make_trace("t1", "hello world", 1000);
        store_trace(&conn, &trace).unwrap();
        let loaded = load_trace(&conn, "t1").unwrap().unwrap();
        assert_eq!(loaded.message, "hello world");
        assert_eq!(loaded.sdr_blob, trace.sdr_blob);
    }

    #[test]
    fn test_load_all_sdrs() {
        let conn = open_memory_db().unwrap();
        store_trace(&conn, &make_trace("t1", "first", 1000)).unwrap();
        store_trace(&conn, &make_trace("t2", "second", 1001)).unwrap();
        let sdrs = load_all_sdrs(&conn).unwrap();
        assert_eq!(sdrs.len(), 2);
    }

    #[test]
    fn test_boost_trace() {
        let conn = open_memory_db().unwrap();
        store_trace(&conn, &make_trace("t1", "boostable", 1000)).unwrap();
        let ok = boost_trace(&conn, "t1", 0.5, 2000).unwrap();
        assert!(ok);
        let loaded = load_trace(&conn, "t1").unwrap().unwrap();
        assert_eq!(loaded.last_accessed, 2000);
        assert!(loaded.boosts_json.contains("0.5"));
    }

    #[test]
    fn test_apoptosis_deletes_weak_traces() {
        let conn = open_memory_db().unwrap();
        // Old trace that should have decayed
        store_trace(&conn, &make_trace("old", "ancient memory", 0)).unwrap();
        // Recent trace that should survive
        store_trace(&conn, &make_trace("new", "fresh memory", 999_990)).unwrap();

        let report = microglia_apoptosis(&conn, 0.01, 0.05, 1_000_000).unwrap();
        assert!(report.traces_deleted >= 1, "Should delete decayed traces");

        // Old trace should be gone
        assert!(load_trace(&conn, "old").unwrap().is_none());
        // New trace should survive
        assert!(load_trace(&conn, "new").unwrap().is_some());
    }

    #[test]
    fn test_trace_count() {
        let conn = open_memory_db().unwrap();
        assert_eq!(trace_count(&conn).unwrap(), 0);
        store_trace(&conn, &make_trace("t1", "one", 1000)).unwrap();
        assert_eq!(trace_count(&conn).unwrap(), 1);
    }
}
