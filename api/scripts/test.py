from multiprocessing import Pool

def cube(x,y):
    return x**y
 
pool = Pool(processes=4)
results = [pool.apply(cube, args=(x,2,)) for x in range(1,7)]
print(results)
