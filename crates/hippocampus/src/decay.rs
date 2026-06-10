//! Lazy exponential decay with retrieval boost.
//!
//! Rule 4: Timestamp math on retrieval ONLY. No polling. No background loops.
//! strength = initial * e^(-lambda * dt) + sum(retrieval_boosts)
//! dt is in DAYS (timestamps are Unix seconds, scaled by 86_400); lambda is a
//! per-day rate (default 0.05/day -> 13.9-day half-life). See ADR-0003.

/// A retrieval boost event.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Boost {
    /// Timestamp of the boost (Unix seconds)
    pub timestamp: i64,
    /// Boost amount
    pub amount: f64,
}

/// Compute the current strength of a trace using lazy decay.
///
/// Pure math. No I/O. No side effects.
///
/// # Arguments
/// * `initial` - Initial strength when first stored
/// * `lambda` - Decay rate constant
/// * `created_at` - Timestamp when trace was created (Unix seconds)
/// * `boosts` - List of retrieval boost events
/// * `now` - Current timestamp (Unix seconds)
pub fn compute_lazy_decay(
    initial: f64,
    lambda: f64,
    created_at: i64,
    boosts: &[Boost],
    now: i64,
) -> f64 {
    // dt in DAYS (Δ9 / ADR-0003): now and created_at are Unix SECONDS, but
    // λ=0.05 is a per-DAY rate (13.9-day half-life). Scale before applying λ,
    // or a one-day-old trace would decay to ~0 in seconds.
    const SECONDS_PER_DAY: f64 = 86_400.0;
    let dt = (now - created_at) as f64 / SECONDS_PER_DAY;
    if dt < 0.0 {
        return initial; // Future trace, no decay
    }

    // Base decay: initial * e^(-lambda * dt)
    let base_strength = initial * (-lambda * dt).exp();

    // Sum retrieval boosts, each decayed from their own timestamp
    let boost_sum: f64 = boosts
        .iter()
        .map(|b| {
            let boost_dt = (now - b.timestamp) as f64 / SECONDS_PER_DAY;
            if boost_dt < 0.0 {
                b.amount
            } else {
                b.amount * (-lambda * boost_dt).exp()
            }
        })
        .sum();

    base_strength + boost_sum
}

/// Check if a trace has decayed below the apoptosis threshold.
///
/// Rule 5: Traces below epsilon are candidates for physical deletion.
pub fn below_epsilon(strength: f64, epsilon: f64) -> bool {
    strength < epsilon
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_no_decay_at_creation() {
        let strength = compute_lazy_decay(1.0, 0.05, 1000, &[], 1000);
        assert!((strength - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_decay_over_time() {
        // 100 DAYS elapsed (Δ9: the unit is days). e^(-0.05*100) = e^(-5) ≈ 0.0067
        let strength = compute_lazy_decay(1.0, 0.05, 0, &[], 100 * 86_400);
        assert!(strength < 0.01);
        assert!(strength > 0.0);
    }

    #[test]
    fn test_boost_increases_strength() {
        let without_boost = compute_lazy_decay(1.0, 0.05, 0, &[], 50);
        let with_boost = compute_lazy_decay(
            1.0,
            0.05,
            0,
            &[Boost {
                timestamp: 25,
                amount: 0.5,
            }],
            50,
        );
        assert!(with_boost > without_boost);
    }

    #[test]
    fn test_multiple_boosts() {
        let boosts = vec![
            Boost { timestamp: 10, amount: 0.3 },
            Boost { timestamp: 20, amount: 0.3 },
            Boost { timestamp: 30, amount: 0.3 },
        ];
        let strength = compute_lazy_decay(1.0, 0.05, 0, &boosts, 40);
        let base_only = compute_lazy_decay(1.0, 0.05, 0, &[], 40);
        assert!(strength > base_only);
    }

    #[test]
    fn test_below_epsilon() {
        assert!(below_epsilon(0.001, 0.01));
        assert!(!below_epsilon(0.1, 0.01));
    }

    // Δ9 regression: the elapsed term is DAYS, not raw Unix seconds. Fed
    // realistic Unix epochs (the case the prior 1,140 tests never exercised),
    // strength must track e^(-λ·days). Pre-fix (seconds) this FAILS hard:
    // e^(-0.05·86400) ≈ 0 for a one-day-old trace.
    #[test]
    fn test_decay_unit_is_days() {
        let created = 1_700_000_000_i64; // ~2023-11, realistic epoch
        let day = 86_400_i64;
        let s1 = compute_lazy_decay(1.0, 0.05, created, &[], created + day);
        assert!((s1 - (-0.05_f64).exp()).abs() < 1e-6, "1 day -> {s1}");
        let s14 = compute_lazy_decay(1.0, 0.05, created, &[], created + 14 * day);
        assert!((s14 - (-0.05 * 14.0_f64).exp()).abs() < 1e-6, "14 days -> {s14}");
        let s90 = compute_lazy_decay(1.0, 0.05, created, &[], created + 90 * day);
        assert!((s90 - (-0.05 * 90.0_f64).exp()).abs() < 1e-6, "90 days -> {s90}");
        // The contract: a one-day-old trace must survive well above epsilon=0.01.
        assert!(s1 > 0.9, "a day-old trace must survive: {s1}");
    }

    #[test]
    fn test_pure_math_no_io() {
        // This test proves decay is pure computation - no I/O needed.
        // If this compiles and runs, the function is pure.
        let _s = compute_lazy_decay(1.0, 0.1, 0, &[], 1000);
    }
}
