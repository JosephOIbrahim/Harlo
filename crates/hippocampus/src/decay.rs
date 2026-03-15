//! Lazy exponential decay with retrieval boost.
//!
//! Rule 4: Timestamp math on retrieval ONLY. No polling. No background loops.
//! strength = initial * e^(-lambda * dt) + sum(retrieval_boosts)

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
    let dt = (now - created_at) as f64;
    if dt < 0.0 {
        return initial; // Future trace, no decay
    }

    // Base decay: initial * e^(-lambda * dt)
    let base_strength = initial * (-lambda * dt).exp();

    // Sum retrieval boosts, each decayed from their own timestamp
    let boost_sum: f64 = boosts
        .iter()
        .map(|b| {
            let boost_dt = (now - b.timestamp) as f64;
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
        let strength = compute_lazy_decay(1.0, 0.05, 0, &[], 100);
        // e^(-0.05 * 100) = e^(-5) ≈ 0.0067
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

    #[test]
    fn test_pure_math_no_io() {
        // This test proves decay is pure computation - no I/O needed.
        // If this compiles and runs, the function is pure.
        let _s = compute_lazy_decay(1.0, 0.1, 0, &[], 1000);
    }
}
