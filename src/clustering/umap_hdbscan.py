from __future__ import annotations

import hdbscan
import matplotlib.pyplot as plt
import numpy as np
import umap


def umap_embed(
    X: np.ndarray,
    *,
    n_components: int = 2,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    metric: str = "cosine",
    random_state: int = 42,
) -> np.ndarray:
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
    )
    return reducer.fit_transform(X)


def hdbscan_labels(
    X: np.ndarray,
    *,
    min_cluster_size: int = 15,
    min_samples: int | None = None,
) -> np.ndarray:
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
    )
    return clusterer.fit_predict(X)


def plot_umap_clusters(
    coords: np.ndarray,
    labels: np.ndarray,
    *,
    alpha: float = 0.7,
    s: float = 8,
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 7))
    noise = labels == -1
    if noise.any():
        ax.scatter(coords[noise, 0], coords[noise, 1], c="0.8", s=s, alpha=alpha)
    labeled = ~noise
    if labeled.any():
        ax.scatter(
            coords[labeled, 0],
            coords[labeled, 1],
            c=labels[labeled],
            s=s,
            alpha=alpha,
            cmap="tab20",
        )
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")
    fig.tight_layout()
    # return fig
