//! 1-bit SDR (Sparse Distributed Representation) encoder.
//!
//! Converts text + metadata into a fixed-size bitvector.
//! Uses deterministic hashing (no float32, no embeddings).
//! Rule 2: All vectors MUST be 1-bit boolean arrays.

use bitvec::prelude::*;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// SDR width in bits. 2048 bits = 256 bytes.
pub const SDR_WIDTH: usize = 2048;

/// Target sparsity: ~2-5% of bits active.
const TARGET_ACTIVE_BITS: usize = 80;

/// Number of hash rounds per token for distributed activation.
const HASH_ROUNDS: usize = 3;

/// Metadata associated with a trace for encoding.
#[derive(Debug, Clone)]
pub struct Metadata {
    pub tags: Vec<String>,
    pub domain: Option<String>,
    pub source: Option<String>,
}

impl Default for Metadata {
    fn default() -> Self {
        Self {
            tags: Vec::new(),
            domain: None,
            source: None,
        }
    }
}

/// Encode a message + metadata into a 1-bit SDR bitvector.
///
/// Uses multi-round hashing of n-grams to produce a sparse
/// distributed representation. No float operations.
pub fn encode_to_sdr(message: &str, metadata: &Metadata) -> BitVec<u8, Lsb0> {
    let mut sdr = bitvec![u8, Lsb0; 0; SDR_WIDTH];

    // Tokenize: split on whitespace and punctuation
    let tokens: Vec<&str> = message
        .split(|c: char| c.is_whitespace() || c.is_ascii_punctuation())
        .filter(|t| !t.is_empty())
        .collect();

    // Encode unigrams
    for token in &tokens {
        activate_token(&mut sdr, &token.to_lowercase());
    }

    // Encode bigrams for positional context
    for window in tokens.windows(2) {
        let bigram = format!("{}_{}", window[0].to_lowercase(), window[1].to_lowercase());
        activate_token(&mut sdr, &bigram);
    }

    // Encode trigrams for deeper context
    for window in tokens.windows(3) {
        let trigram = format!(
            "{}_{}_{}",
            window[0].to_lowercase(),
            window[1].to_lowercase(),
            window[2].to_lowercase()
        );
        activate_token(&mut sdr, &trigram);
    }

    // Encode metadata tags
    for tag in &metadata.tags {
        activate_token(&mut sdr, &format!("tag:{}", tag.to_lowercase()));
    }

    // Encode domain
    if let Some(ref domain) = metadata.domain {
        activate_token(&mut sdr, &format!("domain:{}", domain.to_lowercase()));
    }

    // Encode source
    if let Some(ref source) = metadata.source {
        activate_token(&mut sdr, &format!("source:{}", source.to_lowercase()));
    }

    // Enforce sparsity: if too many bits set, keep only the most
    // deterministic ones (lowest bit indices from hashing).
    enforce_sparsity(&mut sdr);

    sdr
}

/// Activate bits for a single token using multiple hash rounds.
fn activate_token(sdr: &mut BitVec<u8, Lsb0>, token: &str) {
    for round in 0..HASH_ROUNDS {
        let mut hasher = DefaultHasher::new();
        token.hash(&mut hasher);
        round.hash(&mut hasher);
        let hash = hasher.finish();

        let bit_index = (hash as usize) % SDR_WIDTH;
        sdr.set(bit_index, true);
    }
}

/// Enforce target sparsity by trimming excess active bits.
fn enforce_sparsity(sdr: &mut BitVec<u8, Lsb0>) {
    let active_count = sdr.count_ones();
    if active_count <= TARGET_ACTIVE_BITS * 2 {
        return; // Within acceptable range
    }

    // Collect active bit indices and keep only TARGET_ACTIVE_BITS * 2
    let active_indices: Vec<usize> = sdr
        .iter()
        .enumerate()
        .filter(|(_, bit)| *bit == true)
        .map(|(i, _)| i)
        .collect();

    // Deterministic selection: keep evenly spaced bits
    let keep = TARGET_ACTIVE_BITS * 2;
    if active_indices.len() > keep {
        let step = active_indices.len() as f64 / keep as f64;
        let kept: Vec<usize> = (0..keep)
            .map(|i| active_indices[(i as f64 * step) as usize])
            .collect();

        // Clear all and re-set kept bits
        sdr.fill(false);
        for idx in kept {
            sdr.set(idx, true);
        }
    }
}

