import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st
from typing import List, Dict, Set, Tuple, Optional

COLOR_COMPLETED = "#0b7f71"
COLOR_ELIGIBLE = "#16315a"
COLOR_BLOCKED = "#e2e8f0"
TEXT_ON_DARK = "#ffffff"
TEXT_ON_LIGHT = "#0b1f3a"


def build_graph(courses: List[Dict]) -> nx.DiGraph:
    G = nx.DiGraph()
    for c in courses:
        G.add_node(c['code'], name=c['name'], credits=c['credits'])
    for c in courses:
        for pre in c['prereqs']:
            if G.has_node(pre):
                G.add_edge(pre, c['code'])
    return G


def detect_cycle(G: nx.DiGraph) -> bool:
    try:
        cycles = list(nx.find_cycle(G, orientation='original'))
        return len(cycles) > 0
    except nx.exception.NetworkXNoCycle:
        return False


def find_cycle_path(G: nx.DiGraph) -> Optional[List[str]]:
    """Return one cycle as a list of codes (first == last), or None."""
    try:
        edges = nx.find_cycle(G, orientation='original')
    except nx.exception.NetworkXNoCycle:
        return None
    path = [e[0] for e in edges]
    path.append(edges[-1][1])
    return path


def get_eligible_courses(courses: List[Dict], completed: Set[str]) -> List[Dict]:
    eligible = []
    for c in courses:
        if c['code'] in completed:
            continue
        if all(p in completed for p in c['prereqs']):
            eligible.append(c)
    return eligible


def get_missing_prereqs(course: Dict, completed: Set[str]) -> List[str]:
    return [p for p in course['prereqs'] if p not in completed]


def hasse_graph(G: nx.DiGraph) -> nx.DiGraph:
    """Transitive reduction: keeps an edge u->v only if there is no longer
    path from u to v. Defined only for acyclic graphs."""
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError('Circular prerequisite detected')
    return nx.transitive_reduction(G)


def redundant_edges(G: nx.DiGraph, H: nx.DiGraph) -> List[Tuple[str, str]]:
    """Edges of G that are implied by a longer path (absent from the Hasse diagram)."""
    return sorted(set(G.edges()) - set(H.edges()))


def layered_positions(G: nx.DiGraph) -> Dict[str, Tuple[float, float]]:
    """Left-to-right layered layout: layer = length of the longest prerequisite chain
    leading to the course. Falls back to a spring layout if the graph has a cycle."""
    if not nx.is_directed_acyclic_graph(G):
        return nx.spring_layout(G, seed=42)
    layer: Dict[str, int] = {}
    for n in nx.topological_sort(G):
        layer[n] = max((layer[p] + 1 for p in G.predecessors(n)), default=0)
    layers: Dict[int, List[str]] = {}
    for n, l in layer.items():
        layers.setdefault(l, []).append(n)
    order = {n: i for i, n in enumerate(G.nodes())}
    y: Dict[str, float] = {}
    pos: Dict[str, Tuple[float, float]] = {}
    for l in sorted(layers):
        nodes = layers[l]
        if l == 0:
            nodes.sort(key=lambda n: order[n])
        else:
            def bary(n):
                preds = list(G.predecessors(n))
                return (sum(y[p] for p in preds) / len(preds), order[n])
            nodes.sort(key=bary)
        for i, n in enumerate(nodes):
            y[n] = (len(nodes) - 1) / 2 - i
            pos[n] = (float(l), y[n])
    return pos


def make_figure(G: nx.DiGraph, completed: Set[str], eligible: List[Dict],
                hasse: bool = False, compact: bool = False):
    elig_codes = {c['code'] for c in eligible}
    H = hasse_graph(G) if hasse else G
    pos = layered_positions(G)

    n_layers = int(max(x for x, _ in pos.values())) + 1 if pos else 1
    max_rows = max(1, len({round(y, 3) for _, y in pos.values()}))
    if compact:
        figsize = (max(5.5, 1.5 * n_layers), max(3.2, 0.7 * max_rows + 1))
    else:
        figsize = (max(8, 2.1 * n_layers), max(4.2, 1.0 * max_rows + 1.5))

    fig, ax = plt.subplots(figsize=figsize)
    maxlen = max(len(str(n)) for n in G.nodes())
    base = 650 if compact else 1150
    node_size = base + 130 * max(0, maxlen - 3)

    nx.draw_networkx_edges(
        H, pos, ax=ax, arrows=True, arrowstyle='-|>', arrowsize=12 if compact else 16,
        edge_color='#8a99ad', width=1.1, node_size=node_size,
        connectionstyle='arc3,rad=0.08',
    )
    face = []
    for node in G.nodes():
        if node in completed:
            face.append(COLOR_COMPLETED)
        elif node in elig_codes:
            face.append(COLOR_ELIGIBLE)
        else:
            face.append(COLOR_BLOCKED)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=face, node_size=node_size,
                           edgecolors='#0b1f3a', linewidths=0.9)
    for node, color in zip(G.nodes(), face):
        x, y = pos[node]
        ax.text(x, y, str(node), ha='center', va='center',
                fontsize=7.5 if compact else 10, fontweight='bold',
                color=TEXT_ON_LIGHT if color == COLOR_BLOCKED else TEXT_ON_DARK)
    ax.axis('off')
    ax.margins(0.12)
    fig.patch.set_facecolor('white')
    fig.tight_layout(pad=0.4)
    return fig


def draw_graph(G: nx.DiGraph, completed: Set[str], eligible: List[Dict],
               hasse: bool = False, compact: bool = False):
    if G.number_of_nodes() == 0:
        st.info("No courses to display.")
        return
    fig = make_figure(G, completed, eligible, hasse=hasse, compact=compact)
    st.pyplot(fig)
    plt.close(fig)