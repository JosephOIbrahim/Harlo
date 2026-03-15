//! Full recall pipeline.
//!
//! Combines encoding, search, decay, and graph context
//! into a single recall() call. Target: <2ms hot path.
//! Rule 3: No Python in hot path.

use crate::decay::{compute_lazy_decay, Boost};
use crate::encoder::{encode_to_sdr, sdr_to_bytes, Metadata};
use crate::search::{xor_search, TraceResult};
use crate::store::{load_all_sdrs, load_trace, TraceRecord};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};

/// Depth of recall operation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Depth {
    Normal,
    Deep,
}

impl Depth {
    pub fn k(&self) -> usize {
        match self {
            Depth::Normal => 5,
            Depth::Deep => 15,
        }
    }
}

/// A single trace hit with full context.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceHit {
    pub trace_id: String,
    pub message: String,
    pub distance: u32,
    pub strength: f64,
    pub tags: Vec<String>,
    pub domain: Option<String>,
}

/// Result of a recall operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecallResult {
    /// Contextual summary (~500 tokens worth of traces)
    pub context: String,
    /// Individual trace hits
    pub traces: Vec<TraceHit>,
    /// Overall confidence (0.0 to 1.0)
    pub confidence: f64,
}

/// Full recall pipeline: encode → search → decay → build context.
///
/// This is the main entry point for the Association Engine.
/// Rule 3: <2ms hot path target.
pub fn recall(conn: &Connection, query: &str, depth: Depth) -> RecallResult {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    // 1. Encode query to SDR
    let query_sdr = encode_to_sdr(query, &Metadata::default());

    // 2. Load all SDR blobs for search
    let candidates = load_all_sdrs(conn).unwrap_or_default();

    if candidates.is_empty() {
        return RecallResult {
            context: String::new(),
            traces: Vec::new(),
            confidence: 0.0,
        };
    }

    // 3. XOR search for k nearest
    let k = depth.k();
    let search_results = xor_search(&query_sdr, &candidates, k);

    // 4. Load full traces and compute lazy decay
    let mut hits: Vec<TraceHit> = Vec::with_capacity(search_results.len());

    for result in &search_results {
        if let Ok(Some(trace)) = load_trace(conn, &result.trace_id) {
            let boosts: Vec<Boost> =
                serde_json::from_str(&trace.boosts_json).unwrap_or_default();
            let strength = compute_lazy_decay(
                trace.initial_strength,
                trace.decay_lambda,
                trace.created_at,
                &boosts,
                now,
            );

            let tags: Vec<String> =
                serde_json::from_str(&trace.tags_json).unwrap_or_default();

            hits.push(TraceHit {
                trace_id: trace.id,
                message: trace.message,
                distance: result.distance,
                strength,
                tags,
                domain: trace.domain,
            });
        }
    }

    // 5. Sort by strength (decayed), descending
    hits.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap_or(std::cmp::Ordering::Equal));

    // 6. Compute confidence
    let confidence = compute_confidence(&hits, &search_results);

    // 7. Build context string
    let context = build_context(&hits);

    RecallResult {
        context,
        traces: hits,
        confidence,
    }
}

/// Compute confidence based on search quality and trace strength.
fn compute_confidence(hits: &[TraceHit], search_results: &[TraceResult]) -> f64 {
    if hits.is_empty() || search_results.is_empty() {
        return 0.0;
    }

    // Factor 1: Best match distance (lower = better)
    let best_distance = search_results[0].distance as f64;
    let max_distance = crate::encoder::SDR_WIDTH as f64;
    let distance_score = 1.0 - (best_distance / max_distance).min(1.0);

    // Factor 2: Average strength of top hits
    let avg_strength: f64 = hits.iter().map(|h| h.strength).sum::<f64>() / hits.len() as f64;
    let strength_score = avg_strength.min(1.0);

    // Factor 3: Number of hits found
    let hit_ratio = hits.len() as f64 / search_results.len().max(1) as f64;

    // Weighted combination
    (distance_score * 0.5 + strength_score * 0.3 + hit_ratio * 0.2).min(1.0)
}

/// Build a context string from trace hits.
fn build_context(hits: &[TraceHit]) -> String {
    if hits.is_empty() {
        return String::new();
    }

    hits.iter()
        .take(10) // Cap context size
        .map(|h| {
            let domain_tag = h
                .domain
                .as_ref()
                .map(|d| format!(" [{}]", d))
                .unwrap_or_default();
            format!("- {}{} (strength: {:.3})", h.message, domain_tag, h.strength)
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Store a new trace (convenience wrapper).
pub fn store_new_trace(
    conn: &Connection,
    id: &str,
    message: &str,
    tags: &[String],
    domain: Option<&str>,
    source: Option<&str>,
) -> Result<(), Box<dyn std::error::Error>> {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let metadata = Metadata {
        tags: tags.to_vec(),
        domain: domain.map(String::from),
        source: source.map(String::from),
    };

    let sdr = encode_to_sdr(message, &metadata);

    let trace = TraceRecord {
        id: id.to_string(),
        message: message.to_string(),
        sdr_blob: sdr_to_bytes(&sdr),
        initial_strength: 1.0,
        decay_lambda: 0.05,
        created_at: now,
        last_accessed: now,
        boosts_json: "[]".to_string(),
        tags_json: serde_json::to_string(tags)?,
        domain: domain.map(String::from),
        source: source.map(String::from),
    };

    crate::store::store_trace(conn, &trace)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::open_memory_db;

    #[test]
    fn test_recall_empty_db() {
        let conn = open_memory_db().unwrap();
        let result = recall(&conn, "anything", Depth::Normal);
        assert!(result.traces.is_empty());
        assert_eq!(result.confidence, 0.0);
        assert!(result.context.is_empty());
    }

    #[test]
    fn test_recall_finds_stored_trace() {
        let conn = open_memory_db().unwrap();
        store_new_trace(&conn, "t1", "hello world greeting", &[], None, None).unwrap();
        store_new_trace(&conn, "t2", "quantum physics equation", &[], None, None).unwrap();

        let result = recall(&conn, "hello world", Depth::Normal);
        assert!(!result.traces.is_empty());
        assert!(result.confidence > 0.0);
        // The closest match should be "hello world greeting"
        assert_eq!(result.traces[0].trace_id, "t1");
    }

    #[test]
    fn test_recall_depth_affects_k() {
        let conn = open_memory_db().unwrap();
        for i in 0..20 {
            store_new_trace(
                &conn,
                &format!("t{}", i),
                &format!("trace number {}", i),
                &[],
                None,
                None,
            )
            .unwrap();
        }

        let normal = recall(&conn, "trace", Depth::Normal);
        let deep = recall(&conn, "trace", Depth::Deep);
        assert!(deep.traces.len() >= normal.traces.len());
    }

    #[test]
    fn test_recall_returns_context() {
        let conn = open_memory_db().unwrap();
        store_new_trace(&conn, "t1", "important fact about memory", &[], None, None).unwrap();
        let result = recall(&conn, "memory", Depth::Normal);
        assert!(!result.context.is_empty());
        assert!(result.context.contains("important fact"));
    }

    #[test]
    fn test_confidence_range() {
        let conn = open_memory_db().unwrap();
        store_new_trace(&conn, "t1", "test data", &[], None, None).unwrap();
        let result = recall(&conn, "test", Depth::Normal);
        assert!(result.confidence >= 0.0);
        assert!(result.confidence <= 1.0);
    }
}
