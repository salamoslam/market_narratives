from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA


def pca_explained_variance(X: np.ndarray, n_components: int = 50) -> np.ndarray:
    n = min(n_components, X.shape[0], X.shape[1])
    pca = PCA(n_components=n, random_state=42)
    pca.fit(X)
    return pca.explained_variance_ratio_


def plot_pca_variance(variance_ratio: np.ndarray) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(1, len(variance_ratio) + 1)
    ax.bar(x, variance_ratio, alpha=0.7, label="component")
    ax.plot(
        x,
        np.cumsum(variance_ratio),
        color="C1",
        marker="o",
        markersize=3,
        label="cumulative",
    )
    ax.set_xlabel("principal component")
    ax.set_ylabel("explained variance ratio")
    ax.legend()
    fig.tight_layout()
    return fig
