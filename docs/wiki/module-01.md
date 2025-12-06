# Module 01: First & Second Order Conditions

## 1. First-Order Condition

### 1.1 The Inequality
For a differentiable function $f$ with a convex domain, the first-order condition states:

> $f$ is convex $\iff$ $f(y) \ge f(x) + \nabla f(x)^\top (y-x) \quad \forall x,y \in \text{dom } f$.

**Interpretation at a fixed point $x$:**
*   The function $\ell_x(y) := f(x) + \nabla f(x)^\top (y-x)$ is an **affine** function of $y$.
*   Its graph is a hyperplane tangent to the graph of $f$ at point $(x,f(x))$.
*   The inequality says **for every other $y$**, the true value $f(y)$ is above that plane.
*   "The bowl lies above the tangent line everywhere."

### 1.2 Proof: Convex $\Rightarrow$ First-Order Inequality

We use the idea "convex along every line".

**Step 1: Restrict $f$ to a line.**
Fix $x,y \in \text{dom } f$. Define direction $v := y-x$ and a 1-D function:
$$ g(t) := f(x + t v). $$
Since $\text{dom } f$ is convex, $g$ is defined on $[0,1]$.

**Step 2: $g$ is convex.**
By convexity of $f$, for any $u, w$ on the line and $\theta \in [0,1]$:
$$ g(\theta t_1 + (1-\theta)t_2) \le \theta g(t_1) + (1-\theta)g(t_2). $$
So $g$ is a convex function of a single variable.

**Step 3: 1-D convex + differentiable $\Rightarrow$ tangent line is under graph.**
Standard 1D calculus:
$$ g(b) \ge g(a) + g'(a)(b-a) \quad \forall a,b. $$
(The slope of the secant is nondecreasing).

**Step 4: Apply to $g(t)$.**
Use $a=0, b=1$.
$$ g(1) \ge g(0) + g'(0)(1-0). $$
*   $g(1) = f(y)$
*   $g(0) = f(x)$
*   $g'(0) = \nabla f(x)^\top (y-x)$ (Chain rule)

Thus:
$$ f(y) \ge f(x) + \nabla f(x)^\top (y-x). $$

### 1.3 Proof: First-Order Inequality $\Rightarrow$ Convex

Assume $f(y) \ge f(x) + \nabla f(x)^\top (y-x)$ for all $x,y$. We want to show convexity.

Let $z := \theta x + (1-\theta) y$ for $\theta \in [0,1]$.

**Step 1:** Apply inequality with base $z$, target $x$:
$$ f(x) \ge f(z) + \nabla f(z)^\top (x-z). \quad (1) $$

**Step 2:** Apply inequality with base $z$, target $y$:
$$ f(y) \ge f(z) + \nabla f(z)^\top (y-z). \quad (2) $$

**Step 3:** Take convex combination.
Multiply (1) by $\theta$ and (2) by $(1-\theta)$ and add:
$$ \theta f(x) + (1-\theta) f(y) \ge f(z) + \nabla f(z)^\top [\theta(x-z) + (1-\theta)(y-z)]. $$
The term in brackets is:
$$ \theta x - \theta z + y - \theta y - z + \theta z = \theta x + (1-\theta)y - z = z - z = 0. $$
So:
$$ \theta f(x) + (1-\theta) f(y) \ge f(z) = f(\theta x + (1-\theta)y). $$
This is the definition of convexity.

---

## 2. Second-Order Conditions

Now assume $f : \mathbb{R}^n \to \mathbb{R}$ is **twice differentiable**.
*   Gradient: $\nabla f(x) \in \mathbb{R}^n$.
*   Hessian: $\nabla^2 f(x) \in \mathbb{R}^{n \times n}$, with entries $(\nabla^2 f(x))_{ij} = \frac{\partial^2 f}{\partial x_i \partial x_j}$.

### 2.1 Statement of the Theorem
Assume $\text{dom } f$ is convex and open.
1.  $f$ is convex **iff** $\nabla^2 f(x) \succeq 0$ for all $x$ (Hessian is Positive Semidefinite).
    $$ v^\top \nabla^2 f(x) v \ge 0 \quad \forall v \in \mathbb{R}^n. $$
2.  If $\nabla^2 f(x) \succ 0$ (Positive Definite) for all $x$, then $f$ is **strictly convex**.

### 2.2 Directional Second Derivatives
For direction $v$, let $g(t) := f(x+tv)$.
*   $g'(t) = \nabla f(x+tv)^\top v$.
*   $g''(t) = v^\top \nabla^2 f(x+tv) v$.

This links the Hessian to curvature along lines.

### 2.3 Proof: Convex $\Rightarrow$ Hessian PSD
If $f$ is convex, then $g(t)$ is convex.
For 1D functions, convex $\Rightarrow$ $g''(t) \ge 0$.
At $t=0$:
$$ g''(0) = v^\top \nabla^2 f(x) v \ge 0. $$
Since this holds for any $v$, $\nabla^2 f(x) \succeq 0$.

### 2.4 Proof: Hessian PSD $\Rightarrow$ Convex
If $\nabla^2 f(x) \succeq 0$ everywhere, then for any line:
$$ g''(t) = v^\top \nabla^2 f(x+tv) v \ge 0. $$
So every line restriction is convex.
Since $f$ is convex along every line, $f$ is convex.
