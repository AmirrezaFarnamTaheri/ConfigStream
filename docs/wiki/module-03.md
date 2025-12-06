# Module 03: Key Examples & Analysis

## 1. Convexity of Norms

Any norm $\|\cdot\|$ is convex.
**Proof:**
By the triangle inequality and homogeneity:
$$ \|\theta x + (1-\theta)y\| \le \|\theta x\| + \|(1-\theta)y\| = \theta\|x\| + (1-\theta)\|y\|. $$

## 2. Quadratic Functions

Consider $f(x) = \|Ax-b\|_2^2 = (Ax-b)^\top (Ax-b)$.

### 2.1 Gradient and Hessian
$$ f(x) = x^\top A^\top A x - 2 b^\top A x + b^\top b. $$
*   Gradient: $\nabla f(x) = 2 A^\top (Ax-b)$.
*   Hessian: $\nabla^2 f(x) = 2 A^\top A$.

### 2.2 Proof of Convexity
For any vector $v$:
$$ v^\top \nabla^2 f(x) v = v^\top (2 A^\top A) v = 2 (Av)^\top (Av) = 2 \|Av\|_2^2 \ge 0. $$
Since the Hessian is always Positive Semidefinite (PSD), $f$ is convex.

## 3. Log-Sum-Exp

Let $f(x) = \log\left(\sum_{k=1}^n e^{x_k}\right)$. This function is fundamental in machine learning (Softmax loss) and geometric programming.

### 3.1 Gradient
Let $S = \sum_k e^{x_k}$.
$$ \frac{\partial f}{\partial x_i} = \frac{1}{S} \frac{\partial S}{\partial x_i} = \frac{e^{x_i}}{S}. $$
So $\nabla f(x) = \text{softmax}(x)$.

### 3.2 Hessian
Let $z_i = e^{x_i}$. Then $\nabla f(x)_i = z_i / S$.
$$ \frac{\partial^2 f}{\partial x_j \partial x_i} = \frac{\partial}{\partial x_j} \left( \frac{z_i}{S} \right) = \frac{S \cdot z_i \delta_{ij} - z_i z_j}{S^2}. $$
In matrix form:
$$ \nabla^2 f(x) = \frac{1}{S} \text{diag}(z) - \frac{1}{S^2} z z^\top. $$

### 3.3 Proof: Hessian is PSD
We need to show $v^\top \nabla^2 f(x) v \ge 0$ for all $v$.
$$ v^\top \nabla^2 f(x) v = \frac{1}{S} \sum_i z_i v_i^2 - \frac{1}{S^2} \left( \sum_i z_i v_i \right)^2. $$
Multiply by $S^2$:
$$ S^2 v^\top \nabla^2 f(x) v = \left(\sum z_i\right) \left(\sum z_i v_i^2\right) - \left(\sum z_i v_i\right)^2. $$
Let $a_i = \sqrt{z_i} v_i$ and $b_i = \sqrt{z_i}$.
*   $\sum a_i^2 = \sum z_i v_i^2$
*   $\sum b_i^2 = \sum z_i = S$
*   $\sum a_i b_i = \sum z_i v_i$

By **Cauchy-Schwarz Inequality**: $(\sum a_i b_i)^2 \le (\sum a_i^2)(\sum b_i^2)$.
$$ \left(\sum z_i v_i\right)^2 \le \left(\sum z_i v_i^2\right) S. $$
Therefore, the Hessian quadratic form is non-negative. $f$ is convex.
