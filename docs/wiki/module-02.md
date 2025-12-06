# Module 02: Operations that Preserve Convexity

We can build complex convex functions from simpler ones using a toolbox of convexity-preserving operations. This is often easier than checking the definition or Hessian.

## 1. Nonnegative Weighted Sum

Let $f_1, \dots, f_m$ be convex functions and $\alpha_1, \dots, \alpha_m \ge 0$. Then:
$$ f(x) = \sum_{i=1}^m \alpha_i f_i(x) $$
is convex.

**Proof:**
$$ \sum \alpha_i f_i(\theta x + (1-\theta)y) \le \sum \alpha_i [\theta f_i(x) + (1-\theta)f_i(y)] = \theta f(x) + (1-\theta)f(y). $$

## 2. Composition with Affine Map

Let $g : \mathbb{R}^m \to \mathbb{R}$ be convex, and $A \in \mathbb{R}^{m \times n}, b \in \mathbb{R}^m$. Then:
$$ f(x) = g(Ax + b) $$
is convex.

**Proof:**
The affine map preserves straight lines.
$$ g(A(\theta x + (1-\theta)y) + b) = g(\theta(Ax+b) + (1-\theta)(Ay+b)) \le \theta g(Ax+b) + (1-\theta)g(Ay+b). $$

**Example:** Norm of an affine function $f(x) = \|Ax+b\|$ is convex because norms are convex.

## 3. Pointwise Maximum

Let $f_1, \dots, f_m$ be convex. Define:
$$ f(x) = \max_{i=1,\dots,m} f_i(x). $$
Then $f$ is convex.

**Geometric Intuition:** The intersection of convex epigraphs is convex.
$$ \text{epi } f = \bigcap_{i=1}^m \text{epi } f_i. $$

**Algebraic Proof:**
$$ f(\theta x + (1-\theta)y) = \max_i f_i(\dots) \le \max_i (\theta f_i(x) + (1-\theta)f_i(y)) \le \theta \max_i f_i(x) + (1-\theta)\max_i f_i(y). $$

### Example: Piecewise-Linear Functions
$$ f(x) = \max_{i} (a_i^\top x + b_i) $$
is convex.

### Example: Sum of $r$ Largest Components
$f(x) = x_{[1]} + \dots + x_{[r]}$ is convex because it can be written as the maximum of all sums of $r$ components (max over linear functions).

## 4. Pointwise Supremum

Let $f(x,y)$ be convex in $x$ for each $y \in \mathcal{A}$. Define:
$$ g(x) = \sup_{y \in \mathcal{A}} f(x,y). $$
Then $g$ is convex.

### Example: Support Function
$S_C(x) = \sup_{y \in C} y^\top x$ is convex (sup of linear functions).

### Example: Maximum Eigenvalue
$\lambda_{\max}(X) = \sup_{\|y\|=1} y^\top X y$.
For fixed $y$, $X \mapsto y^\top X y$ is linear in $X$. Thus $\lambda_{\max}$ is convex on symmetric matrices.

## 5. Partial Minimization

Let $f(x,y)$ be **jointly convex** in $(x,y)$ and $C$ be a convex set. Define:
$$ g(x) = \inf_{y \in C} f(x,y). $$
Then $g$ is convex.

**Geometric Picture:**
The epigraph of $g$ is the **projection** of the epigraph of $f$ (restricted to $y \in C$) onto the $(x,t)$ space. Projections of convex sets are convex.

### Example: Distance to a Convex Set
$d(x, S) = \inf_{y \in S} \|x-y\|$.
$f(x,y) = \|x-y\|$ is convex (norm of affine). $S$ is convex. So $d(x,S)$ is convex.

### Example: Schur Complement
$f(x,y) = x^\top A x + 2 x^\top B y + y^\top C y$ with $\begin{bmatrix} A & B \\ B^\top & C \end{bmatrix} \succeq 0$.
Minimizing over $y$ yields $g(x) = x^\top (A - B C^{-1} B^\top) x$.
Convexity of $g$ implies $A - B C^{-1} B^\top \succeq 0$.

## 6. What Doesn't Preserve Convexity?
*   **Minimum** of convex functions is **NOT** generally convex (e.g., lower envelope of two parabolas).
