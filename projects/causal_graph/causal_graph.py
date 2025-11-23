"""
Causal graph builder for credit-score domain.

The graph follows Phase 1 requirement:
    - Define causal nodes and CAUSES relationships.
    - Provide utilities to render / print key values.

Usage:
    python projects/causal_graph/causal_graph.py --render
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, List, Tuple

import networkx as nx

try:
    import plotly.graph_objects as go
except ImportError:  # pragma: no cover - optional dependency for rendering
    go = None


@dataclass(frozen=True)
class CausalNode:
    key: str
    label: str
    importance: float
    description: str


CAUSAL_NODES: List[CausalNode] = [
    CausalNode("Annual_Income", "Annual Income", 0.8, "Thu nhập hàng năm lớn giúp giảm rủi ro tín dụng."),
    CausalNode("Outstanding_Debt", "Outstanding Debt", 0.7, "Nợ hiện tại cao làm tăng áp lực tài chính."),
    CausalNode("DTI_Ratio", "Debt-to-Income Ratio", 0.9, "Tỷ lệ nợ trên thu nhập là chỉ báo quan trọng nhất."),
    CausalNode("Credit_Utilization_Ratio", "Credit Utilization", 0.85, "Tỷ lệ sử dụng hạn mức tín dụng."),
    CausalNode("Num_of_Loan", "Number of Loans", 0.6, "Nhiều khoản vay cho thấy mức độ tận dụng tín dụng."),
    CausalNode("Num_of_Delayed_Payment", "Delayed Payments", 0.95, "Các lần trả trễ ảnh hưởng mạnh đến điểm."),
    CausalNode("Credit_History_Age", "Credit History Age", 0.5, "Thời gian tín dụng càng dài, càng tin cậy."),
    CausalNode("Payment_Behaviour", "Payment Behaviour", 0.65, "Thói quen tiêu dùng cho biết hành vi chi tiêu."),
    CausalNode("Credit_Risk", "Credit Risk", 0.92, "Rủi ro tổng thể dựa trên các biến đầu vào."),
    CausalNode("Credit_Score", "Credit Score", 1.0, "Điểm tín dụng đầu ra."),
]

CAUSE_RELATIONS: List[Tuple[str, str, float]] = [
    ("Annual_Income", "DTI_Ratio", -0.8),
    ("Outstanding_Debt", "DTI_Ratio", 0.8),
    ("Outstanding_Debt", "Credit_Utilization_Ratio", 0.7),
    ("Num_of_Loan", "Credit_Utilization_Ratio", 0.5),
    ("Credit_Utilization_Ratio", "Credit_Risk", 0.8),
    ("DTI_Ratio", "Credit_Risk", 0.9),
    ("Num_of_Delayed_Payment", "Credit_Risk", 0.95),
    ("Payment_Behaviour", "Credit_Risk", 0.7),
    ("Credit_History_Age", "Credit_Risk", -0.5),
    ("Credit_Risk", "Credit_Score", -0.95),
]


def build_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in CAUSAL_NODES:
        graph.add_node(node.key, label=node.label, importance=node.importance, description=node.description)
    for source, target, weight in CAUSE_RELATIONS:
        graph.add_edge(source, target, weight=weight)
    return graph


def print_key_values(graph: nx.DiGraph) -> None:
    print("=== Causal Nodes ===")
    for node in CAUSAL_NODES:
        print(f"{node.label} (key={node.key}) → importance={node.importance}, desc={node.description}")
    print("\n=== Edges (CAUSES) ===")
    for source, target, data in graph.edges(data=True):
        weight = data.get("weight")
        influence = "positive" if weight >= 0 else "negative"
        print(f"{source} -> {target} (weight={weight}, {influence})")


def plot_graph(graph: nx.DiGraph, output_path: str | None = None) -> None:
    if go is None:
        print("Plotly không được cài đặt. Bỏ qua bước render.")
        return

    pos = nx.spring_layout(graph, seed=42)
    edge_x = []
    edge_y = []
    for source, target in graph.edges():
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_x = []
    node_y = []
    text = []
    size = []
    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        data = graph.nodes[node]
        text.append(f"{data['label']}<br>Importance: {data['importance']}")
        size.append(20 + data["importance"] * 20)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[graph.nodes[n]["label"] for n in graph.nodes()],
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            showscale=False,
            color="#1f77b4",
            size=size,
            line_width=2,
        ),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="Causal Graph for Credit Score",
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
    )
    if output_path:
        fig.write_html(output_path)
        print(f"Đã lưu biểu đồ causal graph tại {output_path}")
    else:
        fig.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and display causal graph.")
    parser.add_argument("--render", action="store_true", help="Hiển thị biểu đồ bằng Plotly")
    parser.add_argument("--output", type=str, default=None, help="Đường dẫn lưu HTML nếu render.")
    args = parser.parse_args()

    graph = build_graph()
    print_key_values(graph)
    if args.render:
        plot_graph(graph, args.output)


if __name__ == "__main__":
    main()
