# Module 00: Roadmap & Preliminaries

## 1. Roadmap (What We'll Unpack)

This course covers the fundamental properties of convex functions, how to recognize them, and how to construct them. We will dive deep into:

1.  **First-order condition for convexity**
    *   What it *means* geometrically and algebraically.
    *   Proof "convex $\Rightarrow$ inequality" in tiny steps.
    *   Proof "inequality $\Rightarrow$ convex".

2.  **Second-order conditions**
    *   Directional second derivatives.
    *   "Convex $\Rightarrow$ Hessian PSD" step-by-step.
    *   "Hessian PSD $\Rightarrow$ convex".

3.  **Convexity of norms and quadratics**
    *   Why norms and functions like $x \mapsto \|Ax-b\|^2$ are convex.

4.  **Log-sum-exp**
    *   Gradient, Hessian, and why the Hessian is PSD (full Cauchy–Schwarz derivation).

5.  **Sublevel sets and quasiconvexity**

6.  **Epigraphs**
    *   Why $f$ is convex iff $\text{epi}(f)$ is convex.
    *   How this recovers the inequalities.

7.  **Operations that preserve convexity**
    *   Building complex convex functions from simple ones (Max, Sup, Composition, etc.).

8.  **Important Inequalities**
    *   Jensen's inequality, AM-GM, Hölder.

---

## 2. Preliminaries & Definitions

We work in $\mathbb{R}^n$ with the usual inner product $x^\top y$ and Euclidean norm $\|x\|_2$.

### 2.1 Convex Sets
Let $C \subseteq \mathbb{R}^n$ be a **convex set**. This means:
$$ \forall x,y \in C, \quad \forall \theta \in [0,1]: \quad \theta x + (1-\theta)y \in C. $$

### 2.2 Convex Functions
A function $f : C \to \mathbb{R}$ (where $C$ is a convex domain) is **convex** if for all $x,y \in C$ and all $\theta \in [0,1]$:

$$ f(\theta x + (1-\theta) y) \le \theta f(x) + (1-\theta) f(y). $$

**Key mental image (1D):**
Take the graph of $f : \mathbb{R} \to \mathbb{R}$. For any two points $(x,f(x))$ and $(y,f(y))$, the straight line segment (chord) between them lies **above** the graph. Equivalently:
*   The graph bends "upwards".
*   Tangent lines lie **below** the graph.

### 2.3 Epigraph
The **epigraph** of $f : \mathbb{R}^n \to \mathbb{R} \cup \{+\infty\}$ is defined as:
$$ \text{epi } f := \{ (x,t) \in \mathbb{R}^{n+1} : x \in \text{dom } f, \ f(x) \le t \}. $$

This is the set of all points **above** the graph of $f$.

**Theorem:**
$f$ is convex **iff** $\text{epi } f$ is a convex set.

### 2.4 Restricting to a Line
A crucial simplification trick:
> $f : C \to \mathbb{R}$ is convex on $C$ **iff** for every line $\ell$ that intersects $C$, the 1-dimensional function $g(t) = f(x_0 + t v)$ is convex in $t$.

This allows us to prove properties in 1D and lift them to $\mathbb{R}^n$.

---

## 3. Basic Objects
*   **Function**: $f : \mathbb{R}^n \to \mathbb{R}$.
*   **Domain**: $\text{dom } f \subseteq \mathbb{R}^n$ is **convex**.
*   **Differentiable**: For each $x \in \text{dom } f$ there is a vector
    $$ \nabla f(x) = \begin{pmatrix} \partial f/\partial x_1(x) \\ \vdots \\ \partial f/\partial x_n(x) \end{pmatrix} $$
    such that
    $$ f(x+h) = f(x) + \nabla f(x)^\top h + o(\|h\|), $$
    where $o(\|h\|)/\|h\| \to 0$ as $h \to 0$.
