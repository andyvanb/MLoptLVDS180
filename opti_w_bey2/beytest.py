from hyperopt import hp, tpe, fmin



def opttry(x):
    return x ** 2

y = hp.uniform('x', -10, 10)
print(y)
# Single line bayesian optimization of polynomial function
best = fmin(fn=opttry,
            space=y, algo=tpe.suggest,
            max_evals=10)
print('Best={}'.format(best))
