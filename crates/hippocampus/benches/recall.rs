//! Latency benchmark for the hot recall path.
//!
//! The constitution sets a <2 ms hot-recall budget on 100K traces
//! (CLAUDE.md Rule 3).  Until this benchmark existed that budget was a
//! comment in `search.rs`; now it is a measurable contract.

use criterion::{criterion_group, criterion_main, BatchSize, Criterion};
use hippocampus::encoder::{encode_to_sdr, sdr_to_bytes, Metadata};
use hippocampus::search::xor_search;

fn build_candidates(n: usize) -> Vec<(String, Vec<u8>)> {
    let meta = Metadata::default();
    (0..n)
        .map(|i| {
            let sdr = encode_to_sdr(&format!("trace candidate {i}"), &meta);
            (format!("t{i}"), sdr_to_bytes(&sdr))
        })
        .collect()
}

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

criterion_group!(benches, bench_recall_10k, bench_recall_100k);
criterion_main!(benches);
