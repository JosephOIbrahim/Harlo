//! Bitwise XOR kNN search over SDR vectors.
//!
//! Rule 2: Hamming distance via XOR + POPCNT. No cosine similarity.
//! Target: <0.5ms on 100K traces.

use bitvec::prelude::*;
use std::collections::BinaryHeap;

/// Result of a trace search.
#[derive(Debug, Clone)]
pub struct TraceResult {
    /// Trace identifier
    pub trace_id: String,
    /// Hamming distance from query
    pub distance: u32,
    /// Decayed strength at query time
    pub strength: f64,
}

/// Perform kNN search using XOR + popcount over SDR vectors.
///
/// Returns the k nearest traces sorted ascending by Hamming distance.
/// Uses a bounded max-heap so the working set is O(k) and trace ids are
/// cloned only for the k survivors — not for every candidate.
pub fn xor_search(
    query: &BitVec<u8, Lsb0>,
    candidates: &[(String, Vec<u8>)],
    k: usize,
) -> Vec<TraceResult> {
    if k == 0 || candidates.is_empty() {
        return Vec::new();
    }
    let query_bytes = query.as_raw_slice();

    // Max-heap keyed by (distance, idx): peek = worst kept candidate.
    // Tuple ordering preserves stable-sort semantics on ties (smaller idx wins).
    // Cap capacity at the available candidates — k may legitimately exceed N
    // (caller asks for top-1000 but only 50 traces exist) and the
    // pop-before-push loop never grows the heap beyond `cap` anyway.
    let cap = k.min(candidates.len());
    let mut heap: BinaryHeap<(u32, usize)> = BinaryHeap::with_capacity(cap);
    for (idx, (_, sdr_bytes)) in candidates.iter().enumerate() {
        let distance = xor_popcount(query_bytes, sdr_bytes);
        if heap.len() < k {
            heap.push((distance, idx));
        } else if let Some(&(worst, _)) = heap.peek() {
            if distance < worst {
                heap.pop();
                heap.push((distance, idx));
            }
        }
    }

    heap.into_sorted_vec()
        .into_iter()
        .map(|(distance, idx)| TraceResult {
            trace_id: candidates[idx].0.clone(),
            distance,
            strength: 0.0, // Filled by caller after decay computation
        })
        .collect()
}

/// Compute Hamming distance between two byte slices via XOR + popcount.
///
/// This is the core hot-path operation. Must be as fast as possible.
#[inline]
fn xor_popcount(a: &[u8], b: &[u8]) -> u32 {
    // Process 8 bytes at a time for u64 popcount
    let chunks_a = a.chunks_exact(8);
    let chunks_b = b.chunks_exact(8);
    let remainder_a = chunks_a.remainder();
    let remainder_b = chunks_b.remainder();

    let mut total: u32 = chunks_a
        .zip(chunks_b)
        .map(|(ca, cb)| {
            let va = u64::from_le_bytes(
                ca.try_into().expect("chunks_exact(8) yields exactly 8 bytes"),
            );
            let vb = u64::from_le_bytes(
                cb.try_into().expect("chunks_exact(8) yields exactly 8 bytes"),
            );
            (va ^ vb).count_ones()
        })
        .sum();

    // Handle remaining bytes
    for (a_byte, b_byte) in remainder_a.iter().zip(remainder_b.iter()) {
        total += (a_byte ^ b_byte).count_ones();
    }

    total
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::encoder::{encode_to_sdr, sdr_to_bytes, Metadata, SDR_WIDTH};

    #[test]
    fn test_xor_search_returns_k_results() {
        let meta = Metadata::default();
        let query = encode_to_sdr("search query", &meta);

        let candidates: Vec<(String, Vec<u8>)> = (0..10)
            .map(|i| {
                let sdr = encode_to_sdr(&format!("candidate {}", i), &meta);
                (format!("trace_{}", i), sdr_to_bytes(&sdr))
            })
            .collect();

        let results = xor_search(&query, &candidates, 3);
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn test_xor_search_sorted_by_distance() {
        let meta = Metadata::default();
        let query = encode_to_sdr("hello world", &meta);

        let candidates: Vec<(String, Vec<u8>)> = vec![
            ("far".into(), sdr_to_bytes(&encode_to_sdr("quantum physics", &meta))),
            ("close".into(), sdr_to_bytes(&encode_to_sdr("hello earth", &meta))),
            ("exact".into(), sdr_to_bytes(&encode_to_sdr("hello world", &meta))),
        ];

        let results = xor_search(&query, &candidates, 3);
        assert_eq!(results[0].trace_id, "exact");
        assert_eq!(results[0].distance, 0);
        // Each subsequent should be >= previous distance
        for w in results.windows(2) {
            assert!(w[0].distance <= w[1].distance);
        }
    }

    #[test]
    fn test_xor_popcount_identity() {
        let bytes = vec![0xFF_u8; SDR_WIDTH / 8];
        assert_eq!(xor_popcount(&bytes, &bytes), 0);
    }

    #[test]
    fn test_xor_popcount_all_different() {
        let a = vec![0xFF_u8; SDR_WIDTH / 8];
        let b = vec![0x00_u8; SDR_WIDTH / 8];
        assert_eq!(xor_popcount(&a, &b), SDR_WIDTH as u32);
    }

    #[test]
    fn test_empty_candidates() {
        let query = encode_to_sdr("test", &Metadata::default());
        let results = xor_search(&query, &[], 5);
        assert!(results.is_empty());
    }

    #[test]
    fn test_k_larger_than_candidates() {
        let meta = Metadata::default();
        let query = encode_to_sdr("test", &meta);
        let candidates = vec![
            ("one".into(), sdr_to_bytes(&encode_to_sdr("one", &meta))),
        ];
        let results = xor_search(&query, &candidates, 10);
        assert_eq!(results.len(), 1);
    }
}
