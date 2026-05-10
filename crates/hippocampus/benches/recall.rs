//! Latency benchmarks for the recall path.
//!
//! The constitution sets a <2 ms hot-recall budget on 100K traces
//! (CLAUDE.md Rule 3).  Two layers of measurement here:
//!
//! 1. **`xor_search` micro-bench** — pure popcount + heap over pre-loaded
//!    candidates.  Tells us the cost of the bitwise kernel.
//! 2. **Full-pipeline benches** — `load_all_sdrs` (SQLite scan + blob
//!    read) and end-to-end `recall()` (load + search + decay + result
//!    construction).  Tells us where the real bottleneck sits.
//!
//! Optimising popcount with SIMD is wasted work if `load_all_sdrs`
//! dominates; the only way to know is to measure both.

use criterion::{criterion_group, criterion_main, BatchSize, Criterion};
use hippocampus::encoder::{encode_to_sdr, sdr_to_bytes, Metadata};
use hippocampus::query::{recall, Depth};
use hippocampus::search::xor_search;
use hippocampus::store::{load_all_sdrs, open_memory_db, store_trace, TraceRecord};

fn build_candidates(n: usize) -> Vec<(String, Vec<u8>)> {
    let meta = Metadata::default();
    (0..n)
        .map(|i| {
            let sdr = encode_to_sdr(&format!("trace candidate {i}"), &meta);
            (format!("t{i}"), sdr_to_bytes(&sdr))
        })
        .collect()
}

fn build_db(n: usize) -> rusqlite::Connection {
    let conn = open_memory_db().expect("in-memory DB");
    let meta = Metadata::default();
    for i in 0..n {
        let msg = format!("trace candidate {i}");
        let sdr = encode_to_sdr(&msg, &meta);
        let trace = TraceRecord {
            id: format!("t{i}"),
            message: msg,
            sdr_blob: sdr_to_bytes(&sdr),
            initial_strength: 1.0,
            decay_lambda: 0.05,
            created_at: 0,
            last_accessed: 0,
            boosts_json: "[]".into(),
            tags_json: "[]".into(),
            domain: None,
            source: None,
        };
        store_trace(&conn, &trace).expect("store_trace");
    }
    conn
}

// ─── xor_search micro-benches (pre-loaded candidates) ───────────────────

fn bench_recall_100k(c: &mut Criterion) {
    let candidates = build_candidates(100_000);
    let query = encode_to_sdr("hot recall query path", &Metadata::default());

    c.bench_function("xor_search 100k k=5", |b| {
        b.iter_batched(
            || (&query, candidates.as_slice()),
            |(q, c)| xor_search(q, c, 5),
            BatchSize::SmallInput,
        )
    });
}

fn bench_recall_10k(c: &mut Criterion) {
    let candidates = build_candidates(10_000);
    let query = encode_to_sdr("hot recall query path", &Metadata::default());

    c.bench_function("xor_search 10k k=5", |b| {
        b.iter_batched(
            || (&query, candidates.as_slice()),
            |(q, c)| xor_search(q, c, 5),
            BatchSize::SmallInput,
        )
    });
}

// ─── Full-pipeline benches (load + search + decay + result) ─────────────

fn bench_load_all_sdrs_100k(c: &mut Criterion) {
    let conn = build_db(100_000);
    c.bench_function("load_all_sdrs 100k", |b| {
        b.iter(|| load_all_sdrs(&conn).expect("load_all_sdrs"))
    });
}

fn bench_recall_full_10k(c: &mut Criterion) {
    let conn = build_db(10_000);
    c.bench_function("recall_full 10k k=5", |b| {
        b.iter(|| recall(&conn, "hot recall query path", Depth::Normal))
    });
}

fn bench_recall_full_100k(c: &mut Criterion) {
    let conn = build_db(100_000);
    c.bench_function("recall_full 100k k=5", |b| {
        b.iter(|| recall(&conn, "hot recall query path", Depth::Normal))
    });
}

criterion_group!(
    benches,
    bench_recall_10k,
    bench_recall_100k,
    bench_load_all_sdrs_100k,
    bench_recall_full_10k,
    bench_recall_full_100k,
);
criterion_main!(benches);
