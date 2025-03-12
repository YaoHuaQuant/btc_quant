import sympy as sp

# 定义符号
x, l, k, a, x0, x1, x2, t = sp.symbols('x l k a x0 x1 x2 t', real=True, positive=True)

# 定义各函数
N = l * sp.sin((x - x2)/t)
U = 1 + sp.exp(-k*(x - x0))
V = 1 + sp.log(1 + a*(x - x1))
D = U * V
P = N / D

# 求一阶和二阶导数
P_prime = sp.diff(P, x)
P_double_prime = sp.diff(P_prime, x)

# 尽量简化结果
P_prime_simpl = sp.simplify(P_prime)
P_double_prime_simpl = sp.simplify(P_double_prime)

print("一阶导数 P'(x) =")
sp.pprint(P_prime_simpl)
print("\n二阶导数 P''(x) =")
sp.pprint(P_double_prime_simpl)
