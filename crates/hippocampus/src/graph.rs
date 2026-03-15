//! Semantic graph for trace relationships.
//!
//! Tracks co-occurrence and association edges between traces.
//! Used during consolidation to merge related traces.

use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};

/// An edge in the semantic graph.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphEdge {
    pub source_id: String,
    pub target_id: String,
    pub weight: f64,
    pub edge_type: String,
    pub created_at: i64,
}

/// Add or update an edge in the semantic graph.
pub fn add_edge(conn: &Connection, edge: &GraphEdge) -> Result<()> {
    conn.execute(
        "INSERT INTO graph_edges (source_id, target_id, weight, edge_type, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5)
         ON CONFLICT(source_id, target_id) DO UPDATE SET
           weight = weight + ?3,
           edge_type = ?4",
        params![
            edge.source_id,
            edge.target_id,
            edge.weight,
            edge.edge_type,
            edge.created_at,
        ],
    )?;
    Ok(())
}

/// Get all edges from a given source node.
pub fn get_neighbors(conn: &Connection, source_id: &str) -> Result<Vec<GraphEdge>> {
    let mut stmt = conn.prepare(
        "SELECT source_id, target_id, weight, edge_type, created_at
         FROM graph_edges WHERE source_id = ?1
         ORDER BY weight DESC",
    )?;
    let rows = stmt.query_map(params![source_id], |row| {
        Ok(GraphEdge {
            source_id: row.get(0)?,
            target_id: row.get(1)?,
            weight: row.get(2)?,
            edge_type: row.get(3)?,
            created_at: row.get(4)?,
        })
    })?;
    rows.collect()
}

/// Get bidirectional neighbors (both incoming and outgoing edges).
pub fn get_all_neighbors(conn: &Connection, node_id: &str) -> Result<Vec<GraphEdge>> {
    let mut stmt = conn.prepare(
        "SELECT source_id, target_id, weight, edge_type, created_at
         FROM graph_edges WHERE source_id = ?1 OR target_id = ?1
         ORDER BY weight DESC",
    )?;
    let rows = stmt.query_map(params![node_id], |row| {
        Ok(GraphEdge {
            source_id: row.get(0)?,
            target_id: row.get(1)?,
            weight: row.get(2)?,
            edge_type: row.get(3)?,
            created_at: row.get(4)?,
        })
    })?;
    rows.collect()
}

/// Count total edges in the graph.
pub fn edge_count(conn: &Connection) -> Result<usize> {
    conn.query_row("SELECT COUNT(*) FROM graph_edges", [], |r| {
        r.get::<_, usize>(0)
    })
}

/// Count unique nodes in the graph.
pub fn node_count(conn: &Connection) -> Result<usize> {
    conn.query_row(
        "SELECT COUNT(DISTINCT id) FROM (
            SELECT source_id AS id FROM graph_edges
            UNION
            SELECT target_id AS id FROM graph_edges
         )",
        [],
        |r| r.get::<_, usize>(0),
    )
}

/// Consolidate the graph: merge weak edges, remove orphans.
pub fn consolidate(conn: &Connection, min_weight: f64) -> Result<(usize, usize)> {
    // Remove edges below minimum weight
    let _deleted = conn.execute(
        "DELETE FROM graph_edges WHERE weight < ?1",
        params![min_weight],
    )?;

    let nodes = node_count(conn)?;
    let edges = edge_count(conn)?;

    Ok((nodes, edges))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::open_memory_db;

    #[test]
    fn test_add_and_get_edge() {
        let conn = open_memory_db().unwrap();
        let edge = GraphEdge {
            source_id: "a".into(),
            target_id: "b".into(),
            weight: 1.0,
            edge_type: "association".into(),
            created_at: 1000,
        };
        add_edge(&conn, &edge).unwrap();
        let neighbors = get_neighbors(&conn, "a").unwrap();
        assert_eq!(neighbors.len(), 1);
        assert_eq!(neighbors[0].target_id, "b");
    }

    #[test]
    fn test_edge_weight_accumulates() {
        let conn = open_memory_db().unwrap();
        let edge = GraphEdge {
            source_id: "a".into(),
            target_id: "b".into(),
            weight: 1.0,
            edge_type: "association".into(),
            created_at: 1000,
        };
        add_edge(&conn, &edge).unwrap();
        add_edge(&conn, &edge).unwrap();
        let neighbors = get_neighbors(&conn, "a").unwrap();
        assert_eq!(neighbors[0].weight, 2.0);
    }

    #[test]
    fn test_consolidate_removes_weak() {
        let conn = open_memory_db().unwrap();
        add_edge(
            &conn,
            &GraphEdge {
                source_id: "a".into(),
                target_id: "b".into(),
                weight: 0.1,
                edge_type: "weak".into(),
                created_at: 1000,
            },
        )
        .unwrap();
        add_edge(
            &conn,
            &GraphEdge {
                source_id: "c".into(),
                target_id: "d".into(),
                weight: 5.0,
                edge_type: "strong".into(),
                created_at: 1000,
            },
        )
        .unwrap();
        let (nodes, edges) = consolidate(&conn, 1.0).unwrap();
        assert_eq!(edges, 1);
        assert_eq!(nodes, 2);
    }
}
