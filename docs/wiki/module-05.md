# Module 05: Sets, Epigraphs & Summary

## 1. Sublevel Sets

For a function $f : \mathbb{R}^n \to \mathbb{R}$ and $\alpha \in \mathbb{R}$, the **$\alpha$-sublevel set** is:
$$ C_\alpha := \{ x \in \text{dom } f : f(x) \le \alpha \}. $$

### 1.1 Convexity of Sublevel Sets
**Theorem:** If $f$ is convex, then every sublevel set $C_\alpha$ is a convex set.

**Proof:**
Let $x,y \in C_\alpha$ (so $f(x) \le \alpha, f(y) \le \alpha$).
$$ f(\theta x + (1-\theta)y) \le \theta f(x) + (1-\theta)f(y) \le \theta \alpha + (1-\theta)\alpha = \alpha. $$
So the convex combination is also in $C_\alpha$.

### 1.2 Quasiconvexity
The converse is false. Functions whose sublevel sets are convex but satisfy the convexity inequality are called **quasiconvex**.
*   Example: $f(x) = \sqrt{|x|}$ is quasiconvex but not convex.
*   Example: $f(x) = \log x$ (concave) is quasiconvex (sublevel sets are intervals $(0, e^\alpha]$).

## 2. Epigraphs

$$ \text{epi } f := \{ (x,t) \in \mathbb{R}^{n+1} : f(x) \le t \}. $$

### 2.1 Theorem: Epi Convex $\iff$ Function Convex

**Part 1: Convex $\Rightarrow$ Epi Convex**
Take $(x_1, t_1), (x_2, t_2) \in \text{epi } f$.
Consider convex combination $(\bar{x}, \bar{t})$.
$$ f(\bar{x}) \le \theta f(x_1) + (1-\theta)f(x_2) \le \theta t_1 + (1-\theta)t_2 = \bar{t}. $$
So $(\bar{x}, \bar{t}) \in \text{epi } f$.

**Part 2: Epi Convex $\Rightarrow$ Convex**
Take $x_1, x_2$. Then $(x_1, f(x_1))$ and $(x_2, f(x_2))$ are in $\text{epi } f$.
By convexity of epigraph:
$$ (\theta x_1 + (1-\theta)x_2, \theta f(x_1) + (1-\theta)f(x_2)) \in \text{epi } f. $$
This means:
$$ f(\theta x_1 + (1-\theta)x_2) \le \theta f(x_1) + (1-\theta)f(x_2). $$

## 3. How the Pieces Fit

We have seen convexity from multiple angles. They are different coordinates of the same object:

1.  **First-Order:** The "bowl" lies above the tangent plane.
    $$ f(y) \ge f(x) + \nabla f(x)^\top (y-x). $$

2.  **Second-Order:** The curvature is non-negative everywhere.
    $$ \nabla^2 f(x) \succeq 0. $$

3.  **Geometric:** The set of points above the graph (epigraph) is a convex set.

**The Common Motif:**
> Take 1D intuition (bowl vs tangent line) $\to$ restrict to lines $\to$ rewrite as gradient and Hessian conditions $\to$ translate back into geometric language via epigraph/sublevel sets.

If you keep that pipeline in mind, all these formulas stop being random and become a coherent framework for analysis.
