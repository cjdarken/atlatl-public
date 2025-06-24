from numpy import load,mean

data = load('evaluations.npz')
lst = data.files
for item in lst:
    print(item)
    print(data[item])

for row in data['results']:
    print(mean(row))