/// Compute Hamming distance between two SDR bitvectors via XOR + popcount.
/// Rule 2: Bitwise XOR only. No cosine similarity.
pub fn hamming_distance(a: &BitVec<u8, Lsb0>, b: &BitVec<u8, Lsb0>) -> u32 {
    assert_eq!(a.len(), b.len(), "SDR vectors must be same length");

    // XOR the underlying byte slices and count set bits (popcount)
    let a_bytes = a.as_raw_slice();
    let b_bytes = b.as_raw_slice();

    a_bytes
        .iter()
        .zip(b_bytes.iter())
        .map(|(a, b)| (a ^ b).count_ones())
        .sum()
}

/// Serialize a bitvec to bytes for storage.
pub fn sdr_to_bytes(sdr: &BitVec<u8, Lsb0>) -> Vec<u8> {
    sdr.as_raw_slice().to_vec()
}

/// Deserialize bytes back to a bitvec.
pub fn bytes_to_sdr(bytes: &[u8]) -> BitVec<u8, Lsb0> {
    let mut sdr = BitVec::<u8, Lsb0>::from_slice(bytes);
    sdr.resize(SDR_WIDTH, false);
    sdr
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_produces_correct_width() {
        let sdr = encode_to_sdr("hello world", &Metadata::default());
        assert_eq!(sdr.len(), SDR_WIDTH);
    }

    #[test]
    fn test_encode_is_deterministic() {
        let meta = Metadata::default();
        let a = encode_to_sdr("test message", &meta);
        let b = encode_to_sdr("test message", &meta);
        assert_eq!(a, b);
    }

    #[test]
    fn test_encode_is_sparse() {
        let sdr = encode_to_sdr("the quick brown fox", &Metadata::default());
        let active = sdr.count_ones();
        // Should be sparse: less than 10% of bits active
        assert!(active < SDR_WIDTH / 10, "Too many active bits: {}", active);
        assert!(active > 0, "No active bits");
    }

    #[test]
    fn test_similar_inputs_have_low_distance() {
        let meta = Metadata::default();
        let a = encode_to_sdr("the quick brown fox", &meta);
        let b = encode_to_sdr("the quick brown dog", &meta);
        let dist = hamming_distance(&a, &b);
        // Similar messages should have low Hamming distance
        assert!(dist < SDR_WIDTH as u32 / 4, "Distance too high: {}", dist);
    }

    #[test]
    fn test_different_inputs_have_high_distance() {
        let meta = Metadata::default();
        let a = encode_to_sdr("quantum physics equations", &meta);
        let b = encode_to_sdr("baking chocolate cake recipe", &meta);
        let c = encode_to_sdr("quantum physics equations", &meta);
        let dist_ab = hamming_distance(&a, &b);
        let dist_ac = hamming_distance(&a, &c);
        // Different messages should be more distant than identical ones
        assert!(dist_ab > dist_ac);
    }

    #[test]
    fn test_metadata_affects_encoding() {
        let mut meta = Metadata::default();
        let a = encode_to_sdr("hello", &meta);
        meta.tags.push("important".to_string());
        let b = encode_to_sdr("hello", &meta);
        assert_ne!(a, b, "Metadata should affect the encoding");
    }

    #[test]
    fn test_sdr_roundtrip() {
        let sdr = encode_to_sdr("roundtrip test", &Metadata::default());
        let bytes = sdr_to_bytes(&sdr);
        let restored = bytes_to_sdr(&bytes);
        assert_eq!(sdr, restored);
    }

    #[test]
    fn test_hamming_distance_identity() {
        let sdr = encode_to_sdr("identity", &Metadata::default());
        assert_eq!(hamming_distance(&sdr, &sdr), 0);
    }

    #[test]
    fn test_no_float32_in_sdr() {
        // Structural test: SDR is BitVec<u8>, not f32
        let sdr = encode_to_sdr("test", &Metadata::default());
        let _bytes: &[u8] = sdr.as_raw_slice(); // Compiles only if u8
    }
}
