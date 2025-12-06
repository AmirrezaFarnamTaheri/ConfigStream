# Module 04: Inequalities

Jensen's inequality is the workhorse of convex analysis. It generalizes the definition of convexity to expected values and leads to many famous inequalities.

## 1. Jensen's Inequality

### 1.1 Finite Form
If $f$ is convex, $x_1, \dots, x_n \in \text{dom } f$, and $\theta_i \ge 0$ with $\sum \theta_i = 1$:
$$ f\left(\sum_{i=1}^n \theta_i x_i\right) \le \sum_{i=1}^n \theta_i f(x_i). $$

### 1.2 Expectation Form
If $f$ is convex and $Z$ is a random variable:
$$ f(\mathbb{E}[Z]) \le \mathbb{E}[f(Z)]. $$
"The function of the average is less than the average of the function."

## 2. The Arithmetic-Geometric Mean (AM-GM)

Consider $f(x) = -\ln x$.
*   $f'(x) = -1/x$
*   $f''(x) = 1/x^2 > 0$
So $-\ln x$ is strictly convex on $(0, \infty)$.

### 2.1 Weighted AM-GM
Apply Jensen's inequality to $-\ln x$ with points $a, b$ and weights $\theta, 1-\theta$:
$$ -\ln(\theta a + (1-\theta)b) \le \theta(-\ln a) + (1-\theta)(-\ln b). $$
Rearranging:
$$ \ln(\theta a + (1-\theta)b) \ge \theta \ln a + (1-\theta) \ln b = \ln(a^\theta b^{1-\theta}). $$
Exponentiating:
$$ \theta a + (1-\theta)b \ge a^\theta b^{1-\theta}. $$
This is the **Weighted AM-GM inequality**.

### 2.2 Standard AM-GM
For $n$ numbers $a_i$ with weights $1/n$:
$$ \frac{1}{n} \sum a_i \ge \left( \prod a_i \right)^{1/n}. $$

## 3. From AM-GM to Hölder's Inequality

### 3.1 Young's Inequality
Let $p, q > 1$ such that $1/p + 1/q = 1$.
Using weighted AM-GM with $\theta = 1/p$, $a = u^p$, $b = v^q$:
$$ \frac{1}{p} u^p + \frac{1}{q} v^q \ge (u^p)^{1/p} (v^q)^{1/q} = uv. $$
So:
$$ uv \le \frac{u^p}{p} + \frac{v^q}{q}. $$

### 3.2 Hölder's Inequality
For vectors $x, y \in \mathbb{R}^n$:
$$ \sum_{i=1}^n |x_i y_i| \le \|x\|_p \|y\|_q. $$

**Proof:**
Normalize the vectors: let $\hat{x}_i = |x_i| / \|x\|_p$ and $\hat{y}_i = |y_i| / \|y\|_q$.
Then $\sum \hat{x}_i^p = 1$ and $\sum \hat{y}_i^q = 1$.
Apply Young's inequality term-wise:
$$ \hat{x}_i \hat{y}_i \le \frac{\hat{x}_i^p}{p} + \frac{\hat{y}_i^q}{q}. $$
Summing over $i$:
$$ \sum \hat{x}_i \hat{y}_i \le \frac{1}{p}\sum \hat{x}_i^p + \frac{1}{q}\sum \hat{y}_i^q = \frac{1}{p}(1) + \frac{1}{q}(1) = 1. $$
Substituting back the definitions of $\hat{x}, \hat{y}$:
$$ \frac{\sum |x_i y_i|}{\|x\|_p \|y\|_q} \le 1. $$

## 4. Power Functions
$f(x) = x^r$ on $(0, \infty)$:
*   **Convex** if $r \ge 1$ or $r \le 0$.
*   **Concave** if $0 \le r \le 1$.

Proof via $f''(x) = r(r-1)x^{r-2}$.
