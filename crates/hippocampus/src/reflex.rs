//! Compiled reflex cache.
//!
//! Rule 12: store_reflex REJECTS if verification_state != "verified"
//!          UNLESS is_permanent (amygdala bypass). Rule 7.
//! Rule 26: Motor reflexes skip planning, NEVER skip Basal Ganglia.
//! Rule 32: Single failure = instant de-compilation.

use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};

/// A compiled reflex pattern.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Reflex {
    pub pattern_hash: String,
    pub response: serde_json::Value,
    pub merkle_root: String,
    pub verification_state: String, // "verified" or "amygdala_bypass"
    pub is_permanent: bool,
    pub hit_count: u32,
    pub compiled: bool,
    pub success_count: u32,
}

/// Error when storing an unverified reflex.
#[derive(Debug)]
pub struct UnverifiedReflexError;

impl std::fmt::Display for UnverifiedReflexError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Cannot store reflex: verification_state must be 'verified' or reflex must be permanent (amygdala)"
        )
    }
}

impl std::error::Error for UnverifiedReflexError {}

/// Store a reflex. REJECTS unverified reflexes (Rule 12).
///
/// Only accepts:
/// - verification_state == "verified"
/// - is_permanent == true (amygdala bypass, Rule 7)
pub fn store_reflex(
    conn: &Connection,
    reflex: &Reflex,
) -> std::result::Result<String, Box<dyn std::error::Error>> {
    // Rule 12: VERIFIED-ONLY CONSOLIDATION
    if reflex.verification_state != "verified" && !reflex.is_permanent {
        return Err(Box::new(UnverifiedReflexError));
    }

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    conn.execute(
        "INSERT OR REPLACE INTO reflexes
         (pattern_hash, response_json, merkle_root, verification_state,
          is_permanent, hit_count, compiled, success_count, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![
            reflex.pattern_hash,
            reflex.response.to_string(),
            reflex.merkle_root,
            reflex.verification_state,
            reflex.is_permanent as i32,
            reflex.hit_count,
            reflex.compiled as i32,
            reflex.success_count,
            now,
        ],
    )?;

    Ok(reflex.pattern_hash.clone())
}

/// Look up a compiled reflex by pattern hash.
pub fn lookup_reflex(conn: &Connection, hash: &str) -> Result<Option<Reflex>> {
    let mut stmt = conn.prepare(
        "SELECT pattern_hash, response_json, merkle_root, verification_state,
                is_permanent, hit_count, compiled, success_count
         FROM reflexes WHERE pattern_hash = ?1 AND compiled = 1",
    )?;
    let mut rows = stmt.query_map(params![hash], |row| {
        let response_str: String = row.get(1)?;
        Ok(Reflex {
            pattern_hash: row.get(0)?,
            response: serde_json::from_str(&response_str).unwrap_or(serde_json::Value::Null),
            merkle_root: row.get(2)?,
            verification_state: row.get(3)?,
            is_permanent: row.get::<_, i32>(4)? != 0,
            hit_count: row.get::<_, u32>(5)?,
            compiled: row.get::<_, i32>(6)? != 0,
            success_count: row.get::<_, u32>(7)?,
        })
    })?;
    match rows.next() {
        Some(Ok(r)) => Ok(Some(r)),
        Some(Err(e)) => Err(e),
        None => Ok(None),
    }
}

/// Increment hit count on reflex use.
pub fn increment_hit_count(conn: &Connection, hash: &str) -> Result<()> {
    conn.execute(
        "UPDATE reflexes SET hit_count = hit_count + 1 WHERE pattern_hash = ?1",
        params![hash],
    )?;
    Ok(())
}

/// Record a successful reflex execution.
pub fn record_success(conn: &Connection, hash: &str) -> Result<()> {
    conn.execute(
        "UPDATE reflexes SET success_count = success_count + 1 WHERE pattern_hash = ?1",
        params![hash],
    )?;
    Ok(())
}

/// Rule 32: Single failure = instant de-compilation.
/// compiled=False, success_count=0. Route to Premotor for re-planning.
pub fn decompile_reflex(conn: &Connection, hash: &str) -> Result<()> {
    conn.execute(
        "UPDATE reflexes SET compiled = 0, success_count = 0 WHERE pattern_hash = ?1",
        params![hash],
    )?;
    Ok(())
}

/// List all compiled reflexes.
pub fn list_reflexes(conn: &Connection) -> Result<Vec<Reflex>> {
    let mut stmt = conn.prepare(
        "SELECT pattern_hash, response_json, merkle_root, verification_state,
                is_permanent, hit_count, compiled, success_count
         FROM reflexes ORDER BY hit_count DESC",
    )?;
    let rows = stmt.query_map([], |row| {
        let response_str: String = row.get(1)?;
        Ok(Reflex {
            pattern_hash: row.get(0)?,
            response: serde_json::from_str(&response_str).unwrap_or(serde_json::Value::Null),
            merkle_root: row.get(2)?,
            verification_state: row.get(3)?,
            is_permanent: row.get::<_, i32>(4)? != 0,
            hit_count: row.get::<_, u32>(5)?,
            compiled: row.get::<_, i32>(6)? != 0,
            success_count: row.get::<_, u32>(7)?,
        })
    })?;
    rows.collect()
}

/// Invalidate a reflex by hash.
pub fn invalidate_reflex(conn: &Connection, hash: &str) -> Result<bool> {
    let changed = conn.execute(
        "DELETE FROM reflexes WHERE pattern_hash = ?1",
        params![hash],
    )?;
    Ok(changed > 0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::open_memory_db;

    fn make_verified_reflex(hash: &str) -> Reflex {
        Reflex {
            pattern_hash: hash.to_string(),
            response: serde_json::json!({"action": "test"}),
            merkle_root: "root123".to_string(),
            verification_state: "verified".to_string(),
            is_permanent: false,
            hit_count: 0,
            compiled: true,
            success_count: 0,
        }
    }

    #[test]
    fn test_store_verified_reflex() {
        let conn = open_memory_db().unwrap();
        let reflex = make_verified_reflex("hash1");
        let result = store_reflex(&conn, &reflex);
        assert!(result.is_ok());
    }

    #[test]
    fn test_reject_unverified_reflex() {
        let conn = open_memory_db().unwrap();
        let reflex = Reflex {
            pattern_hash: "bad".to_string(),
            response: serde_json::json!({}),
            merkle_root: "root".to_string(),
            verification_state: "fixable".to_string(), // NOT verified
            is_permanent: false,
            hit_count: 0,
            compiled: true,
            success_count: 0,
        };
        let result = store_reflex(&conn, &reflex);
        assert!(result.is_err(), "Must reject unverified reflex (Rule 12)");
    }

    #[test]
    fn test_accept_permanent_amygdala_reflex() {
        let conn = open_memory_db().unwrap();
        let reflex = Reflex {
            pattern_hash: "amygdala1".to_string(),
            response: serde_json::json!({"safety": "block"}),
            merkle_root: "root".to_string(),
            verification_state: "amygdala_bypass".to_string(),
            is_permanent: true, // Amygdala bypass (Rule 7)
            hit_count: 0,
            compiled: true,
            success_count: 0,
        };
        let result = store_reflex(&conn, &reflex);
        assert!(result.is_ok(), "Permanent amygdala reflex must be accepted");
    }

    #[test]
    fn test_lookup_reflex() {
        let conn = open_memory_db().unwrap();
        store_reflex(&conn, &make_verified_reflex("lookup1")).unwrap();
        let found = lookup_reflex(&conn, "lookup1").unwrap();
        assert!(found.is_some());
        assert_eq!(found.unwrap().pattern_hash, "lookup1");
    }

    #[test]
    fn test_lookup_missing_reflex() {
        let conn = open_memory_db().unwrap();
        let found = lookup_reflex(&conn, "nonexistent").unwrap();
        assert!(found.is_none());
    }

    #[test]
    fn test_decompile_reflex_on_failure() {
        let conn = open_memory_db().unwrap();
        let mut reflex = make_verified_reflex("fail1");
        reflex.success_count = 5;
        store_reflex(&conn, &reflex).unwrap();

        // Rule 32: Single failure = instant de-compilation
        decompile_reflex(&conn, "fail1").unwrap();

        // Should not be found via lookup (compiled=0)
        let found = lookup_reflex(&conn, "fail1").unwrap();
        assert!(found.is_none(), "Decompiled reflex must not be returned");
    }

    #[test]
    fn test_invalidate_reflex() {
        let conn = open_memory_db().unwrap();
        store_reflex(&conn, &make_verified_reflex("inv1")).unwrap();
        let deleted = invalidate_reflex(&conn, "inv1").unwrap();
        assert!(deleted);
        assert!(lookup_reflex(&conn, "inv1").unwrap().is_none());
    }
}
