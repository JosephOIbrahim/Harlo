//! Hippocampus — Association Engine for the Cognitive Twin.
//!
//! Rust hot path via PyO3. 1-bit SDR vectors. Bitwise XOR search.
//! Lazy decay. Physical apoptosis. Compiled reflex cache.

pub mod decay;
pub mod encoder;
pub mod graph;
pub mod query;
pub mod reflex;
pub mod search;
pub mod store;

use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::PathBuf;
use std::sync::Mutex;

static DB_PATH: Mutex<Option<PathBuf>> = Mutex::new(None);

fn get_or_open_db(path: Option<&str>) -> PyResult<rusqlite::Connection> {
    let db_path = if let Some(p) = path {
        PathBuf::from(p)
    } else {
        let guard = DB_PATH.lock().map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Lock error: {}", e))
        })?;
        guard
            .clone()
            .unwrap_or_else(|| PathBuf::from("data/twin.db"))
    };

    store::open_db(&db_path)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("DB error: {}", e)))
}

#[pyfunction]
#[pyo3(signature = (query_str, depth = "normal", db_path = None))]
fn py_recall<'py>(py: Python<'py>, query_str: &str, depth: &str, db_path: Option<&str>) -> PyResult<Bound<'py, PyDict>> {
    let depth = match depth {
        "deep" => query::Depth::Deep,
        _ => query::Depth::Normal,
    };

    let conn = get_or_open_db(db_path)?;
    let result = query::recall(&conn, query_str, depth);

    let dict = PyDict::new(py);
    dict.set_item("context", &result.context)?;
    dict.set_item("confidence", result.confidence)?;

    let traces_list = pyo3::types::PyList::empty(py);
    for t in &result.traces {
        let d = PyDict::new(py);
        d.set_item("trace_id", &t.trace_id)?;
        d.set_item("message", &t.message)?;
        d.set_item("distance", t.distance)?;
        d.set_item("strength", t.strength)?;
        d.set_item("tags", &t.tags)?;
        d.set_item("domain", &t.domain)?;
        traces_list.append(d)?;
    }
    dict.set_item("traces", traces_list)?;

    Ok(dict)
}

#[pyfunction]
#[pyo3(signature = (trace_id, message, tags = None, domain = None, source = None, db_path = None))]
fn py_store_trace(
    trace_id: &str,
    message: &str,
    tags: Option<Vec<String>>,
    domain: Option<&str>,
    source: Option<&str>,
    db_path: Option<&str>,
) -> PyResult<()> {
    let conn = get_or_open_db(db_path)?;
    let tags = tags.unwrap_or_default();
    query::store_new_trace(&conn, trace_id, message, &tags, domain, source)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Store error: {}", e)))
}

#[pyfunction]
#[pyo3(signature = (epsilon = 0.01, db_path = None))]
fn py_microglia<'py>(py: Python<'py>, epsilon: f64, db_path: Option<&str>) -> PyResult<Bound<'py, PyDict>> {
    let conn = get_or_open_db(db_path)?;
    let report = store::microglia_apoptosis(&conn, epsilon, 0.05, now_unix())
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Apoptosis error: {}", e)))?;

    let dict = PyDict::new(py);
    dict.set_item("traces_deleted", report.traces_deleted)?;
    dict.set_item("db_size_before", report.db_size_before)?;
    dict.set_item("db_size_after", report.db_size_after)?;
    Ok(dict)
}

#[pyfunction]
#[pyo3(signature = (min_weight = 0.5, db_path = None))]
fn py_consolidate<'py>(py: Python<'py>, min_weight: f64, db_path: Option<&str>) -> PyResult<Bound<'py, PyDict>> {
    let conn = get_or_open_db(db_path)?;
    let (nodes, edges) = graph::consolidate(&conn, min_weight)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Consolidate error: {}", e)))?;

    let dict = PyDict::new(py);
    dict.set_item("graph_nodes", nodes)?;
    dict.set_item("graph_edges", edges)?;
    Ok(dict)
}

#[pyfunction]
#[pyo3(signature = (pattern_hash, db_path = None))]
fn py_lookup_reflex<'py>(py: Python<'py>, pattern_hash: &str, db_path: Option<&str>) -> PyResult<Py<PyAny>> {
    let conn = get_or_open_db(db_path)?;
    let result = reflex::lookup_reflex(&conn, pattern_hash)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Lookup error: {}", e)))?;

    match result {
        Some(r) => {
            let dict = PyDict::new(py);
            dict.set_item("pattern_hash", &r.pattern_hash)?;
            dict.set_item("response", r.response.to_string())?;
            dict.set_item("merkle_root", &r.merkle_root)?;
            dict.set_item("verification_state", &r.verification_state)?;
            dict.set_item("is_permanent", r.is_permanent)?;
            dict.set_item("hit_count", r.hit_count)?;
            dict.set_item("compiled", r.compiled)?;
            dict.set_item("success_count", r.success_count)?;
            Ok(dict.into_pyobject(py)?.into_any().unbind())
        }
        None => Ok(py.None()),
    }
}

#[pyfunction]
#[pyo3(signature = (pattern_hash, response_json, merkle_root, verification_state, is_permanent = false, db_path = None))]
fn py_store_reflex(
    pattern_hash: &str,
    response_json: &str,
    merkle_root: &str,
    verification_state: &str,
    is_permanent: bool,
    db_path: Option<&str>,
) -> PyResult<String> {
    let conn = get_or_open_db(db_path)?;
    let response: serde_json::Value = serde_json::from_str(response_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid JSON: {}", e)))?;

    let r = reflex::Reflex {
        pattern_hash: pattern_hash.to_string(),
        response,
        merkle_root: merkle_root.to_string(),
        verification_state: verification_state.to_string(),
        is_permanent,
        hit_count: 0,
        compiled: true,
        success_count: 0,
    };

    reflex::store_reflex(&conn, &r)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("{}", e)))
}

#[pyfunction]
#[pyo3(signature = (trace_id, amount = 0.1, db_path = None))]
fn py_boost(trace_id: &str, amount: f64, db_path: Option<&str>) -> PyResult<bool> {
    let conn = get_or_open_db(db_path)?;
    store::boost_trace(&conn, trace_id, amount, now_unix())
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Boost error: {}", e)))
}

fn now_unix() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

#[pymodule]
fn hippocampus(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_recall, m)?)?;
    m.add_function(wrap_pyfunction!(py_store_trace, m)?)?;
    m.add_function(wrap_pyfunction!(py_microglia, m)?)?;
    m.add_function(wrap_pyfunction!(py_consolidate, m)?)?;
    m.add_function(wrap_pyfunction!(py_lookup_reflex, m)?)?;
    m.add_function(wrap_pyfunction!(py_store_reflex, m)?)?;
    m.add_function(wrap_pyfunction!(py_boost, m)?)?;
    Ok(())
}
